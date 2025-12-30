"""
Round Manager classes to operate rounds
Actions :-
1.) Send Start signal to clients
2.) PLAY / PAUSE (signal from admin)

Admin Signals :-
1.) Signal to play , pause , stop, goto next round and pre round
"""
from .sockets import ServerSocket
import csv
import random
from .struct import ADMIN
from .qb import QuestionBank
from .util import Participants, Participant
from .struct import Round
from .qb import ClientQuestion, Question
from .sm import Scores
from .util import createPayload
from ..ui.admin.frames.live import PlayFrame
from ..ui.rounds.round2 import Round2 as R2
from .logger import get_logger
from ..config import config

logger = get_logger("round")

class Round1(Round):
    name = "Straight Forward"
    
    def __init__(self, admin: ADMIN) -> None:
        mark = config.get("rounds.round1.mark", 10)
        minus_mark = config.get("rounds.round1.minus_mark", 0)
        super().__init__(admin, admin.qBank.round1, mark=mark, minusMark=minus_mark, id=1, name=Round1.name)
        logger.info(f"Round1 initialized: mark={mark}, minus_mark={minus_mark}")

class Round2(Round):
    name = "Bujho Toh Jano"
    
    def __init__(self, admin: ADMIN) -> None:
        mark = config.get("rounds.round2.mark", 10)
        minus_mark = config.get("rounds.round2.minus_mark", -5)
        super().__init__(admin, admin.qBank.round2, mark=mark, minusMark=minus_mark, id=2, name=Round2.name)
        logger.info(f"Round2 initialized: mark={mark}, minus_mark={minus_mark}")

    def check_answer(self, qid, answer):
        rightAns = super().check_answer(qid, answer)
        self.admin.show_right_answer(qid, rightAns, answer)
    
class Round3(Round):
    name = "Roll the Dice"
    rolling_i = None  # store the index of the participant who is rolling the dice
    target_i = None  # the index of the participant came by rolling the dice

    def __init__(self, admin) -> None:
        mark = config.get("rounds.round3.mark", 10)
        minus_mark = config.get("rounds.round3.minus_mark", -5)
        super().__init__(admin, admin.qBank.round3, mark=mark, minusMark=minus_mark, id=3, name=Round3.name)
        logger.info(f"Round3 initialized: mark={mark}, minus_mark={minus_mark}")

    def check_answer(self, qid, answer):
        rightAns = super().check_answer(qid, answer)
        isRight = int(rightAns) == int(answer)
        if self.rolling_i is not None or isRight: self.admin.show_right_answer(qid, rightAns, answer)
        if not isRight and self.rolling_i is None:
            self.roll_the_dice()
            pass
    
    def roll_the_dice(self):
        """Show the roll the dice interface and then """
        pf:PlayFrame = PlayFrame.me
        pf.curr_round.dice.show()
        self.rolling_i=self.curr_participant_i
        pass

    def roll(self)->int:
        num:int = self.admin.participants.count()
        if num <= 1:
            logger.warning("Not enough participants for dice roll")
            return None
        indices = list(range(0, num))
        if self.rolling_i is not None and self.rolling_i in indices:
            indices.remove(int(self.rolling_i))
        if not indices:
            logger.warning("No valid indices for dice roll")
            return None
        result = random.choice(indices)
        self.target_i = result

        names = self.admin.participants.getNames()
        if result < len(names):
            name = names[result]
            return name
        else:
            logger.error(f"Dice roll result {result} out of range for {len(names)} participants")
            return None

    def ask(self):
        pf:PlayFrame = PlayFrame.me
        pf.curr_round.dice.hide()
        self.curr_participant_i = self.target_i
        self.askQ()
    
    def mark_right(self):
        if self.lastQuestionMarked or self.roundEnded:return
        self.lastQuestionMarked=True
        participantID = self.admin.participants.getClientIDs()[self.curr_participant_i]
        self.curr_scores.add(participantID, self.mark)

    def mark_wrong(self):
        if self.lastQuestionMarked or self.roundEnded:return
        self.lastQuestionMarked=True
        participantID = self.admin.participants.getClientIDs()[self.curr_participant_i]
        self.curr_scores.add(participantID, self.minusMark)

    def askNextQ(self):
        """Move to next question, handling dice roll logic."""
        if not self.lastQuestionMarked:
            return
        self.lastQuestionMarked = False

        if self.rolling_i is not None:
            self.curr_participant_i = self.rolling_i
            self.target_i = None
            self.rolling_i = None
        
        self.curr_participant_i = (self.curr_participant_i + 1) % self.admin.participants.count()
        self.curr_question_i += 1
        if self.curr_question_i >= len(self.questions):
            self.onend()
            return
        self.askQ()



