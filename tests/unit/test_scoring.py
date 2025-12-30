"""
Unit tests for scoring system.
"""
import pytest
from app.lib.sm import Scores


class TestScores:
    """Tests for Scores class."""
    
    def test_scores_initialization(self):
        """Test Scores initialization with participant IDs."""
        ids = [1001, 1002, 1003]
        scores = Scores(ids)
        
        assert scores.get(1001) == 0
        assert scores.get(1002) == 0
        assert scores.get(1003) == 0
    
    def test_scores_add(self):
        """Test adding points to a participant."""
        ids = [1001, 1002]
        scores = Scores(ids)
        
        scores.add(1001, 10)
        assert scores.get(1001) == 10
        
        scores.add(1001, 5)
        assert scores.get(1001) == 15
    
    def test_scores_add_negative(self):
        """Test adding negative points (penalties)."""
        ids = [1001]
        scores = Scores(ids)
        
        scores.add(1001, -5)
        assert scores.get(1001) == -5
    
    def test_scores_set(self):
        """Test setting score directly."""
        ids = [1001]
        scores = Scores(ids)
        
        scores.set(1001, 25)
        assert scores.get(1001) == 25
    
    def test_scores_add_score(self):
        """Test adding scores from another Scores object."""
        ids = [1001, 1002]
        scores1 = Scores(ids)
        scores2 = Scores(ids)
        
        scores1.add(1001, 10)
        scores1.add(1002, 5)
        
        scores2.add(1001, 3)
        scores2.add(1002, 2)
        
        scores1.addScore(scores2)
        
        assert scores1.get(1001) == 13
        assert scores1.get(1002) == 7
    
    def test_scores_reset(self):
        """Test resetting all scores to zero."""
        ids = [1001, 1002]
        scores = Scores(ids)
        
        scores.add(1001, 10)
        scores.add(1002, 5)
        
        scores.reset()
        
        assert scores.get(1001) == 0
        assert scores.get(1002) == 0
    
    def test_scores_to_string(self):
        """Test scores serialization."""
        ids = [1001, 1002]
        scores = Scores(ids)
        
        scores.add(1001, 10)
        scores.add(1002, 5)
        
        result = scores.toString()
        assert "1001" in result
        assert "1002" in result
        assert "10" in result
        assert "5" in result

