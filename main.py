import uvicorn
from typing import Annotated
import jwt
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select, delete
from datetime import datetime, timedelta
from db import get_session, init_db
from config import SUPABASE_SECRET_KEY, JWT_ALGORITHM
from models.trips import Trip
from models.itineraries import Itinerary
from services.openai_service import OpenAIService

app = FastAPI()

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:5173",
    "http://localhost:8000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_token(token: str):
    """Verify JWT token from Supabase"""
    try:
        payload = jwt.decode(token, SUPABASE_SECRET_KEY,
                             audience=["authenticated"],
                             algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def generate_itinerary(trip: Trip) -> str:
    """
    Generate a detailed itinerary using OpenAI based on trip details.
    Uses our OpenAIService for consistent formatting and error handling.
    """
    ai_service = OpenAIService()
    
    # Updated prompt format to match new system instructions
    prompt = f"""
    Please create an itinerary for:
    
    Destination: {trip.destination}
    Length of Stay: {(trip.end_date - trip.start_date).days + 1} days
    Travel Preferences: {trip.activity_preferences or 'None specified'}
    
    Additional Details:
    - Arrival: {trip.arrival_time or 'Not specified'}
    - Departure: {trip.departure_time or 'Not specified'}
    - Dietary Preferences: {trip.dietary_preferences or 'None specified'}
    - Additional Notes: {trip.additional_notes or 'None'}
    """

    try:
        response = await ai_service.generate_trip_plan(prompt)
        return response
    except Exception as e:
        print(f"OpenAI API error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate itinerary")

@app.get("/")
def root():
    """Root endpoint - API health check"""
    return {"message": "Welcome to the Trip Planner API!"}

@app.post("/trips/create")
async def create_trip(
    trip: Trip,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session)
):
    """
    Create a new trip and generate its itinerary.
    Requires authentication.
    """
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    trip.user_id = auth_result['sub']
    
    try:
        # Save the trip
        session.add(trip)
        session.commit()
        session.refresh(trip)
        
        # Generate itinerary using OpenAI
        itinerary_content = await generate_itinerary(trip)
        
        # Create daily itineraries
        current_date = trip.start_date
        day_number = 1
        
        while current_date <= trip.end_date:
            # Create an itinerary for each day of the trip
            itinerary = Itinerary(
                trip_id=trip.id,
                day_number=day_number,
                date=current_date,
                morning_activities="To be parsed from AI response",
                lunch_suggestions="To be parsed from AI response",
                afternoon_activities="To be parsed from AI response",
                dinner_suggestions="To be parsed from AI response",
                evening_activities="To be parsed from AI response",
                ai_suggestions=itinerary_content
            )
            session.add(itinerary)
            current_date += timedelta(days=1)
            day_number += 1
        
        session.commit()
        return {"message": "Trip created successfully", "trip": trip}
    
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trips/")
async def get_trips(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session)
):
    """
    Get all trips for the authenticated user.
    """
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    user_id = auth_result['sub']
    
    trips = session.exec(select(Trip).where(Trip.user_id == user_id)).all()
    return trips

@app.get("/trips/{trip_id}")
async def get_trip(
    trip_id: int,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session)
):
    """
    Get a specific trip and its itineraries.
    Verifies user owns the trip.
    """
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    user_id = auth_result['sub']
    
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if trip.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this trip")
    
    itineraries = session.exec(
        select(Itinerary)
        .where(Itinerary.trip_id == trip_id)
        .order_by(Itinerary.day_number)
    ).all()
    
    return {"trip": trip, "itineraries": itineraries}

@app.delete("/trips/{trip_id}")
async def delete_trip(
    trip_id: int,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session)
):
    """
    Delete a trip and its associated itineraries.
    Verifies user owns the trip.
    """
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    user_id = auth_result['sub']
    
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if trip.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this trip")
    
    # Delete associated itineraries first
    session.exec(delete(Itinerary).where(Itinerary.trip_id == trip_id))
    session.delete(trip)
    session.commit()
    
    return {"message": "Trip and associated itineraries deleted successfully"}

# New Itinerary Routes
@app.get("/trips/{trip_id}/itineraries/")
async def get_trip_itineraries(
    trip_id: int,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session)
):
    """Get all itineraries for a specific trip."""
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    user_id = auth_result['sub']
    
    # Verify trip exists and belongs to user
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this trip's itineraries")
    
    itineraries = session.exec(
        select(Itinerary)
        .where(Itinerary.trip_id == trip_id)
        .order_by(Itinerary.day_number)
    ).all()
    
    return itineraries

@app.get("/trips/{trip_id}/itineraries/{day_number}")
async def get_itinerary(
    trip_id: int,
    day_number: int,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session)
):
    """Get a specific itinerary by trip ID and day number."""
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    user_id = auth_result['sub']
    
    # Verify trip exists and belongs to user
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this itinerary")
    
    itinerary = session.exec(
        select(Itinerary)
        .where(Itinerary.trip_id == trip_id)
        .where(Itinerary.day_number == day_number)
    ).first()
    
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    return itinerary

@app.put("/trips/{trip_id}/itineraries/{day_number}")
async def update_itinerary(
    trip_id: int,
    day_number: int,
    itinerary_update: Itinerary,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session)
):
    """Update a specific itinerary."""
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    user_id = auth_result['sub']
    
    # Verify trip exists and belongs to user
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this itinerary")
    
    existing_itinerary = session.exec(
        select(Itinerary)
        .where(Itinerary.trip_id == trip_id)
        .where(Itinerary.day_number == day_number)
    ).first()
    
    if not existing_itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    # Update the existing itinerary with new values
    existing_itinerary.morning_activities = itinerary_update.morning_activities
    existing_itinerary.lunch_suggestions = itinerary_update.lunch_suggestions
    existing_itinerary.afternoon_activities = itinerary_update.afternoon_activities
    existing_itinerary.dinner_suggestions = itinerary_update.dinner_suggestions
    existing_itinerary.evening_activities = itinerary_update.evening_activities
    existing_itinerary.ai_suggestions = itinerary_update.ai_suggestions
    
    session.add(existing_itinerary)
    session.commit()
    session.refresh(existing_itinerary)
    
    return existing_itinerary

@app.delete("/trips/{trip_id}/itineraries/{day_number}")
async def delete_itinerary(
    trip_id: int,
    day_number: int,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session)
):
    """Delete a specific itinerary."""
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    user_id = auth_result['sub']
    
    # Verify trip exists and belongs to user
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this itinerary")
    
    itinerary = session.exec(
        select(Itinerary)
        .where(Itinerary.trip_id == trip_id)
        .where(Itinerary.day_number == day_number)
    ).first()
    
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    session.delete(itinerary)
    session.commit()
    
    return {"message": "Itinerary deleted successfully"}

# Initialize database on startup
@app.on_event("startup")
async def on_startup():
    init_db()

# Run the application
if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)