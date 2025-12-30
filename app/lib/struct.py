"""
Base classes and structures for the quiz application.

Defines the core Round, ADMIN, and USER classes that form the
foundation of the quiz system.
"""
from typing import TYPE_CHECKING, Optional
from .util import Participants, createPayload
from .qb import QuestionBank, Question, ClientQuestion
from .sm import Scores
from ..ui.admin.structs import _App
from .sockets import ServerSocket, ClientSocket
import os
import random
from ..ui.admin.frames.live import PlayFrame

if TYPE_CHECKING:
    from typing import TYPE_CHECKING

class Round():
    """
    Base class for quiz rounds.
    
    Handles common round functionality including question asking,
    answer checking, and score management.
    
    Attributes:
        admin: Reference to the Admin instance
        questions: Tuple of Question objects for this round
        num_q: Number of questions per participant (default: 3)
        curr_participant_i: Index of current participant
        curr_question_i: Index of current question
        isFinished: Whether the round has finished
        curr_scores: Scores object for this round
        lastQuestionMarked: Whether the last question was marked
        mark: Points awarded for correct answer
        minusMark: Points deducted for wrong answer
        id: Round identifier
        name: Human-readable round name
        roundEnded: Whether the round has ended
    """
    admin = None
    questions: tuple = None
    num_q = 3
    curr_participant_i: int = 0
    curr_question_i: int = 0
    isFinished = False
    curr_scores: Scores = None
    lastQuestionMarked = False
    mark = 10
    minusMark = 0
    id = None
    name = None
    roundEnded = False

    def __init__(self, admin: 'ADMIN', questions: tuple, mark: int, minusMark: int, 
                 id: int, name: str, num_q: int = 5) -> None:
        """
        Initialize a round.
        
        Args:
            admin: Reference to the Admin instance
            questions: Tuple of Question objects
            mark: Points for correct answer
            minusMark: Points for wrong answer
            id: Round identifier
            name: Round name
            num_q: Number of questions per participant
        """
        self.admin: ADMIN = admin
        self.questions = tuple(questions)
        self.mark = mark
        self.minusMark = minusMark
        self.id = id
        self.name = name
        self.num_q = num_q

    def check_answer(self, qid: str, answer: int) -> int:
        """
        Check if the submitted answer is correct.
        
        Args:
            qid: Question identifier
            answer: Submitted answer (1-based index)
        
        Returns:
            The correct answer index (1-based), or None if error
        """
        from .logger import get_logger
        logger = get_logger("round")
        
        self.lastQuestionMarked = True
        rightAns = None
        for question in self.questions:
            if str(qid) == str(question.qid):
                rightAns = question.answer
                break
        
        if rightAns is None:
            logger.error(f"Question ID {qid} not found in round {self.id}")
            return None
        
        try:
            isRight = int(rightAns) == int(answer)
            client_ids = self.admin.participants.getClientIDs()
            if self.curr_participant_i >= len(client_ids):
                logger.error(f"Participant index {self.curr_participant_i} out of range (total: {len(client_ids)})")
                return None
            participantID = client_ids[self.curr_participant_i]
            participant = self.admin.participants.get(participantID)
            participant_name = participant.name if participant and participant.name else "Unknown"
            
            logger.info(f"Answer check - qid:{qid}, submitted:{answer}, correct:{rightAns}, result:{'CORRECT' if isRight else 'WRONG'}, participant:{participant_name}")
            
            # Record in analytics
            if hasattr(self.admin, 'analytics') and self.admin.analytics:
                self.admin.analytics.record_answer(participantID, qid, isRight)
            
            if isRight:
                self.curr_scores.add(participantID, self.mark)
            else:
                self.curr_scores.add(participantID, self.minusMark)
            
            return int(rightAns)
        except (ValueError, IndexError, TypeError, AttributeError) as e:
            logger.error(f"Error checking answer: {e}", exc_info=True)
            return None
    
        
    def loadQ(self) -> None:
        """
        Load and shuffle questions for this round.
        
        Raises:
            Exception: If not enough questions available
        """
        allQuestions = list(self.questions)
        required_q = self.num_q * self.admin.participants.count()
        if len(allQuestions) < required_q:
            raise Exception("NUMBER OF QUESTIONs in DB is less than participants")
        random.shuffle(allQuestions)
        self.questions = tuple(allQuestions[0:required_q])

    def start(self) -> None:
        """
        Start the round.
        
        Loads questions, broadcasts round start to participants,
        and asks the first question.
        """
        from .logger import get_logger
        logger = get_logger("round")
        logger.info(f"ROUND-{self.id} ({self.name}) started")
        self.loadQ()
        self.admin.server.broadcast(createPayload("setround", self.id))
        
        # Record round start in analytics
        if hasattr(self.admin, 'analytics') and self.admin.analytics:
            self.admin.analytics.record_round_start(self.id, self.name)
        
        self.askQ()
        self.curr_scores = Scores(self.admin.participants.getClientIDs())
        logger.info(f"Round {self.id} initialized with {len(self.questions)} questions")

    def askQ(self) -> None:
        """
        Ask the current question to the current participant.
        
        Sends screensaver to other participants and the question
        to the active participant.
        """
        participantID = self.admin.participants.getClientIDs()[self.curr_participant_i]
        question: Question = self.questions[self.curr_question_i]
        
        # Send screensaver to other participants
        for cid in self.admin.participants.getClientIDs():
            if cid == participantID:
                continue
            self.admin.server.sendAllTo(createPayload("setscreensaver"), cid)
        
        self.admin.askQ(participantID, question.forParticipant())
        pf: PlayFrame = PlayFrame.me
        name = self.admin.participants.getNames()[self.curr_participant_i]
        pf.setInfo(name, f"Question : {self.curr_question_i+1}/{len(self.questions)}")

    def askNextQ(self) -> None:
        """
        Move to the next question.
        
        Advances to next participant and question, or ends the round
        if all questions are complete.
        """
        if not self.lastQuestionMarked:
            return
        self.lastQuestionMarked = False
        
        # Get participant count atomically to prevent race condition
        participant_count = self.admin.participants.count()
        if participant_count == 0:
            logger.warning("No participants available, cannot ask next question")
            return
        
        # Use atomic modulo operation to prevent race condition
        try:
            self.curr_participant_i = (self.curr_participant_i + 1) % participant_count
        except (ZeroDivisionError, TypeError) as e:
            logger.error(f"Error calculating next participant index: {e}", exc_info=True)
            return
        
        self.curr_question_i += 1
        if self.curr_question_i >= len(self.questions):
            self.onend()
            return
        self.askQ()

    def mark_right(self) -> None:
        """
        Manually mark the current answer as correct.
        
        Awards points to the current participant.
        """
        if self.lastQuestionMarked or self.roundEnded:
            return
        self.lastQuestionMarked = True
        participantID = self.admin.participants.getClientIDs()[self.curr_participant_i]
        self.curr_scores.add(participantID, self.mark)

    def mark_wrong(self) -> None:
        """
        Manually mark the current answer as wrong.
        
        Deducts points from the current participant.
        """
        if self.lastQuestionMarked or self.roundEnded:
            return
        self.lastQuestionMarked = True
        participantID = self.admin.participants.getClientIDs()[self.curr_participant_i]
        self.curr_scores.add(participantID, self.minusMark)

    def onend(self) -> None:
        """
        Handle round end.
        
        Adds round scores to main scores, resets round scores,
        and displays the scoreboard.
        """
        from .logger import get_logger
        logger = get_logger("round")
        
        self.roundEnded = True
        self.admin.scores.addScore(self.curr_scores)
        
        # Record round end in analytics
        if hasattr(self.admin, 'analytics') and self.admin.analytics:
            self.admin.analytics.record_round_end(self.id, self.curr_scores)
        
        self.curr_scores.reset()
        logger.info(f"Round {self.id} ended. Final scores: {self.admin.scores.toString()}")
        pf: PlayFrame = PlayFrame.me
        pf.f_scores.setData(self.name, self.admin.scores.scores, self.id < 4)
        pf.setActiveFrame(pf.f_scores)

class ADMIN():
    
    lastQuestionMarked=False
    participants=Participants()
    qBank:QuestionBank=None
    scores:Scores=None
    ui:_App=None
    server:ServerSocket=None
    me=None
    quiz_started=False
    currentRound:Round=None
    num_participants:int=0 # number of participant in quiz when it started

    def askQ(self,clientID, question:ClientQuestion):
        pass

    def askAll(self, question):
        pass

    def checkQ(self, question)->bool:
        pass

    def updateScore(self):
        pass

    def start(self):
        pass

    def setUserData(self, clientID, name):
        pass

class USER():
    client:ClientSocket=None
    me=None
    ui=None
    name:str=None

    def setName(self, name):
        self.name = name