from .ui.user.main import App
from .lib.sockets import ClientSocket
from .settings import addr, getWIFI, port
from .lib.struct import USER
from .lib.util import createPayload, rand_str
import json
from .lib.qb import ClientQuestion
from ._globals import _GLOBALs
from .lib.logger import participant_logger
from .lib.validators import ParticipantValidator
from .config import config

logger = participant_logger()


class User(USER):
    ui:App=None
    connecting=False
    currRound=1
    failed_count=0

    def __init__(self) -> None:
        logger.info("Initializing Participant application")
        USER.me = self
        _GLOBALs['user'] = self
        self.ui = App()
        USER.me = self
        logger.info("Participant application initialized")

    def setRound(self, data):
        try:
            round_num = int(data)
            logger.info(f"Setting current round to {round_num}")
            self.currRound = round_num

            if round_num == 1:
                self.ui.mainpanel.setActiveFrame(self.ui.mainpanel.f_round1)
            elif round_num == 2:
                self.ui.mainpanel.setActiveFrame(self.ui.mainpanel.f_round2)
            elif round_num == 3:
                self.ui.mainpanel.setActiveFrame(self.ui.mainpanel.f_round3)
            elif round_num == 4:
                self.ui.mainpanel.setActiveFrame(self.ui.mainpanel.f_round4)
            else:
                # All rounds completed
                logger.info(f"All rounds completed (round_num: {round_num})")
                self.show_quiz_complete_popup()
        except (ValueError, TypeError) as e:
            logger.error(f"Error setting round: {e}")

    def login(self):
        if self.connecting:
            logger.debug("Login already in progress, skipping")
            return
        
        self.connecting = True
        logger.info("Attempting to connect to admin server")

        if self.client:
            self.client.off_all()
            self.client.disconnect()
            self.client = None

        try:
            wifi_ip = getWIFI()
            if not wifi_ip:
                raise OSError("Could not detect WiFi IP address")
            
            server_addr = (wifi_ip, port)
            logger.info(f"Connecting to server at {server_addr}")
            self.client = ClientSocket(addr=server_addr)

            self.client.on("handshake-done", self.onHandshakeDone)
            self.client.on("handshake-error", self.onLoginFailed)
            self.client.on("disconnected", self.reconnect)
            self.client.on("data", self.handleDataEvent)
            
            self.client.connect()
            self.uid = rand_str()
            logger.debug(f"Connection initiated, UID: {self.uid}")
        except OSError as e:
            logger.error(f"Network error during login: {e}", exc_info=True)
            self.connecting = False
            self.onLoginFailed()
        except Exception as e:
            logger.error(f"Unexpected error during login: {e}", exc_info=True)
            self.connecting = False
            self.onLoginFailed()

    def onLoginFailed(self, *a):
        self.failed_count += 1
        logger.warning(f"Login failed (attempt {self.failed_count})")
        self.connecting = False
        if hasattr(self.ui.mainpanel.f_login.f_form, 'l_info'):
            self.ui.mainpanel.f_login.f_form.l_info.configure(
                text=f"Login Failed - attempt {self.failed_count}", 
                text_color="red"
            )

    def setConnectingFalse(self,*a): self.connecting = False

    def submit_answer(self, qid, answer):
        self.client.send(createPayload("checkanswer", {"qid":qid, "answer":answer}))
        pass

    def handleDataEvent(self, args):
        payload = args[0]
        
        try:
            payload = json.loads(payload)
            logger.debug(f"Received payload: action={payload.get('action')}")
            
            action = payload["action"]
            data = payload["data"]

            if action == "setround":
                self.setRound(data)
            
            elif action == "setquestion":
                self.setRound(self.currRound)
                d = json.loads(data)
                q = ClientQuestion(
                    qid=d["qid"], 
                    text=d["text"], 
                    options=d["options"], 
                    imgPath=d["imgPath"]
                )
                logger.info(f"Question received: qid={q.qid}")
                self.ui.mainpanel.activeframe.setQ(q)
            
            elif action == "setscreensaver":
                logger.info("Setting screensaver mode")
                self.ui.mainpanel.setActiveFrame(self.ui.mainpanel.f_screensaver)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in payload: {e}")
        except KeyError as e:
            logger.error(f"Missing key in payload: {e}")
        except Exception as e:
            logger.error(f"Error handling data event: {e}", exc_info=True)
        
    def reconnect(self, *args):
        logger.info("Connection lost, will reconnect in 3 seconds")
        self.connecting = False
        if self.client:
            self.client.off_all()
            self.client.disconnect()
        self.ui.after(3000, self.login)

    def start(self):
        self.ui.show()

    def onHandshakeDone(self, args):
        self.connecting = False
        logger.info("Handshake completed successfully")
        
        # Validate name before sending
        if not self.name:
            logger.warning("No name set, using default")
            self.name = "Participant"
        
        is_valid, error = ParticipantValidator.validate_name(self.name)
        if not is_valid:
            logger.warning(f"Invalid name '{self.name}': {error}, using default")
            self.name = "Participant"
        
        self.ui.mainpanel.setActiveFrame(self.ui.mainpanel.f_screensaver)
        logger.info(f"Sending participant name: {self.name}")
        payload = createPayload("setdata", self.name)
        self.client.send(payload)
        self.ui.title("Participant - " + self.name)

    def show_quiz_complete_popup(self):
        """
        Display a popup message when all rounds are completed.
        """
        try:
            import customtkinter as ctk
            
            # Create popup window
            popup = ctk.CTkToplevel(self.ui)
            popup.title("Quiz Complete!")
            popup.geometry("500x300")
            popup.resizable(False, False)
            
            # Center on screen
            popup.grab_set()
            
            # Title
            title_label = ctk.CTkLabel(
                popup,
                text="🎉 QUIZ COMPLETE! 🎉",
                font=("Roboto", 26, "bold"),
                text_color="#FFD700"
            )
            title_label.pack(pady=20)
            
            # Message
            msg_label = ctk.CTkLabel(
                popup,
                text="Congratulations!\n\nYou have completed all 4 rounds of the quiz!",
                font=("Roboto", 14),
                text_color="#333"
            )
            msg_label.pack(pady=20)
            
            # Thank you message
            thanks_label = ctk.CTkLabel(
                popup,
                text="Thank you for participating!",
                font=("Roboto", 12),
                text_color="#666"
            )
            thanks_label.pack(pady=10)
            
            # Close button
            close_btn = ctk.CTkButton(
                popup,
                text="Close",
                font=("Roboto", 14),
                height=40,
                command=popup.destroy,
                fg_color="#4169E1"
            )
            close_btn.pack(pady=15, padx=20, fill="x")
            
        except Exception as e:
            logger.error(f"Error showing completion popup: {e}", exc_info=True)

    def on_buzzer_pressed(self, qid):
        self.client.send(createPayload("buzzer-pressed", ))


def main():
    try:
        logger.info("=" * 50)
        logger.info("Starting Participant Application")
        logger.info("=" * 50)
        user = User()
        user.start()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.critical(f"Fatal error in main: {e}", exc_info=True)

if __name__ == "__main__":
    main()