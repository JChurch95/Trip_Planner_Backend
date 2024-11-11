from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import date
from .base import Base

class Accommodation(Base, table=True):
    __tablename__ = "accommodations"
    
    trip_id: int = Field(foreign_key="trips.id")
    name: str
    description: str
    location: str
    rating: float
    website_url: Optional[str] = None
    unique_features: Optional[str] = None
    price_range: Optional[str] = None

class DailyItinerary(Base, table=True):
    __tablename__ = "daily_itineraries"
    
    trip_id: int = Field(foreign_key="trips.id")
    day_number: int
    date: date
    
    # Morning
    breakfast_spot: str
    breakfast_rating: float
    morning_activity: str
    morning_activity_time: str
    morning_activity_location: str
    morning_activity_url: Optional[str] = None
    
    # Afternoon
    lunch_spot: str
    lunch_rating: float
    afternoon_activity: str
    afternoon_activity_time: str
    afternoon_activity_location: str
    afternoon_activity_url: Optional[str] = None
    
    # Evening
    dinner_spot: str
    dinner_rating: float
    evening_activity: str
    evening_activity_time: str
    evening_activity_location: str
    evening_activity_url: Optional[str] = None

class TravelTips(Base, table=True):
    __tablename__ = "travel_tips"
    
    trip_id: int = Field(foreign_key="trips.id", primary_key=True)
    weather_summary: str
    clothing_suggestions: str
    transportation_tips: str
    cultural_notes: str
    seasonal_events: Optional[str] = None