import uvicorn
from typing import Annotated, Optional
import jwt
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select, delete, Column, JSON
from datetime import datetime, timedelta
from db import get_session, init_db
from config import SUPABASE_SECRET_KEY, JWT_ALGORITHM
from models.trips import Trip
from models.itineraries import Itinerary
from models.user_profile import UserProfile, TravelerType, ActivityLevel
from services.openai_service import OpenAIService
from services.auth_helpers import verify_token, extract_user_id
import json
import traceback

# Add the get_current_user dependency
async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())]
) -> str:
    """Dependency that extracts and verifies user ID from JWT token."""
    if not credentials:
        raise HTTPException(status_code=403, detail="No authentication credentials provided")
    
    payload = verify_token(credentials.credentials, SUPABASE_SECRET_KEY)
    user_id = extract_user_id(payload)
    return user_id

app = FastAPI(
    title="Trip Planner API",
    description="API for managing travel itineraries",
    version="1.0.0",
)

origins = [
    "https://rabbitroute.netlify.app",
    "http://localhost:5173",
    "http://localhost:8000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

app.swagger_ui_init_oauth = {
    "usePkceWithAuthorizationCodeGrant": True,
}

security_scheme = {
    "Bearer": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Enter your Supabase JWT token in the format: Bearer <token>"
    }
}

app.openapi_components = {"securitySchemes": security_scheme}
app.openapi_security = [{"Bearer": []}]

async def generate_itinerary(trip: Trip, user_profile: Optional[UserProfile] = None) -> str:
    """Generate a detailed itinerary using OpenAI based on trip details."""
    ai_service = OpenAIService()
    
    print("\n=== Generating Itinerary ===")
    print(f"Trip ID: {trip.id}")
    print(f"Destination: {trip.destination}")
    print(f"Date Range: {trip.start_date} to {trip.end_date}")
    
    prompt = f"""
    Create a detailed itinerary with the following structure:
    ACCOMMODATION
    - Hotel Name: [Description, Location, Rating]
    - Hotel Name: [Description, Location, Rating]
    DAILY ITINERARY
    Day 1 - {trip.start_date}:
    Breakfast: [Restaurant Name] (Rating)
    Morning Activity: [Activity] (Time) @ [Location]
    Lunch: [Restaurant Name] (Rating)
    Afternoon Activity: [Activity] (Time) @ [Location]
    Dinner: [Restaurant Name] (Rating)
    Evening Activity: [Activity] (Time) @ [Location]
    [Repeat for each day until {trip.end_date}]
    TRAVEL TIPS:
    Weather:
    Transportation:
    Cultural Notes:
    
    Trip Details:
    - Destination: {trip.destination}
    - Duration: {(trip.end_date - trip.start_date).days + 1} days
    - Dates: {trip.start_date} to {trip.end_date}
    - Arrival: {trip.arrival_time or 'Not specified'}
    - Departure: {trip.departure_time or 'Not specified'}
    - Dietary Requirements: {trip.dietary_preferences or 'None specified'}
    - Activity Preferences: {trip.activity_preferences or 'None specified'}
    - Additional Notes: {trip.additional_notes or 'None'}
    """
    
    if user_profile:
        prompt += f"""
        User Preferences:
        - Traveler Type: {user_profile.traveler_type.value if user_profile.traveler_type else 'Not specified'}
        - Activity Level: {user_profile.activity_level.value if user_profile.activity_level else 'Not specified'}
        - Budget: {user_profile.budget_preference.value if user_profile.budget_preference else 'Not specified'}
        - Special Interests: {user_profile.special_interests or 'Not specified'}
        - Dietary Preferences: {user_profile.dietary_preferences or 'Not specified'}
        - Accessibility Needs: {user_profile.accessibility_needs or 'Not specified'}
        - Languages: {user_profile.preferred_languages or 'Not specified'}
        """
    
    try:
        print("\nSending prompt to OpenAI...")
        response = await ai_service.generate_trip_plan(prompt)
        print("\nReceived response from OpenAI")
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
    user_id: Annotated[str, Depends(get_current_user)],
    session: Session = Depends(get_session)
):
    """Create a new trip and generate its itinerary."""
    try:
        # Get or create user profile
        user_profile = session.exec(
            select(UserProfile).where(UserProfile.user_id == user_id)
        ).first()
        
        if not user_profile:
            user_profile = UserProfile(user_id=user_id)
            session.add(user_profile)
            session.commit()
            print("Created new user profile")
        
        # Set the user_id on the trip
        trip.user_id = user_id
        session.add(trip)
        session.commit()
        session.refresh(trip)
        
        try:
            print("\n=== Generating OpenAI Content ===")
            itinerary_content = await generate_itinerary(trip, user_profile)
            print("\nRaw OpenAI Response:")
            print(itinerary_content)
            
            print("\n=== Parsing OpenAI Response ===")
            structured_data = OpenAIService.parse_itinerary_response(itinerary_content)
            print("Parsed Data Structure:")
            print(json.dumps(structured_data, indent=2))
            
            # Create new Itinerary object
            new_itinerary = Itinerary(
                user_id=user_id,
                destination=trip.destination,
                start_date=trip.start_date,
                end_date=trip.end_date,
                arrival_time=trip.arrival_time,
                departure_time=trip.departure_time,
                notes=trip.additional_notes,
                daily_schedule=structured_data.get('daily_schedule', []),
                accommodation=structured_data.get('accommodation', []),
                travel_tips=structured_data.get('travel_tips', {}),  
                is_published=True,
                status="active"
)            
            session.add(new_itinerary)
            session.commit()
            
        except Exception as e:
            print(f"\nERROR in itinerary generation: {str(e)}")
            print(f"Error type: {type(e)}")
            print(f"Error traceback: {traceback.format_exc()}")
            session.rollback()
            raise
        
        return {
            "message": "Trip created successfully",
            "trip": {
                "id": trip.id,
                "user_id": trip.user_id,
                "destination": trip.destination,
                "start_date": trip.start_date.isoformat(),
                "end_date": trip.end_date.isoformat(),
                "is_published": trip.is_published,
                "is_favorite": trip.is_favorite
            }
        }
    
    except Exception as e:
        print(f"Error in create_trip: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trips")
