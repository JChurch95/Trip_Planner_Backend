import uvicorn
from typing import Annotated, Optional
import jwt
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select, delete
from datetime import datetime, timedelta
from db import get_session, init_db
from config import SUPABASE_SECRET_KEY, JWT_ALGORITHM
from models.trips import Trip
from models.itineraries import Accommodation, DailyItinerary, TravelTips  # Updated import
from models.user_profile import UserProfile, TravelerType, ActivityLevel
from services.openai_service import OpenAIService
import json
import traceback

app = FastAPI(
    title="Trip Planner API",
    description="API for managing travel itineraries",
    version="1.0.0",
)

origins = [
    "http://localhost:5173",
    "http://localhost:8000",
    "http://127.0.0.1:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.swagger_ui_init_oauth = {
    "usePkceWithAuthorizationCodeGrant": True,
}

security_scheme = {
    "Bearer": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Enter your JWT token in the format: Bearer <token>"
    }
}

app.openapi_components = {"securitySchemes": security_scheme}
app.openapi_security = [{"Bearer": []}]

def verify_token(token: str):
    """Verify JWT token from Supabase"""
    try:
        if token.startswith('Bearer '):
            token = token.split(' ')[1]
        
        try:
            payload = jwt.decode(
                token, 
                SUPABASE_SECRET_KEY,
                algorithms=["HS256", "JWS"],
                audience=["authenticated"]
            )
            return payload
        except jwt.InvalidTokenError as e:
            print(f"Token decode error: {str(e)}")
            raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token verification failed")

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

