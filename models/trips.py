from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import date
from .base import Base

if TYPE_CHECKING:
    from .user_profile import UserProfile

class Trip(Base, table=True):
    __tablename__ = "trips"
    
    user_id: str = Field(index=True, foreign_key="user_profiles.user_id")
    destination: str
    start_date: date
    end_date: date
    arrival_time: Optional[str] = None
    departure_time: Optional[str] = None
    dietary_preferences: Optional[str] = None
    activity_preferences: Optional[str] = None
    additional_notes: Optional[str] = None
    status: str = Field(default="pending")
    is_published: bool = Field(default=True) 
    is_favorite: bool = Field(default=False)  

    user_profile: Optional["UserProfile"] = Relationship(back_populates="trips")