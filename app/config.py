"""
Centralized configuration management for the quiz application.

Supports JSON configuration files with environment variable overrides.
"""
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class Config:
    """
    Singleton configuration manager.
    
    Loads configuration from JSON file or creates default configuration.
    Supports environment variable overrides.
    """
    _instance: Optional['Config'] = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._config:
            self.load()
    
    def load(self) -> None:
        """Load configuration from file or create default."""
        config_path = Path(os.getcwd()) / "config.json"
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config: {e}. Using defaults.")
                self._config = self._default_config()
                self.save()
        else:
            self._config = self._default_config()
            self.save()
        
        # Override with environment variables
        self._apply_env_overrides()
    
    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "network": {
                "port": 4040,
                "buffer_size": 4096,
                "timeout": 30,
                "magic_key": "India",
                "max_reconnect_attempts": 5,
                "reconnect_delay": 1
            },
            "rounds": {
                "round1": {
                    "mark": 10,
                    "minus_mark": 0,
                    "questions_per_participant": 3,
                    "name": "Straight Forward"
                },
                "round2": {
                    "mark": 10,
                    "minus_mark": -5,
                    "questions_per_participant": 3,
                    "name": "Bujho Toh Jano"
                },
                "round3": {
                    "mark": 10,
                    "minus_mark": -5,
                    "questions_per_participant": 3,
                    "name": "Roll the Dice"
                },
                "round4": {
                    "mark": 10,
                    "minus_mark": -5,
                    "total_questions": 15,
                    "name": "Speedo Round"
                }
            },
            "ui": {
                "admin_window_size": "1920x1080",
                "participant_window_size": "1920x1080",
                "theme": "light",
                "question_timeout": 30
            },
            "quiz": {
                "min_participants": 1,
                "max_participants": 50
            },
            "logging": {
                "level": "INFO",
                "log_dir": "logs"
            },
            "security": {
                "admin_password_hash": None,
                "enable_encryption": False,
                "session_timeout": 3600
            },
            "analytics": {
                "enabled": True,
                "export_dir": "exports"
            }
        }
    
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides."""
        # Network settings
        if os.getenv("QUIZ_PORT"):
            try:
                self._config["network"]["port"] = int(os.getenv("QUIZ_PORT"))
            except ValueError:
                pass
        
        if os.getenv("QUIZ_BUFFER_SIZE"):
            try:
                self._config["network"]["buffer_size"] = int(os.getenv("QUIZ_BUFFER_SIZE"))
            except ValueError:
                pass
        
        # Logging
        if os.getenv("QUIZ_LOG_LEVEL"):
            log_level = os.getenv("QUIZ_LOG_LEVEL").upper()
            if log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                self._config["logging"]["level"] = log_level
    
    def save(self) -> None:
        """Save current configuration to file."""
        config_path = Path(os.getcwd()) / "config.json"
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving config: {e}")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get config value using dot notation.
        
        Args:
            key_path: Dot-separated key path (e.g., 'network.port')
            default: Default value if key not found
        
        Returns:
            Config value or default
        """
        keys = key_path.split('.')
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        return value
    
    def set(self, key_path: str, value: Any) -> None:
        """
        Set config value using dot notation.
        
        Args:
            key_path: Dot-separated key path
            value: Value to set
        """
        keys = key_path.split('.')
        config = self._config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
        self.save()
    
    def get_all(self) -> Dict[str, Any]:
        """Get entire configuration dictionary."""
        return self._config.copy()


# Global config instance
config = Config()

