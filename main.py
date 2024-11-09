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
from models.user_profile import UserProfile, TravelerType, ActivityLevel
from services.openai_service import OpenAIService

app = FastAPI(
    title="Trip Planner API",
    description="API for managing travel itineraries",
    version="1.0.0",
)

origins = [
    "http://localhost:5173",  # Your frontend
    "http://localhost:8000",  # Your backend
    "http://127.0.0.1:5173"   # Alternative frontend URL
]

# Add security scheme configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure security scheme for Swagger UI
app.swagger_ui_init_oauth = {
    "usePkceWithAuthorizationCodeGrant": True,
}

# Define security scheme
security_scheme = {
    "Bearer": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Enter your JWT token in the format: Bearer <token>"
    }
}

# Add security scheme to OpenAPI configuration
app.openapi_components = {"securitySchemes": security_scheme}
app.openapi_security = [{"Bearer": []}]

def verify_token(token: str):
    """Verify JWT token from Supabase"""
    try:
        print("Raw token received:", token)
        # Remove 'Bearer ' if present
        if token.startswith('Bearer '):
            token = token.split(' ')[1]
        
        print(f"Processing token: {token[:20]}...")
        try:
            payload = jwt.decode(
                token, 
                SUPABASE_SECRET_KEY,
                algorithms=["HS256", "JWS"],
                audience=["authenticated"]
            )
            print("Token decoded successfully:", payload)
            return payload
        except jwt.InvalidTokenError as e:
            print(f"Token decode error: {str(e)}")
            print(f"Token used: {token}")
            print(f"Secret key used: {SUPABASE_SECRET_KEY[:10]}...")
            raise
    except Exception as e:
        print(f"Unexpected error during token verification: {str(e)}")
        raise HTTPException(status_code=401, detail="Token verification failed")

async def generate_itinerary(trip: Trip) -> str:
    """
    Generate a detailed itinerary using OpenAI based on trip details.
    Uses our OpenAIService for consistent formatting and error handling.
    """
    ai_service = OpenAIService()
    
    # Get user profile for additional context
    session = next(get_session())
    user_profile = session.exec(
        select(UserProfile).where(UserProfile.user_id == trip.user_id)
    ).first()
    
    # Updated prompt format to include user preferences if available
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

    # Add user profile information if available
    if user_profile:
        prompt += f"""
        
        User Preferences:
        - Traveler Type: {user_profile.traveler_type.value if user_profile.traveler_type else 'Not specified'}
        - Activity Level: {user_profile.activity_level.value if user_profile.activity_level else 'Not specified'}
        - Special Interests: {user_profile.special_interests or 'Not specified'}
        - Dietary Preferences: {user_profile.dietary_preferences or 'Not specified'}
        - Accessibility Needs: {user_profile.accessibility_needs or 'Not specified'}
        - Preferred Languages: {user_profile.preferred_languages or 'Not specified'}
        - Budget Preference: {user_profile.budget_preference or 'Not specified'}
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



@app.put("/trips/{trip_id}/publish")
async def publish_trip(
    trip_id: int,
    publish: bool,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session)
):
    """Toggle trip published status"""
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    user_id = auth_result['sub']
    
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if trip.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this trip")
    
    trip.is_published = publish
    session.add(trip)
    session.commit()
    session.refresh(trip)
    
    return {"message": f"Trip {'published' if publish else 'unpublished'} successfully"}

@app.put("/trips/{trip_id}/favorite")
async def favorite_trip(
    trip_id: int,
    favorite: bool,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session)
):
    """Toggle trip favorite status"""
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    user_id = auth_result['sub']
    
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if trip.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this trip")
    
    trip.is_favorite = favorite
    session.add(trip)
    session.commit()
    session.refresh(trip)
    
    return {"message": f"Trip {'added to' if favorite else 'removed from'} favorites"}

# Modify the existing get_trips endpoint
@app.get("/trips/")
async def get_trips(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session),
    show_unpublished: bool = False,
    favorites_only: bool = False
):
    """
    Get all trips for the authenticated user.
    Optionally filter by published status and favorites.
    """
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    user_id = auth_result['sub']
    
    query = select(Trip).where(Trip.user_id == user_id)
    
    if not show_unpublished:
        query = query.where(Trip.is_published == True)
    
    if favorites_only:
        query = query.where(Trip.is_favorite == True)
    
    trips = session.exec(query).all()
    return trips



# User Profile Endpoints

@app.post("/users/profile")
async def create_user_profile(
    profile: UserProfile,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session)
):
    """Create or update a user's profile"""
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    user_id = auth_result.get('sub')
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Could not determine user ID from token")
    
    # Check if profile already exists
    existing_profile = session.exec(
        select(UserProfile).where(UserProfile.user_id == user_id)
    ).first()
    
    try:
        if existing_profile:
            # Update existing profile
            for key, value in profile.dict(exclude_unset=True).items():
                if key != 'id' and key != 'user_id':  # Protect these fields
                    setattr(existing_profile, key, value)
            existing_profile.updated_at = datetime.utcnow()
            profile = existing_profile
        else:
            # Create new profile
            profile.user_id = user_id
            profile.created_at = datetime.utcnow()
            profile.updated_at = datetime.utcnow()
        
        session.add(profile)
        session.commit()
        session.refresh(profile)
        return profile
        
    except Exception as e:
        session.rollback()
        print(f"Error creating/updating profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/profile")
