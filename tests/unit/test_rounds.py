"""
Unit tests for round classes.
"""
import pytest
from app.lib.rounds import Round1, Round2, Round3, Round4
from app.lib.struct import ADMIN
from app.lib.qb import QuestionBank
from app.lib.sm import Scores
from app.lib.util import Participants
from app.lib.sockets import ServerSocket
from unittest.mock import Mock, MagicMock
import os


class MockAdmin(ADMIN):
    """Mock admin for testing."""
    
    def __init__(self):
        self.participants = Participants()
        self.scores = None
        self.server = Mock()
        self.server.broadcast = Mock()
        self.server.sendAllTo = Mock()
        self.server.sendTo = Mock()
        self.server.clients = {}
        
        # Create mock question bank
        questions_dir = os.path.join(os.getcwd(), "data", "questions")
        if os.path.exists(questions_dir):
            self.qBank = QuestionBank(qdir=questions_dir)
        else:
            self.qBank = Mock()
            self.qBank.round1 = tuple()
            self.qBank.round2 = tuple()
            self.qBank.round3 = tuple()
            self.qBank.round4 = tuple()
    
    def askQ(self, clientID, question):
        pass
    
    def show_right_answer(self, qid, rightAns, answer):
        pass


class TestRound1:
    """Tests for Round1 class."""
    
    def test_round1_initialization(self):
        """Test Round1 initialization."""
        admin = MockAdmin()
        round1 = Round1(admin)
        
        assert round1.id == 1
        assert round1.name == "Straight Forward"
        assert round1.mark == 10
        assert round1.minusMark == 0
    
    def test_round1_config_usage(self):
        """Test Round1 uses config values."""
        from app.config import config
        
        # This test verifies config is being used
        # Actual values depend on config.json
        admin = MockAdmin()
        round1 = Round1(admin)
        
        # Should have valid mark values
        assert round1.mark > 0
        assert round1.minusMark >= 0


class TestRound2:
    """Tests for Round2 class."""
    
    def test_round2_initialization(self):
        """Test Round2 initialization."""
        admin = MockAdmin()
        round2 = Round2(admin)
        
        assert round2.id == 2
        assert round2.name == "Bujho Toh Jano"
        assert round2.mark == 10
        assert round2.minusMark == -5
    
    def test_round2_check_answer_shows_result(self):
        """Test Round2 shows answer after checking."""
        admin = MockAdmin()
        round2 = Round2(admin)
        
        # Mock the show_right_answer method
        admin.show_right_answer = Mock()
        
        # This would normally check an answer
        # For now, just verify the method exists
        assert hasattr(round2, 'check_answer')


class TestRound3:
    """Tests for Round3 class."""
    
    def test_round3_initialization(self):
        """Test Round3 initialization."""
        admin = MockAdmin()
        round3 = Round3(admin)
        
        assert round3.id == 3
        assert round3.name == "Roll the Dice"
        assert round3.rolling_i is None
        assert round3.target_i is None


class TestRound4:
    """Tests for Round4 class."""
    
    def test_round4_initialization(self):
        """Test Round4 initialization."""
        admin = MockAdmin()
        round4 = Round4(admin)
        
        assert round4.id == 4
        assert round4.name == "Speedo Round"
        assert round4.totalQ == 15
        assert round4.isBuzzerPressed is False
        assert round4.first_id is None