# Trip Creation and Management
@app.post("/trips/create")
async def create_trip(
    trip: Trip,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session)
):
    """Create a new trip and generate its itinerary."""
    try:
        # Validate credentials
        if not credentials:
            raise HTTPException(status_code=403, detail="No authentication credentials provided")
        
        auth_result = verify_token(credentials.credentials)
        user_id = auth_result.get('sub')
        
        print(f"\n=== Starting Trip Creation ===")
        print(f"User ID: {user_id}")
        print(f"Trip Details: {trip.dict()}")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Could not determine user ID from token")
        
        # Set the user ID and create the trip
        trip.user_id = user_id
        session.add(trip)
        session.commit()
        session.refresh(trip)
        
        try:
            # Get user profile for personalized recommendations
            user_profile = session.exec(
                select(UserProfile).where(UserProfile.user_id == user_id)
            ).first()
            
            print("\n=== Generating OpenAI Content ===")
            # Generate itinerary
            itinerary_content = await generate_itinerary(trip, user_profile)
            print("\nRaw OpenAI Response:")
            print(itinerary_content)
            
            print("\n=== Parsing OpenAI Response ===")
            structured_data = OpenAIService.parse_itinerary_response(itinerary_content)
            print("Parsed Data Structure:")
            print(json.dumps(structured_data, indent=2))
            
            # Debug checks for structured data
            print("\n=== Data Validation ===")
            print(f"Has accommodation data: {bool(structured_data.get('accommodation'))}")
            print(f"Accommodation count: {len(structured_data.get('accommodation', []))}")
            print(f"Has daily itinerary data: {bool(structured_data.get('daily_itinerary'))}")
            print(f"Daily itinerary count: {len(structured_data.get('daily_itinerary', []))}")
            
            # Create accommodations if available
            if structured_data.get('accommodation'):
                print("\n=== Creating Accommodations ===")
                for hotel in structured_data['accommodation']:
                    print(f"Creating accommodation: {hotel.get('name')}")
                    accommodation = Accommodation(
                        trip_id=trip.id,
                        name=hotel.get('name', 'TBD'),
                        description=hotel.get('description', ''),
                        location=hotel.get('location', ''),
                        rating=hotel.get('rating', 0.0),
                        website_url=hotel.get('website_url'),
                        unique_features=hotel.get('unique_features'),
                        price_range=hotel.get('price_range')
                    )
                    session.add(accommodation)
                    print(f"Added accommodation to session: {accommodation.dict()}")
            
            # Create daily itineraries if available
            if structured_data.get('daily_itinerary'):
                print("\n=== Creating Daily Itineraries ===")
                current_date = trip.start_date
                for day_number, day_data in enumerate(structured_data['daily_itinerary'], 1):
                    print(f"\nProcessing Day {day_number}")
                    print(f"Day data: {json.dumps(day_data, indent=2)}")
                    daily_itinerary = DailyItinerary(
                        trip_id=trip.id,
                        day_number=day_number,
                        date=current_date,
                        breakfast_spot=day_data.get('breakfast', {}).get('name', ''),
                        breakfast_rating=day_data.get('breakfast', {}).get('rating', 0.0),
                        morning_activity=day_data.get('morning', {}).get('activity', ''),
                        morning_activity_time=day_data.get('morning', {}).get('time', ''),
                        morning_activity_location=day_data.get('morning', {}).get('location', ''),
                        morning_activity_url=day_data.get('morning', {}).get('url'),
                        lunch_spot=day_data.get('lunch', {}).get('name', ''),
                        lunch_rating=day_data.get('lunch', {}).get('rating', 0.0),
                        afternoon_activity=day_data.get('afternoon', {}).get('activity', ''),
                        afternoon_activity_time=day_data.get('afternoon', {}).get('time', ''),
                        afternoon_activity_location=day_data.get('afternoon', {}).get('location', ''),
                        afternoon_activity_url=day_data.get('afternoon', {}).get('url'),
                        dinner_spot=day_data.get('dinner', {}).get('name', ''),
                        dinner_rating=day_data.get('dinner', {}).get('rating', 0.0),
                        evening_activity=day_data.get('evening', {}).get('activity', ''),
                        evening_activity_time=day_data.get('evening', {}).get('time', ''),
                        evening_activity_location=day_data.get('evening', {}).get('location', ''),
                        evening_activity_url=day_data.get('evening', {}).get('url')
                    )
                    print(f"Created itinerary object: {daily_itinerary.dict()}")
                    session.add(daily_itinerary)
                    current_date += timedelta(days=1)
            
            print("\n=== Committing to Database ===")
            session.commit()
            print("Database commit successful")
            
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
        print(f"\nERROR in trip creation: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Error traceback: {traceback.format_exc()}")
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/trips")  # Note: no trailing slash
async def get_trips(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session),
    show_unpublished: bool = False,
    favorites_only: bool = False
):
    """Get all trips for the authenticated user."""
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    user_id = auth_result['sub']
    
    print(f"Fetching trips for user: {user_id}")  # Add debugging
    print(f"Filters - show_unpublished: {show_unpublished}, favorites_only: {favorites_only}")
    
    query = select(Trip).where(Trip.user_id == user_id)
    
    if not show_unpublished:
        query = query.where(Trip.is_published == True)
    
    if favorites_only:
        query = query.where(Trip.is_favorite == True)
    
    trips = session.exec(query).all()
    print(f"Found {len(trips)} trips")  # Add debugging
    
    return trips

@app.delete("/trips/{trip_id}")
async def delete_trip(
    trip_id: int,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session)
):
    """Delete a trip and all associated data."""
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    user_id = auth_result['sub']
    
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if trip.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this trip")
    
    # Delete all associated data
    session.exec(delete(DailyItinerary).where(DailyItinerary.trip_id == trip_id))
    session.exec(delete(Accommodation).where(Accommodation.trip_id == trip_id))
    session.exec(delete(TravelTips).where(TravelTips.trip_id == trip_id))
    session.delete(trip)
    session.commit()
    
    return {"message": "Trip and all associated data deleted successfully"}

# Daily Itinerary Endpoints
@app.get("/trips/{trip_id}/daily-itineraries")
async def get_daily_itineraries(
    trip_id: int,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session)
):
    """Get all daily itineraries for a trip."""
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    user_id = auth_result['sub']
    
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view these itineraries")
    
    print(f"Fetching itineraries for trip {trip_id}")
    daily_itineraries = session.exec(
        select(DailyItinerary)
        .where(DailyItinerary.trip_id == trip_id)
        .order_by(DailyItinerary.day_number)
    ).all()
    print(f"Found {len(daily_itineraries)} itineraries")
    
    return daily_itineraries

