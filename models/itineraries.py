from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import date
from .base import Base

class Itinerary(Base, table=True):
    __tablename__ = "itineraries"
    
    trip_id: int = Field(foreign_key="trips.id")
    day_number: int
    date: date
    morning_activities: str
    lunch_suggestions: str
    afternoon_activities: str
    dinner_suggestions: str
    evening_activities: Optional[str] = None
    ai_suggestions: Optional[str] = None