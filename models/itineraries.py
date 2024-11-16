from datetime import date
from typing import Optional, Dict, Any, List
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
    
    # Accommodation Details (stored as JSON array)
    accommodation: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        sa_column=Column(JSON)
    )
    
    # Daily Activities (stored as JSON)
    daily_schedule: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        sa_column=Column(JSON)
    )
    
    # Travel Tips (stored as JSON)
    travel_tips: Optional[Dict[str, str]] = Field(
        default_factory=lambda: {
            "weather": "",
            "transportation": "",
            "cultural_notes": ""
        },
        sa_column=Column(JSON)
    )
    
    # Status and Preferences  
    is_published: bool = Field(default=True)
    is_favorite: bool = Field(default=False)
    status: str = Field(default="active")

    class Config:
        json_encoders = {
            date: lambda v: v.isoformat()
        }