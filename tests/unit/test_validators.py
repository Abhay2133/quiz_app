"""
Unit tests for validators module.
"""
import pytest
from pathlib import Path
import tempfile
import os
from app.lib.validators import QuestionValidator, ParticipantValidator, NetworkValidator


class TestQuestionValidator:
    """Tests for QuestionValidator class."""
    
    def test_validate_csv_row_valid(self):
        """Test validation of a valid CSV row."""
        row = ["1", "What is 2+2?", "2,3,4,5", "3", "test.jpg"]
        is_valid, error = QuestionValidator.validate_csv_row(row, 1)
        assert is_valid is True
        assert error is None
    
    def test_validate_csv_row_insufficient_columns(self):
        """Test validation fails with insufficient columns."""
        row = ["1", "Question?", "opt1,opt2"]
        is_valid, error = QuestionValidator.validate_csv_row(row, 1)
        assert is_valid is False
        assert "Insufficient columns" in error
    
    def test_validate_csv_row_missing_qid(self):
        """Test validation fails with missing question ID."""
        row = ["", "Question?", "opt1,opt2", "1", ""]
        is_valid, error = QuestionValidator.validate_csv_row(row, 1)
        assert is_valid is False
        assert "Missing question ID" in error
    
    def test_validate_csv_row_missing_text(self):
        """Test validation fails with missing question text."""
        row = ["1", "", "opt1,opt2", "1", ""]
        is_valid, error = QuestionValidator.validate_csv_row(row, 1)
        assert is_valid is False
        assert "Missing question text" in error
    
    def test_validate_csv_row_too_few_options(self):
        """Test validation fails with too few options."""
        row = ["1", "Question?", "opt1", "1", ""]
        is_valid, error = QuestionValidator.validate_csv_row(row, 1)
        assert is_valid is False
        assert "Need at least" in error
    
    def test_validate_csv_row_invalid_answer(self):
        """Test validation fails with invalid answer."""
        row = ["1", "Question?", "opt1,opt2,opt3", "5", ""]
        is_valid, error = QuestionValidator.validate_csv_row(row, 1)
        assert is_valid is False
        assert "Answer index out of range" in error
    
    def test_validate_csv_row_non_numeric_answer(self):
        """Test validation fails with non-numeric answer."""
        row = ["1", "Question?", "opt1,opt2", "abc", ""]
        is_valid, error = QuestionValidator.validate_csv_row(row, 1)
        assert is_valid is False
        assert "Invalid answer format" in error


class TestParticipantValidator:
    """Tests for ParticipantValidator class."""
    
    def test_validate_name_valid(self):
        """Test validation of valid participant name."""
        is_valid, error = ParticipantValidator.validate_name("John Doe")
        assert is_valid is True
        assert error is None
    
    def test_validate_name_empty(self):
        """Test validation fails with empty name."""
        is_valid, error = ParticipantValidator.validate_name("")
        assert is_valid is False
        assert "cannot be empty" in error
    
    def test_validate_name_too_long(self):
        """Test validation fails with name too long."""
        long_name = "A" * 51
        is_valid, error = ParticipantValidator.validate_name(long_name)
        assert is_valid is False
        assert "too long" in error
    
    def test_validate_name_invalid_characters(self):
        """Test validation fails with invalid characters."""
        is_valid, error = ParticipantValidator.validate_name("John@Doe")
        assert is_valid is False
        assert "invalid characters" in error


class TestNetworkValidator:
    """Tests for NetworkValidator class."""
    
    def test_validate_port_valid(self):
        """Test validation of valid port."""
        is_valid, error = NetworkValidator.validate_port(4040)
        assert is_valid is True
        assert error is None
    
    def test_validate_port_too_low(self):
        """Test validation fails with port < 1024."""
        is_valid, error = NetworkValidator.validate_port(80)
        assert is_valid is False
        assert "must be >= 1024" in error
    
    def test_validate_port_too_high(self):
        """Test validation fails with port > 65535."""
        is_valid, error = NetworkValidator.validate_port(70000)
        assert is_valid is False
        assert "must be <= 65535" in error
    
    def test_validate_ip_valid(self):
        """Test validation of valid IP address."""
        is_valid, error = NetworkValidator.validate_ip("192.168.1.1")
        assert is_valid is True
        assert error is None
    
    def test_validate_ip_invalid(self):
        """Test validation fails with invalid IP."""
        is_valid, error = NetworkValidator.validate_ip("999.999.999.999")
        assert is_valid is False
        assert "Invalid IP address" in error

