"""
User preferences value object.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional

from ..base import ValueObject


@dataclass(frozen=True)
class UserPreferences(ValueObject):
    """
    User preferences value object for customizable settings.
    
    Stores user's interface and notification preferences.
    """
    
    # UI preferences
    theme: str = "light"  # light, dark, auto
    language: str = "zh-CN"  # zh-CN, en-US
    timezone: str = "Asia/Shanghai"
    
    # Notification preferences
    email_notifications: bool = True
    push_notifications: bool = True
    match_notifications: bool = True
    rating_change_notifications: bool = True
    team_activity_notifications: bool = True
    
    # Privacy preferences
    profile_visibility: str = "public"  # public, friends, private
    show_real_name: bool = False
    show_email: bool = False
    
    # Display preferences
    items_per_page: int = 20
    show_advanced_stats: bool = False
    show_position_colors: bool = True
    
    # Additional custom settings
    custom_settings: Dict[str, Any] = None
    
    def __post_init__(self):
        """Validate preferences after initialization."""
        # Set default empty dict for custom_settings if None
        if self.custom_settings is None:
            object.__setattr__(self, 'custom_settings', {})
        
        # Validate theme
        valid_themes = {"light", "dark", "auto"}
        if self.theme not in valid_themes:
            object.__setattr__(self, 'theme', "light")
        
        # Validate language
        valid_languages = {"zh-CN", "en-US"}
        if self.language not in valid_languages:
            object.__setattr__(self, 'language', "zh-CN")
        
        # Validate profile visibility
        valid_visibility = {"public", "friends", "private"}
        if self.profile_visibility not in valid_visibility:
            object.__setattr__(self, 'profile_visibility', "public")
        
        # Validate items per page
        if self.items_per_page < 10 or self.items_per_page > 100:
            object.__setattr__(self, 'items_per_page', 20)
    
    @classmethod
    def create_default(cls) -> 'UserPreferences':
        """Create default user preferences."""
        return cls()
    
    def with_theme(self, theme: str) -> 'UserPreferences':
        """Create new preferences with updated theme."""
        return UserPreferences(
            theme=theme,
            language=self.language,
            timezone=self.timezone,
            email_notifications=self.email_notifications,
            push_notifications=self.push_notifications,
            match_notifications=self.match_notifications,
            rating_change_notifications=self.rating_change_notifications,
            team_activity_notifications=self.team_activity_notifications,
            profile_visibility=self.profile_visibility,
            show_real_name=self.show_real_name,
            show_email=self.show_email,
            items_per_page=self.items_per_page,
            show_advanced_stats=self.show_advanced_stats,
            show_position_colors=self.show_position_colors,
            custom_settings=self.custom_settings
        )
    
    def with_notifications(
        self,
        email: Optional[bool] = None,
        push: Optional[bool] = None,
        match: Optional[bool] = None,
        rating_change: Optional[bool] = None,
        team_activity: Optional[bool] = None
    ) -> 'UserPreferences':
        """Create new preferences with updated notification settings."""
        return UserPreferences(
            theme=self.theme,
            language=self.language,
            timezone=self.timezone,
            email_notifications=email if email is not None else self.email_notifications,
            push_notifications=push if push is not None else self.push_notifications,
            match_notifications=match if match is not None else self.match_notifications,
            rating_change_notifications=rating_change if rating_change is not None else self.rating_change_notifications,
            team_activity_notifications=team_activity if team_activity is not None else self.team_activity_notifications,
            profile_visibility=self.profile_visibility,
            show_real_name=self.show_real_name,
            show_email=self.show_email,
            items_per_page=self.items_per_page,
            show_advanced_stats=self.show_advanced_stats,
            show_position_colors=self.show_position_colors,
            custom_settings=self.custom_settings
        )
    
    def with_privacy_settings(
        self,
        visibility: Optional[str] = None,
        show_real_name: Optional[bool] = None,
        show_email: Optional[bool] = None
    ) -> 'UserPreferences':
        """Create new preferences with updated privacy settings."""
        return UserPreferences(
            theme=self.theme,
            language=self.language,
            timezone=self.timezone,
            email_notifications=self.email_notifications,
            push_notifications=self.push_notifications,
            match_notifications=self.match_notifications,
            rating_change_notifications=self.rating_change_notifications,
            team_activity_notifications=self.team_activity_notifications,
            profile_visibility=visibility if visibility is not None else self.profile_visibility,
            show_real_name=show_real_name if show_real_name is not None else self.show_real_name,
            show_email=show_email if show_email is not None else self.show_email,
            items_per_page=self.items_per_page,
            show_advanced_stats=self.show_advanced_stats,
            show_position_colors=self.show_position_colors,
            custom_settings=self.custom_settings
        )
    
    def with_custom_setting(self, key: str, value: Any) -> 'UserPreferences':
        """Create new preferences with additional custom setting."""
        new_custom_settings = dict(self.custom_settings)
        new_custom_settings[key] = value
        
        return UserPreferences(
            theme=self.theme,
            language=self.language,
            timezone=self.timezone,
            email_notifications=self.email_notifications,
            push_notifications=self.push_notifications,
            match_notifications=self.match_notifications,
            rating_change_notifications=self.rating_change_notifications,
            team_activity_notifications=self.team_activity_notifications,
            profile_visibility=self.profile_visibility,
            show_real_name=self.show_real_name,
            show_email=self.show_email,
            items_per_page=self.items_per_page,
            show_advanced_stats=self.show_advanced_stats,
            show_position_colors=self.show_position_colors,
            custom_settings=new_custom_settings
        )
    
    def get_custom_setting(self, key: str, default: Any = None) -> Any:
        """Get a custom setting value."""
        return self.custom_settings.get(key, default)
    
    def has_email_notifications_enabled(self) -> bool:
        """Check if email notifications are enabled."""
        return self.email_notifications
    
    def has_push_notifications_enabled(self) -> bool:
        """Check if push notifications are enabled."""
        return self.push_notifications
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert preferences to dictionary."""
        return {
            "theme": self.theme,
            "language": self.language,
            "timezone": self.timezone,
            "email_notifications": self.email_notifications,
            "push_notifications": self.push_notifications,
            "match_notifications": self.match_notifications,
            "rating_change_notifications": self.rating_change_notifications,
            "team_activity_notifications": self.team_activity_notifications,
            "profile_visibility": self.profile_visibility,
            "show_real_name": self.show_real_name,
            "show_email": self.show_email,
            "items_per_page": self.items_per_page,
            "show_advanced_stats": self.show_advanced_stats,
            "show_position_colors": self.show_position_colors,
            "custom_settings": dict(self.custom_settings)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPreferences':
        """Create preferences from dictionary."""
        return cls(
            theme=data.get("theme", "light"),
            language=data.get("language", "zh-CN"),
            timezone=data.get("timezone", "Asia/Shanghai"),
            email_notifications=data.get("email_notifications", True),
            push_notifications=data.get("push_notifications", True),
            match_notifications=data.get("match_notifications", True),
            rating_change_notifications=data.get("rating_change_notifications", True),
            team_activity_notifications=data.get("team_activity_notifications", True),
            profile_visibility=data.get("profile_visibility", "public"),
            show_real_name=data.get("show_real_name", False),
            show_email=data.get("show_email", False),
            items_per_page=data.get("items_per_page", 20),
            show_advanced_stats=data.get("show_advanced_stats", False),
            show_position_colors=data.get("show_position_colors", True),
            custom_settings=data.get("custom_settings", {})
        )