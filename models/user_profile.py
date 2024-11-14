from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List, TYPE_CHECKING
from enum import Enum
from datetime import datetime
from .base import Base

if TYPE_CHECKING:
    from .trips import Trip

class TravelerType(str, Enum):
    SOLO = "solo"
    COUPLE = "couple"
    FAMILY = "family"
    GROUP = "group"

class ActivityLevel(str, Enum):
    RELAXED = "relaxed"
    MODERATE = "moderate"
    ACTIVE = "active"

class BudgetPreference(str, Enum):
    BUDGET = "BUDGET"      # $100-200 per day
    COMFORT = "COMFORT"    # $200-400 per day
    PREMIUM = "PREMIUM"    # $400-800 per day  
    LUXURY = "LUXURY"      # $800-1500 per day
    ULTRA_LUXURY = "ULTRA_LUXURY"  # $1500+ per day


    def get_budget_range(self) -> tuple[int, int]:
        """Returns the daily budget range in USD for this preference level"""
        ranges = {
            "BUDGET": (100, 200),
            "COMFORT": (200, 400),
            "PREMIUM": (400, 800),
            "LUXURY": (800, 1500),
            "ULTRA_LUXURY": (1500, float('inf'))
        }
        return ranges[self.value]
    
    def get_description(self) -> str:
        """Returns a human-readable description of this budget level"""
        descriptions = {
            "BUDGET": "Budget-friendly options, $100-200 per day",
            "COMFORT": "Mid-range comfort, $200-400 per day",
            "PREMIUM": "Premium experiences, $400-800 per day",
            "LUXURY": "Luxury accommodations and dining, $800-1500 per day",
            "ULTRA_LUXURY": "Ultra-luxury with no expense spared, $1500+ per day"
        }
        return descriptions[self.value]


class UserProfile(Base, table=True):
    __tablename__ = "user_profiles"
    
    user_id: str = Field(unique=True, index=True)
    traveler_type: Optional[TravelerType] = Field(default=None)
    activity_level: Optional[ActivityLevel] = Field(default=None)
    special_interests: Optional[str] = Field(default=None)
    dietary_preferences: Optional[str] = Field(default=None)
    accessibility_needs: Optional[str] = Field(default=None)
    preferred_languages: Optional[str] = Field(default=None)
    budget_preference: Optional[BudgetPreference] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    trips: List["Trip"] = Relationship(back_populates="user_profile")