async def get_trips(
    user_id: Annotated[str, Depends(get_current_user)],
    session: Session = Depends(get_session),
    show_unpublished: bool = False,
    favorites_only: bool = False
):
    """Get all trips for the authenticated user."""
    print(f"Fetching trips for user: {user_id}")
    print(f"Filters - show_unpublished: {show_unpublished}, favorites_only: {favorites_only}")
    
    query = select(Trip).where(Trip.user_id == user_id)
    
    if not show_unpublished:
        query = query.where(Trip.is_published == True)
    
    if favorites_only:
        query = query.where(Trip.is_favorite == True)
    
    trips = session.exec(query).all()
    print(f"Found {len(trips)} trips")
    
    return trips

@app.get("/trips/{trip_id}/details")
async def get_trip_details(
    trip_id: int,
    user_id: Annotated[str, Depends(get_current_user)],
    session: Session = Depends(get_session)
):
    """Get basic details for a specific trip."""
    trip = session.get(Trip, trip_id)
    
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if trip.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this trip")
    
    return {
        "id": trip.id,
        "user_id": trip.user_id,
        "destination": trip.destination,
        "start_date": trip.start_date,
        "end_date": trip.end_date,
        "arrival_time": trip.arrival_time,
        "departure_time": trip.departure_time,
        "status": trip.status,
        "is_published": trip.is_published,
        "is_favorite": trip.is_favorite
    }