class Round4(Round):
    name = "Speedo Round"
    totalQ = 15
    isBuzzerPressed = False
    first_id = None

    def __init__(self, admin) -> None:
        mark = config.get("rounds.round4.mark", 10)
        minus_mark = config.get("rounds.round4.minus_mark", -5)
        self.totalQ = config.get("rounds.round4.total_questions", 15)
        super().__init__(admin, admin.qBank.round4, mark=mark, minusMark=minus_mark, id=4, name=Round4.name)
        logger.info(f"Round4 initialized: mark={mark}, minus_mark={minus_mark}, total_questions={self.totalQ}")

    
    def check_answer(self, qid: str, answer: int) -> int:
        """Check answer for Round4 (buzzer round)."""
        self.lastQuestionMarked = True
        rightAns = None
        for question in self.questions:
            if str(qid) == str(question.qid):
                rightAns = question.answer
                break
        isRight = int(rightAns) == int(answer)
        logger.debug(f"Round4 answer check - qid:{qid}, ans:{answer}, correct:{rightAns}, result:{'CORRECT' if isRight else 'WRONG'}")
        participantID = self.admin.participants.getClientIDs()[self.curr_participant_i]
        if isRight:
            self.curr_scores.add(participantID, self.mark)
        else:
            self.curr_scores.add(participantID, self.minusMark)
        return int(rightAns)
        
    def loadQ(self) -> None:
        """Load questions for Round 4 (fixed total)."""
        allQuestions = list(self.admin.qBank.round4)
        
        if len(allQuestions) < self.totalQ:
            raise Exception(f"NUMBER OF QUESTIONs in DB is less than required: {len(allQuestions)} < {self.totalQ}")
        random.shuffle(allQuestions)
        self.questions = tuple(allQuestions[0:self.totalQ])

    def start(self) -> None:
        """Start Round4."""
        logger.info(f"ROUND-{self.id} ({self.name}) started")
        self.loadQ()
        self.admin.server.broadcast(createPayload("setround", self.id))
        self.askQ()
        self.curr_scores = Scores(self.admin.participants.getClientIDs())

    def askQ(self) -> None:
        """Ask question to all participants (buzzer round)."""
        self.first_id = None
        self.isBuzzerPressed = False
        self.clear_users()
        question: Question = self.questions[self.curr_question_i]
        question: ClientQuestion = question.forParticipant()
        
        self.admin.server.broadcast(
            createPayload("setquestion", question.jsons())
        )

        pf: PlayFrame = PlayFrame.me
        pf.curr_round.setQ(question)
        pf.setInfo("", f"Question : {self.curr_question_i+1}/{len(self.questions)}")

    def askNextQ(self) -> None:
        """Move to next question."""
        if not self.lastQuestionMarked:
            return
        self.lastQuestionMarked = False
        self.curr_question_i += 1
        if self.curr_question_i >= len(self.questions):
            self.onend()
            return
        self.askQ()

    def mark_right(self):
        if self.lastQuestionMarked or self.roundEnded :return
        self.lastQuestionMarked=True
        # participantID = self.admin.participants.getClientIDs()[self.currentParticipant]
        participantID = self.first_id
        if not participantID: return
        self.curr_scores.add(participantID, self.mark)

    def mark_wrong(self):
        if self.lastQuestionMarked or self.roundEnded:return
        self.lastQuestionMarked=True
        # participantID = self.admin.participants.getClientIDs()[self.currentParticipant]
        participantID = self.first_id
        if not participantID: return
        self.curr_scores.add(participantID, self.minusMark)

    def check_answer(self, qid, answer):
        rightAns = super().check_answer(qid, answer)
        self.admin.show_right_answer(qid, rightAns, answer)

    def clear_users(self):
        pf:PlayFrame = PlayFrame.me
        pf.curr_round.clearusers()
        pass

    def add_user(self,clientID):
        name = self.admin.participants.get(clientID).name
        pf:PlayFrame = PlayFrame.me
        pf.curr_round.adduser(name)
        pass

    def buzzer_pressed(self, clientID):
        # add client to list
        self.add_user(clientID)
        if self.isBuzzerPressed: return
        self.isBuzzerPressed=True
        self.first_id = clientID
        
        print("ADDING ")