async def get_user_profile(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session)
):
    """Get the current user's profile"""
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    user_id = auth_result.get('sub')
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Could not determine user ID from token")
    
    profile = session.exec(
        select(UserProfile).where(UserProfile.user_id == user_id)
    ).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return profile

@app.put("/users/profile")
async def update_user_profile(
    profile_update: UserProfile,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session)
):
    """Update user profile"""
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    user_id = auth_result.get('sub')
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Could not determine user ID from token")
    
    existing_profile = session.exec(
        select(UserProfile).where(UserProfile.user_id == user_id)
    ).first()
    
    if not existing_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    try:
        # Update fields while protecting id and user_id
        for key, value in profile_update.dict(exclude_unset=True).items():
            if key != 'id' and key != 'user_id':
                setattr(existing_profile, key, value)
        
        existing_profile.updated_at = datetime.utcnow()
        session.add(existing_profile)
        session.commit()
        session.refresh(existing_profile)
        return existing_profile
        
    except Exception as e:
        session.rollback()
        print(f"Error updating profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/users/profile")
async def delete_user_profile(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session)
):
    """Delete user profile"""
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    user_id = auth_result.get('sub')
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Could not determine user ID from token")
    
    existing_profile = session.exec(
        select(UserProfile).where(UserProfile.user_id == user_id)
    ).first()
    
    if not existing_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    try:
        session.delete(existing_profile)
        session.commit()
        return {"message": "Profile deleted successfully"}
    except Exception as e:
        session.rollback()
        print(f"Error deleting profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Trip Endpoints

@app.post("/trips/create")
async def create_trip(
    trip: Trip,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session)
):
    """
    Create a new trip and generate its itinerary.
    Returns both the message and the created trip data.
    """
    try:
        if not credentials:
            raise HTTPException(status_code=403, detail="No authentication credentials provided")
        
        # Verify the token and get the user ID
        auth_result = verify_token(credentials.credentials)
        user_id = auth_result.get('sub')
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Could not determine user ID from token")
        
        # Set the user_id from the token
        trip.user_id = user_id
        print(f"Creating trip for user: {user_id}")
        
        # Save the trip
        session.add(trip)
        session.commit()
        session.refresh(trip)
        print(f"Created trip with ID: {trip.id}")
        
        # Generate itinerary using OpenAI
        itinerary_content = await generate_itinerary(trip)
        
        # Create daily itineraries
        current_date = trip.start_date
        day_number = 1
        
        while current_date <= trip.end_date:
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
        
        # Return both the message and the trip data
        response_data = {
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
        
        print("Returning response data:", response_data)
        return response_data
    
    except HTTPException as he:
        session.rollback()
        raise he
    except Exception as e:
        session.rollback()
        print(f"Error creating trip: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trips/")
async def get_trips(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session),
    show_unpublished: bool = False,
    favorites_only: bool = False
):
    """
    Get all trips for the authenticated user.
    Optionally filter by published status and favorites.
    """
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    user_id = auth_result['sub']
    
    query = select(Trip).where(Trip.user_id == user_id)
    
    # If show_unpublished is False, only show published trips
    if not show_unpublished:
        query = query.where(Trip.is_published == True)
    
    if favorites_only:
        query = query.where(Trip.is_favorite == True)
    
    trips = session.exec(query).all()
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