@app.get("/itineraries/{trip_id}")
async def get_itinerary(
    trip_id: int,
    user_id: Annotated[str, Depends(get_current_user)],
    session: Session = Depends(get_session)
):
    """Get detailed itinerary information for a trip."""
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if trip.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this itinerary")
    
    # Improve the query to be more specific
    itinerary = session.exec(
        select(Itinerary)
        .where(Itinerary.user_id == user_id)
        .where(Itinerary.destination == trip.destination)
        .where(Itinerary.start_date == trip.start_date)
        .where(Itinerary.end_date == trip.end_date)
    ).first()
    
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    # Ensure daily_schedule is properly parsed
    try:
        daily_schedule = itinerary.daily_schedule
        if isinstance(daily_schedule, str):
            daily_schedule = json.loads(daily_schedule)
    except (json.JSONDecodeError, TypeError):
        daily_schedule = []
    
    # Add debug logging
    print("Raw itinerary data:", {
        "accommodation": itinerary.accommodation,
        "hotel_name": itinerary.hotel_name if hasattr(itinerary, 'hotel_name') else None
    })

    # Parse accommodation data from the response
    accommodation = []
    if itinerary.accommodation:
        # Use the complete accommodation array from the response
        accommodation = itinerary.accommodation
    elif hasattr(itinerary, 'hotel_name') and itinerary.hotel_name:
        # Fallback for legacy single hotel
        accommodation = [{
            "name": itinerary.hotel_name,
            "description": itinerary.hotel_description or "",
            "location": itinerary.hotel_location or "",
            "rating": float(itinerary.hotel_rating or 4.5),
            "nightly_rate": "200",
            "url": "#"
        }]

    # Log final accommodation data
    print("Final accommodation data:", accommodation)

    return {
        "id": itinerary.id,
        "destination": itinerary.destination,
        "start_date": itinerary.start_date,
        "end_date": itinerary.end_date,
        "arrival_time": itinerary.arrival_time,
        "departure_time": itinerary.departure_time,
        "notes": itinerary.notes,
        "daily_schedule": daily_schedule,
        "accommodation": accommodation,
        "travel_tips": itinerary.travel_tips,
        "status": itinerary.status
    }

@app.delete("/trips/{trip_id}")
async def delete_trip(
    trip_id: int,
    user_id: Annotated[str, Depends(get_current_user)],
    session: Session = Depends(get_session)
):
    """Delete a trip and all associated data, unless it's marked as favorite."""
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if trip.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this trip")
    
    if trip.is_favorite:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete a favorited trip. Please unfavorite the trip first."
        )
    
    # Delete associated itinerary if it exists
    itinerary = session.exec(
        select(Itinerary).where(Itinerary.user_id == user_id)
    ).first()
    if itinerary:
        session.delete(itinerary)
    
    session.delete(trip)
    session.commit()
    
    return {"message": "Trip and associated data deleted successfully"}

@app.get("/users/profile")
async def get_user_profile(
    user_id: Annotated[str, Depends(get_current_user)],
    session: Session = Depends(get_session)
):
    """Get user profile."""
    profile = session.exec(
        select(UserProfile).where(UserProfile.user_id == user_id)
    ).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return profile

@app.post("/users/profile")
async def create_or_update_profile(
    profile: UserProfile,
    user_id: Annotated[str, Depends(get_current_user)],
    session: Session = Depends(get_session)
):
    """Create or update user profile."""
    existing_profile = session.exec(
        select(UserProfile).where(UserProfile.user_id == user_id)
    ).first()
    
    if existing_profile:
        # Update existing profile
        profile_data = profile.dict(exclude_unset=True)
        for key, value in profile_data.items():
            setattr(existing_profile, key, value)
        session.add(existing_profile)
    else:
        # Create new profile
        profile.user_id = user_id
        session.add(profile)
    
    session.commit()
    return {"message": "Profile updated successfully"}

# Favorite Button
@app.post("/trips/{trip_id}/favorite")
async def toggle_favorite(
    trip_id: int,
    favorite_data: dict,
    user_id: Annotated[str, Depends(get_current_user)],
    session: Session = Depends(get_session)
):
    """Toggle favorite status for a trip."""
    trip = session.get(Trip, trip_id)
    
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if trip.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this trip")
    
    trip.is_favorite = favorite_data.get('is_favorite', False)
    session.add(trip)
    session.commit()
    
    return {
        "message": "Favorite status updated successfully",
        "is_favorite": trip.is_favorite
    }


# Initialize database on startup
@app.on_event("startup")
async def on_startup():
    init_db()

# Run the application
if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)