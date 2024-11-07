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
    BUDGET = "daily_budget_50_100"           # Daily budget $50-100 
    COMFORT = "daily_budget_100_200"         # Daily budget $100-200
    PREMIUM = "daily_budget_200_500"         # Daily budget $200-500
    LUXURY = "daily_budget_500_1000"         # Daily budget $500-1000
    ULTRA_LUXURY = "daily_budget_1000_plus"  # Daily budget $1000+


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

