from datetime import date
from typing import Optional, Dict, Any
from sqlmodel import Field, SQLModel, Column, JSON
from .base import Base

class Itinerary(Base, table=True):
    __tablename__ = "itineraries"
    
    user_id: str = Field(index=True)
    destination: str
    start_date: date
    end_date: date
    
    # Trip Details
    arrival_time: Optional[str] = None
    departure_time: Optional[str] = None
    notes: Optional[str] = None
    
    # Accommodation Details
    hotel_name: Optional[str] = None
    hotel_location: Optional[str] = None
    hotel_description: Optional[str] = None
    hotel_rating: Optional[float] = None
    
    # Daily Activities (stored as JSON)
    daily_schedule: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON)
    )
    
    # Status and Preferences
    is_published: bool = Field(default=True)
    is_favorite: bool = Field(default=False)
    status: str = Field(default="active")