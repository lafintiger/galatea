"""Settings Manager Service"""
import json
from pathlib import Path
from typing import Optional
from ..models.schemas import UserSettings
from ..config import settings as app_settings


class SettingsManager:
    """Manages user settings persistence"""
    
    def __init__(self):
        self.settings_file = app_settings.data_dir / "settings.json"
        self._settings: Optional[UserSettings] = None
    
    def load(self) -> UserSettings:
        """Load settings from file or return defaults"""
        if self._settings:
            return self._settings
        
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r") as f:
                    data = json.load(f)
                    self._settings = UserSettings(**data)
            except Exception:
                self._settings = UserSettings()
        else:
            self._settings = UserSettings()
        
        return self._settings
    
    def save(self, new_settings: UserSettings) -> UserSettings:
        """Save settings to file"""
        self._settings = new_settings
        
        # Ensure directory exists
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.settings_file, "w") as f:
            json.dump(new_settings.model_dump(), f, indent=2)
        
        return self._settings
    
    def update(self, **kwargs) -> UserSettings:
        """Update specific settings"""
        current = self.load()
        updated_data = current.model_dump()
        updated_data.update(kwargs)
        return self.save(UserSettings(**updated_data))


# Singleton instance
settings_manager = SettingsManager()

