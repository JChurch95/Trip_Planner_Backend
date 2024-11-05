from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import date
from .base import Base

class Trip(Base, table=True):
    __tablename__ = "trips"
    
    user_id: str = Field(index=True)  # Supabase user ID
    destination: str
    start_date: date
    end_date: date
    arrival_time: Optional[str] = None
    departure_time: Optional[str] = None
    dietary_preferences: Optional[str] = None
    activity_preferences: Optional[str] = None
    additional_notes: Optional[str] = None
    status: str = Field(default="pending")  # pending, completed, cancelled