@app.put("/trips/{trip_id}/daily-itineraries/{day_number}")
async def update_daily_itinerary(
    trip_id: int,
    day_number: int,
    itinerary_update: DailyItinerary,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session)
):
    """Update a specific daily itinerary."""
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    user_id = auth_result['sub']
    
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this itinerary")
    
    existing_itinerary = session.exec(
        select(DailyItinerary)
        .where(DailyItinerary.trip_id == trip_id)
        .where(DailyItinerary.day_number == day_number)
    ).first()
    
    if not existing_itinerary:
        raise HTTPException(status_code=404, detail="Daily itinerary not found")
    
    update_data = itinerary_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(existing_itinerary, key, value)
    
    session.add(existing_itinerary)
    session.commit()
    session.refresh(existing_itinerary)
    
    return existing_itinerary

# Accommodation Endpoints
@app.get("/trips/{trip_id}/accommodations")
async def get_accommodations(
    trip_id: int,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session)
):
    """Get all accommodations for a trip."""
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    user_id = auth_result['sub']
    
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view these accommodations")
    
    accommodations = session.exec(
        select(Accommodation)
        .where(Accommodation.trip_id == trip_id)
    ).all()
    
    return accommodations

@app.put("/trips/{trip_id}/accommodations/{accommodation_id}")
async def update_accommodation(
    trip_id: int,
    accommodation_id: int,
    accommodation_update: Accommodation,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session)
):
    """Update a specific accommodation."""
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    user_id = auth_result['sub']
    
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this accommodation")
    
    existing_accommodation = session.get(Accommodation, accommodation_id)
    if not existing_accommodation or existing_accommodation.trip_id != trip_id:
        raise HTTPException(status_code=404, detail="Accommodation not found")
    
    update_data = accommodation_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(existing_accommodation, key, value)
    
    session.add(existing_accommodation)
    session.commit()
    session.refresh(existing_accommodation)
    
    return existing_accommodation

# Travel Tips Endpoints
@app.get("/trips/{trip_id}/travel-tips")
async def get_travel_tips(
    trip_id: int,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session)
):
    """Get travel tips for a trip."""
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    user_id = auth_result['sub']
    
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view these travel tips")
    
    travel_tips = session.exec(
        select(TravelTips)
        .where(TravelTips.trip_id == trip_id)
    ).first()
    
    if not travel_tips:
        raise HTTPException(status_code=404, detail="Travel tips not found")
    
    return travel_tips

@app.put("/trips/{trip_id}/travel-tips")
async def update_travel_tips(
    trip_id: int,
    tips_update: TravelTips,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session)
):
    """Update travel tips for a trip."""
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    user_id = auth_result['sub']
    
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update these travel tips")
    
    existing_tips = session.exec(
        select(TravelTips)
        .where(TravelTips.trip_id == trip_id)
    ).first()
    
    if not existing_tips:
        raise HTTPException(status_code=404, detail="Travel tips not found")
    
    update_data = tips_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(existing_tips, key, value)
    
    session.add(existing_tips)
    session.commit()
    session.refresh(existing_tips)
    
    return existing_tips

@app.get("/trips/{trip_id}/details")
async def get_trip_details(
    trip_id: int,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    session: Session = Depends(get_session)
):
    """Get basic details for a specific trip."""
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    auth_result = verify_token(credentials.credentials)
    user_id = auth_result['sub']
    
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this trip")
    
    return {
        "id": trip.id,
        "destination": trip.destination,
        "start_date": trip.start_date,
        "end_date": trip.end_date,
        "user_id": trip.user_id,
        "is_published": trip.is_published,
        "is_favorite": trip.is_favorite
    }

# Initialize database on startup
@app.on_event("startup")
async def on_startup():
    init_db()

# Run the application
if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)