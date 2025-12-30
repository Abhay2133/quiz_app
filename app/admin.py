from .lib.sm import Scores
import json
from .lib.qb import QuestionBank
from app.lib.qb import ClientQuestion
from .lib.struct import ADMIN
from .lib.sockets import ClientSocket, ServerSocket, EventEmitter
from .ui.admin.main import App
from .settings import addr, getHOTSPOT, port
from .lib.util import Participant, createPayload
from .lib.rounds import Round1, Round2, Round3, Round4
import os
from .ui.admin.frames.live import PlayFrame, LiveFrame
from ._globals import _GLOBALs
import tkinter as tk
from tkinter import messagebox
from .lib.logger import admin_logger
from .config import config
from .lib.analytics import QuizAnalytics
from .lib.security import get_auth_manager

logger = admin_logger()

def show_and_exit(error_message: str = "Turn on hotspot first"):
    """
    Displays an alert dialog and exits the application.
    
    Args:
        error_message: Error message to display
    """
    logger.error(f"Fatal error: {error_message}")
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    messagebox.showerror("Error", error_message)
    root.destroy()  # Destroy the hidden window to exit the app

class Admin(ADMIN):
    curr_round_i=0
    min_participants=1
    currentRound = None
    rounds=tuple()
    
    def __init__(self, ) -> None:
        super().__init__()
        logger.info("Initializing Admin application")
        _GLOBALs["admin"] = self
        ADMIN.me = self
        self.ui=App()
        
        # Get min participants from config
        self.min_participants = config.get("quiz.min_participants", 1)
        
        # Initialize question bank
        questions_dir = os.path.join(os.getcwd(), "data", "questions")
        logger.info(f"Loading question bank from: {questions_dir}")
        self.qBank = QuestionBank(qdir=questions_dir)
        
        # Initialize server socket
        try:
            hotspot_ip = getHOTSPOT()
            if not hotspot_ip:
                raise OSError("Could not detect hotspot IP address")
            
            server_addr = (hotspot_ip, port)
            logger.info(f"Starting server on {server_addr}")
            self.server = ServerSocket(addr=server_addr)

            self.server.on("new-connection", self.addParticipant)
            self.server.on("data", self.handleDataEvents)
            self.server.on("disconnected", self.onDisconnect)
            logger.info("Server socket initialized successfully")
        except OSError as e:
            logger.error(f"Network error: {e}", exc_info=True)
            show_and_exit("Turn on hotspot first - Could not detect network interface")
        except Exception as e:
            logger.critical(f"Unexpected error initializing server: {e}", exc_info=True)
            show_and_exit(f"Failed to start server: {str(e)}")
        
        # Initialize rounds
        logger.info("Initializing quiz rounds")
        self.rounds = (
            Round1(self), 
            Round2(self), 
            Round3(self), 
            Round4(self)
        )
        self.currentRound = self.rounds[self.curr_round_i]
        
        # Initialize analytics
        self.analytics = QuizAnalytics()
        analytics_enabled = config.get("analytics.enabled", True)
        if analytics_enabled:
            logger.info("Analytics enabled")
        else:
            logger.info("Analytics disabled")
        
        # Initialize authentication
        self.auth_manager = get_auth_manager()
        
        logger.info(f"Admin initialized with {len(self.rounds)} rounds")

    # def set_screensaver()

    def onDisconnect(self, args):
        clientID=args[0]
        participant = self.participants.get(clientID)
        if participant:
            participant_name = participant.name or f"Unknown ({clientID})"
            logger.info(f"Participant {participant_name} (ID: {clientID}) disconnected")
            if participant.isPlaying:
                logger.warning(f"Participant {participant_name} disconnected during active play")
                # Mark as not playing and remove zombie participant
                participant.isPlaying = False
            # Always remove disconnected participants to prevent zombies
            self.participants.remove(clientID)
            logger.debug(f"Removed participant {clientID} from participants list")
        else:
            logger.warning(f"Unknown participant (ID: {clientID}) disconnected")

    def handleDataEvents(self, args):
        payload = args[0]
        clientID = payload["clientID"]
        
        try:
            data = json.loads(payload["data"])
            action = data["action"]
            data = data["data"]

            logger.debug(f"Received action '{action}' from client {clientID}")

            if action == "setdata":
                self.setUserData(clientID, data)
            
            if action == "checkanswer":
                qid = data["qid"]
                answer = data["answer"]
                logger.info(f"Answer received: qid={qid}, answer={answer} from client {clientID}")
                self.currentRound.check_answer(qid, answer)
                if hasattr(self.ui.f_main.f_live.f_play.curr_round, 'stop_timer'):
                    self.ui.f_main.f_live.f_play.curr_round.stop_timer()

            if action == "buzzer-pressed" and self.curr_round_i == 3:
                logger.info(f"Buzzer pressed by client {clientID}")
                self.currentRound.buzzer_pressed(clientID)
                if hasattr(self.ui.f_main.f_live.f_play.curr_round, 'stop_timer'):
                    self.ui.f_main.f_live.f_play.curr_round.stop_timer()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from client {clientID}: {e}")
        except KeyError as e:
            logger.error(f"Missing key in payload from client {clientID}: {e}")
        except Exception as e:
            logger.error(f"Error handling data event from client {clientID}: {e}", exc_info=True)

    def askQ(self, clientID, question: ClientQuestion):
        # return super().askQ(clientID, question)()
        self.ui.f_main.f_live.f_play.curr_round.setQ(question)
        self.server.sendTo(createPayload("setquestion", question.jsons()), clientID)

    def setUserData(self, clientID, name, id=None):
        """
        Set user data for a participant.
        
        Args:
            clientID: Client identifier
            name: Participant name
            id: Optional participant ID (not currently used)
        
        Raises:
            ValueError: If participant not found or name is invalid
        """
        if not name or not isinstance(name, str) or not name.strip():
            logger.warning(f"Invalid name provided for client {clientID}: {name}")
            return
        
        participant: Participant = self.participants.get(clientID)
        if participant is None:
            logger.error(f"Participant {clientID} not found when setting user data")
            raise ValueError(f"Participant {clientID} not found")
        
        participant.name = name.strip()
        logger.info(f"Set name '{name}' for participant {clientID}")
        
        # Update analytics if available
        if hasattr(self, 'analytics') and self.analytics and clientID in self.analytics.participant_data:
            self.analytics.participant_data[clientID]["name"] = name.strip()

    def addParticipant(self, args):
        clientID = args[0]
        client = self.server.clients[clientID]
        participant = Participant(client=client, clientID=clientID)
        self.participants.add(participant)
    
    def start(self):
        self.server.start()
        self.ui.show()

    def askAll(self, question:ClientQuestion):
        pass
        # return super().askAll(question)()

    def start_quiz(self):
        participant_count = self.participants.count()
        if participant_count < self.min_participants:
            logger.warning(f"Cannot start quiz: {participant_count} participants (minimum: {self.min_participants})")
            return
        
        logger.info(f"Starting quiz with {participant_count} participants")
        self.quiz_started = True
        self.num_participants = participant_count
        self.scores = Scores(self.participants.getClientIDs())
        
        # Start analytics tracking
        if self.analytics:
            participant_ids = list(self.participants.getClientIDs())
            self.analytics.start_quiz(participant_ids)
            # Set participant names in analytics
            for client_id in participant_ids:
                participant = self.participants.get(client_id)
                if participant and participant.name:
                    self.analytics.participant_data[client_id]["name"] = participant.name
        
        lf: LiveFrame = LiveFrame.me
        lf.setActiveFrame(lf.f_play)
        self.start_curr_round()
        logger.info("Quiz started successfully")

    def start_curr_round(self):
        """udpate Frame and send signal"""
        pf:PlayFrame = PlayFrame.me
        pf.setCurrRound(pf.roundUIs[self.curr_round_i])
        self.currentRound.start()
        pass

    def start_next_round(self):
        self.curr_round_i+=1
        
        # Check if all rounds are completed
        if self.curr_round_i >= len(self.rounds):
            self.show_quiz_complete_message()
            return
        
        self.currentRound = self.rounds[self.curr_round_i]
        # self.currentRound.start()
        self.start_curr_round()
        pass
        # self.roundUIs = (Round1(self.ui.f_main.f_live.f_play.))

    def show_quiz_complete_message(self):
        """
        Display a message when all rounds are completed.
        Shows a popup with the final scores.
        """
        try:
            import customtkinter as ctk
            from tkinter import messagebox
            
            # Get final scores
            scores_data = []
            if hasattr(self, 'scores') and self.scores:
                scores_data = self.scores.getScoreBoard()
            
            # Create a popup window
            popup = ctk.CTkToplevel(self.ui)
            popup.title("Quiz Complete!")
            popup.geometry("600x400")
            popup.resizable(False, False)
            
            # Title
            title_label = ctk.CTkLabel(
                popup, 
                text="🎉 QUIZ COMPLETE! 🎉",
                font=("Roboto", 28, "bold"),
                text_color="#FFD700"
            )
            title_label.pack(pady=20)
            
            # Message
            msg_label = ctk.CTkLabel(
                popup,
                text="All 4 rounds have been completed successfully!",
                font=("Roboto", 16),
                text_color="#333"
            )
            msg_label.pack(pady=10)
            
            # Final Scores
            scores_text = "FINAL SCORES:\n\n"
            if scores_data:
                for i, score_entry in enumerate(scores_data, 1):
                    name = score_entry.get('name', f'Participant {i}')
                    score = score_entry.get('score', 0)
                    scores_text += f"{i}. {name}: {score} points\n"
            else:
                scores_text += "No scores available"
            
            scores_label = ctk.CTkLabel(
                popup,
                text=scores_text,
                font=("Roboto", 14),
                text_color="#333",
                justify="left"
            )
            scores_label.pack(pady=15, padx=20, fill="both", expand=True)
            
            # Close button
            close_btn = ctk.CTkButton(
                popup,
                text="Close Quiz",
                font=("Roboto", 14),
                height=40,
                command=popup.destroy,
                fg_color="#4169E1"
            )
            close_btn.pack(pady=15, padx=20, fill="x")
            
            logger.info("Quiz completed - All 4 rounds finished!")
            
        except Exception as e:
            logger.error(f"Error showing completion message: {e}", exc_info=True)
            # Fallback: just log it
            logger.warning("⚠️ ALL ROUNDS COMPLETED! ⚠️")

    def show_right_answer(self, qid, rightAns, answer):
        pf:PlayFrame = PlayFrame.me
        if pf.curr_round.hasOptions: pf.curr_round.show_answer(rightAns, answer)
        # show_answer(self, correct_i, selected_i):
        pass
    
    def get_analytics_summary(self):
        """
        Get analytics summary.
        
        Returns:
            Dictionary with analytics summary or None if analytics not available
        """
        if not hasattr(self, 'analytics') or not self.analytics:
            return None
        return self.analytics.get_summary()
    
    def get_participant_analytics(self, participant_id):
        """
        Get analytics for a specific participant.
        
        Args:
            participant_id: Participant identifier
            
        Returns:
            Dictionary with participant statistics or None if not found
        """
        if not hasattr(self, 'analytics') or not self.analytics:
            return None
        return self.analytics.get_participant_stats(participant_id)
    
    def get_round_analytics(self, round_id):
        """
        Get analytics for a specific round.
        
        Args:
            round_id: Round identifier
            
        Returns:
            Dictionary with round statistics or None if not found
        """
        if not hasattr(self, 'analytics') or not self.analytics:
            return None
        return self.analytics.get_round_stats(round_id)
    
    def export_analytics_json(self, filepath):
        """
        Export analytics to JSON file.
        
        Args:
            filepath: Path to output file
            
        Returns:
            True if successful, False otherwise
        """
        if not hasattr(self, 'analytics') or not self.analytics:
            logger.warning("Analytics not available for export")
            return False
        return self.analytics.export_to_json(filepath)
    
    def export_analytics_csv(self, filepath):
        """
        Export analytics leaderboard to CSV file.
        
        Args:
            filepath: Path to output file
            
        Returns:
            True if successful, False otherwise
        """
        if not hasattr(self, 'analytics') or not self.analytics:
            logger.warning("Analytics not available for export")
            return False
        return self.analytics.export_to_csv(filepath)
    
    def get_leaderboard(self):
        """
        Get current leaderboard from analytics.
        
        Returns:
            List of participants sorted by score or None if analytics not available
        """
        if not hasattr(self, 'analytics') or not self.analytics:
            return None
        return self.analytics.get_leaderboard()

def main():
    try:
        logger.info("=" * 50)
        logger.info("Starting Admin Application")
        logger.info("=" * 50)
        admin = Admin()
        admin.start()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.critical(f"Fatal error in main: {e}", exc_info=True)
        show_and_exit(f"Application error: {str(e)}")

if __name__=="__main__":
    main()