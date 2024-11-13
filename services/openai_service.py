import os
from openai import OpenAI
from typing import Optional
import re
import traceback
import json
from datetime import datetime, date

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

class OpenAIService:
    SYSTEM_INSTRUCTIONS = """You are a travel planner. Create personalized, easy-to-read itineraries based on the user's:
- Destination city
- Trip duration
- Interests and travel preferences
- Budget constraints (strictly adhere to these)
- Profile settings
- Local events during their stay
- Weather conditions

BUDGET CATEGORIES AND GUIDELINES:
- BUDGET ($50-100 per day):
  * Hotels: Quality budget accommodations ($20-40/night)
    - Well-rated hostels
    - Guesthouses
    - B&Bs
    - Budget hotels
    Only venues with a user rating of 4.0 or higher (out of 5) will be selected.
  * Meals: Local eateries, street food, casual restaurants ($10-20/meal)
  * Activities: Free or low-cost attractions, walking tours, public spaces

- COMFORT ($100-200 per day):
  * Hotels: Mid-range accommodations ($40-80/night)
    - Quality 2-3 star hotels
    - Boutique guesthouses
    - Serviced apartments
    - Small boutique hotels
    Only venues with a user rating of 4.0 or higher (out of 5) will be selected.
  * Meals: Mid-range restaurants, casual dining ($20-40/meal)
  * Activities: Mix of paid attractions and free activities

- PREMIUM ($200-500 per day):
  * Hotels: High-end accommodations ($80-200/night)
    - Quality 3-4 star hotels
    - Boutique hotels
    - Luxury apartments
    - Small luxury properties
    Only venues with a user rating of 4.0 or higher (out of 5) will be selected.
  * Meals: Fine dining, trendy restaurants ($40-80/meal)
  * Activities: Premium experiences, guided tours, special events

- LUXURY ($500-1000 per day):
  * Hotels: Luxury accommodations ($200-400/night)
    - 4-5 star hotels
    - Luxury boutique hotels
    - High-end resorts
    - Premium luxury apartments
    Only venues with a user rating of 4.0 or higher (out of 5) will be selected.
  * Meals: High-end restaurants, michelin-starred venues ($80-150/meal)
  * Activities: VIP experiences, private tours, exclusive access

- ULTRA_LUXURY ($1000+ per day):
  * Hotels: Ultra-luxury accommodations ($400+/night)
    - 5-star hotels and resorts
    - Presidential suites
    - Exclusive luxury properties
    - Private villas
    Only venues with a user rating of 4.0 or higher (out of 5) will be selected.
  * Meals: World-class restaurants, private dining ($150+/meal)
  * Activities: Ultra-exclusive experiences, private guides, helicopter tours

IMPORTANT NOTE ABOUT ACCOMMODATIONS:
- All recommended accommodations MUST have user ratings of 4.2+ out of 5 on major travel platforms
- Star ratings (1-5 stars) indicate the official classification based on facilities/amenities
- User ratings 4.0 or higher (out of 5) reflect actual guest experiences and satisfaction
- Focus on finding accommodations that match both the budget category AND maintain high user ratings
- Consider factors like:
  * Recent renovations
  * Superior service
  * Excellent location
  * Outstanding cleanliness
  * Great value for money within their category

For each itinerary, provide the following within the specified budget category:

1. ACCOMMODATION (List exactly 3 hotels)
For each hotel, provide:
- Name with clickable website link
- Detailed description (2-3 sentences about amenities, style, and atmosphere)
- Precise location and proximity to attractions
- Official star rating (if applicable)
- User rating (MUST be 4.0 or higher (out of 5))
- Unique features or special offerings
- Price range category (must match user's budget preference)
- Typical nightly rate

2. DAILY ITINERARY
For each day, organize detailed recommendations into three sections:

Morning:
- Breakfast: Restaurant name (rating) - Include 1-2 sentences about cuisine style, atmosphere, and popular dishes
- Activity: Name (Time) @ Location
  * Detailed description of the activity (2-3 sentences)
  * What makes it special or worth visiting
  * Practical tips for visiting
  * Include website link

Afternoon:
- Lunch: Restaurant name (rating) - Include 1-2 sentences about cuisine style, atmosphere, and signature dishes
- Activity: Name (Time) @ Location
  * Detailed description of the activity (2-3 sentences)
  * Historical or cultural significance
  * What visitors can expect to see/do
  * Include website link

Evening:
- Dinner: Restaurant name (rating) - Include 1-2 sentences about cuisine style, ambiance, and must-try dishes
- Activity: Name (Time) @ Location
  * Detailed description of the activity (2-3 sentences)
  * Why it's worth experiencing
  * What makes it unique
  * Include website link

3. TRAVEL TIPS
- Weather Considerations: Detailed expected conditions and specific clothing suggestions
- Local Transportation: Comprehensive navigation tips including costs and recommended methods
- Cultural Etiquette: Essential customs, practices, and behavioral tips
- Seasonal Events: Special events during the visit with dates and brief descriptions, with website link if applicable

Ensure all recommendations:
- Have ratings of 4.4 or higher
- Include accurate timings and durations
- Are geographically logical to minimize travel time
- Align with user preferences and budget
- Include clickable website links
- Have detailed descriptions for all venues and activities"""

    @staticmethod
    async def generate_trip_plan(prompt: str) -> str:
        """Generate itinerary using OpenAI."""
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": OpenAIService.SYSTEM_INSTRUCTIONS},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000  # Increased token limit to accommodate more detailed descriptions
            )
            
            if not response.choices:
                raise Exception("No response generated from OpenAI")
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error generating trip plan: {str(e)}")
            raise

    @staticmethod
    def parse_itinerary_response(response_text: str) -> dict:
        """Parse OpenAI response into structured data matching the itinerary model."""
        print("\n=== Starting Response Parsing ===")
        
        def extract_link_data(text: str) -> tuple[str, Optional[str]]:
            """Extract name and URL from markdown link format."""
            link_pattern = r'\[(.*?)\]\((.*?)\)'
            match = re.search(link_pattern, text)
            if match:
                return match.group(1).strip(), match.group(2).strip()
            return text.strip(), None

        def extract_rating(text: str) -> float:
            """Extract rating value from text."""
            rating_pattern = r'(\d+\.\d+)'
            match = re.search(rating_pattern, text)
            return float(match.group(1)) if match else 0.0

        def extract_description(text: str) -> str:
            """Extract description from text after the rating or initial identifier."""
            # First, remove any markdown links
            text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
            # Then remove the rating if present
            text = re.sub(r'\(\d+\.?\d*\)', '', text)
            # Remove any leading identifiers like "Breakfast:", "Activity:", etc.
            text = re.sub(r'^(Breakfast|Lunch|Dinner|Activity|Morning|Afternoon|Evening):\s*', '', text)
            # Clean up and return the remaining text
            return text.strip()

        def parse_accommodation(text: str) -> list[dict]:
            """Parse hotel details into structured format."""
            hotels = []
            current_hotel = None
            
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if not line or line.lower() == 'accommodation':
                    continue
                    
                # Check for new hotel entry (starts with number and period)
                if re.match(r'^\d+\.', line):
                    # If we already have a hotel, add it to our list
                    if current_hotel:
                        hotels.append(current_hotel)
                    
                    # Start new hotel entry
                    hotel_name = line.split('.', 1)[1].strip()
                    # Extract name and website if in markdown link format
                    link_match = re.match(r'\[(.*?)\]\((.*?)\)', hotel_name)
                    if link_match:
                        name = link_match.group(1)
                        website = link_match.group(2)
                    else:
                        name = hotel_name
                        website = None
                        
                    current_hotel = {
                        "name": name,
                        "website": website,
                        "description": "",
                        "location": "",
                        "rating": 0.0,
                        "star_rating": 0,
                        "unique_features": "",
                        "price_range": "",
                        "nightly_rate": ""
                    }
                    
                elif current_hotel and line.startswith('-'):
                    detail = line[1:].strip()
                    
                    # Handle different detail types
                    if 'Location:' in detail:
                        current_hotel['location'] = detail.split(':', 1)[1].strip()
                    elif 'Official Star Rating:' in detail:
                        try:
                            current_hotel['star_rating'] = int(re.search(r'(\d+)', detail).group(1))
                        except (AttributeError, ValueError):
                            pass
                    elif 'User Rating:' in detail:
                        try:
                            current_hotel['rating'] = float(re.search(r'(\d+\.?\d*)', detail).group(1))
                        except (AttributeError, ValueError):
                            pass
                    elif 'Unique Features:' in detail:
                        current_hotel['unique_features'] = detail.split(':', 1)[1].strip()
                    elif 'Price Range Category:' in detail:
                        current_hotel['price_range'] = detail.split(':', 1)[1].strip()
                    elif 'Typical Nightly Rate:' in detail:
                        current_hotel['nightly_rate'] = detail.split(':', 1)[1].strip()
                    else:
                        # If no specific label, treat as part of description
                        if current_hotel['description']:
                            current_hotel['description'] += ' ' + detail
                        else:
                            current_hotel['description'] = detail
            
            # Don't forget to add the last hotel
            if current_hotel:
                hotels.append(current_hotel)
            
            return hotels

        def parse_daily_activities(text: str) -> list[dict]:
            """Parse daily activities into structured format."""
            daily_schedule = []
            current_day = None
            current_section = None
            day_pattern = re.compile(r'Day (\d+) - (\d{4}-\d{2}-\d{2}):')
            section_patterns = {
                'breakfast': re.compile(r'Breakfast:\s*(.*?)(?=\n|$)', re.DOTALL),
                'morning_activity': re.compile(r'Morning Activity:\s*(.*?)(?=\n|$)', re.DOTALL),
                'lunch': re.compile(r'Lunch:\s*(.*?)(?=\n|$)', re.DOTALL),
                'afternoon_activity': re.compile(r'Afternoon Activity:\s*(.*?)(?=\n|$)', re.DOTALL),
                'dinner': re.compile(r'Dinner:\s*(.*?)(?=\n|$)', re.DOTALL),
                'evening_activity': re.compile(r'Evening Activity:\s*(.*?)(?=\n|$)', re.DOTALL)
            }

            def parse_meal(text: str) -> dict:
                """Parse meal details including name and rating."""
                # Look for rating in parentheses, e.g. "Restaurant Name (4.5)"
                rating_match = re.search(r'\(([\d.]+)\)', text)
                rating = float(rating_match.group(1)) if rating_match else 0.0
                # Remove rating from name if present
                name = re.sub(r'\s*\([\d.]+\)', '', text).strip()
                # Get description if available (after the dash or hyphen)
                parts = name.split(' - ', 1)
                spot = parts[0].strip()
                description = parts[1].strip() if len(parts) > 1 else ""
                return {
                    "spot": spot,
                    "rating": rating,
                    "description": description
                }

            def parse_activity(text: str) -> dict:
                """Parse activity details including time and location."""
                # Pattern for time in parentheses and location after @
                time_match = re.search(r'\((.*?)\)', text)
                location_match = re.search(r'@\s*(.*?)(?=\.|$)', text)
                
                # Extract URL if present
                url_match = re.search(r'\[(.*?)\]\((.*?)\)', text)
                if url_match:
                    activity = url_match.group(1)
                    url = url_match.group(2)
                else:
                    # Remove time and location portions to get activity name
                    activity = text.split('(')[0].strip()
                    url = None
                    
                return {
                    "activity": activity,
                    "time": time_match.group(1) if time_match else "",
                    "location": location_match.group(1).strip() if location_match else "",
                    "url": url
                }

            # Split text into days
            days = text.split('\nDay ')
            for day_text in days:
                if not day_text.strip():
                    continue
                    
                if not day_text.startswith('Day '):
                    day_text = 'Day ' + day_text

                day_match = day_pattern.search(day_text)
                if day_match:
                    if current_day:
                        daily_schedule.append(current_day)

                    current_day = {
                        "day_number": int(day_match.group(1)),
                        "date": day_match.group(2),
                        "breakfast": {"spot": "", "rating": 0.0, "description": ""},
                        "morning_activity": {"activity": "", "time": "", "location": "", "url": None},
                        "lunch": {"spot": "", "rating": 0.0, "description": ""},
                        "afternoon_activity": {"activity": "", "time": "", "location": "", "url": None},
                        "dinner": {"spot": "", "rating": 0.0, "description": ""},
                        "evening_activity": {"activity": "", "time": "", "location": "", "url": None}
                    }

                    # Process each section
                    for section, pattern in section_patterns.items():
                        match = pattern.search(day_text)
                        if match:
                            content = match.group(1).strip()
                            if section in ['breakfast', 'lunch', 'dinner']:
                                current_day[section] = parse_meal(content)
                            else:
                                current_day[section] = parse_activity(content)

            # Don't forget to append the last day
            if current_day:
                daily_schedule.append(current_day)

            return daily_schedule

        def parse_travel_tips(text: str) -> dict:
            """Parse travel tips into structured format."""
            tips = {
                "weather": "",
                "transportation": "",
                "cultural_notes": "",
                "seasonal_events": ""
            }
            
            current_section = None
            for line in text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('Weather:'):
                    current_section = "weather"
                    tips["weather"] = line.split(':', 1)[1].strip()
                elif line.startswith('Transportation:'):
                    current_section = "transportation"
                    tips["transportation"] = line.split(':', 1)[1].strip()
                elif line.startswith('Cultural Notes:'):
                    current_section = "cultural_notes"
                    tips["cultural_notes"] = line.split(':', 1)[1].strip()
                elif line.startswith('Seasonal Events:'):
                    current_section = "seasonal_events"
                    tips["seasonal_events"] = line.split(':', 1)[1].strip()
                elif current_section and line:
                    tips[current_section] += " " + line

            return tips

        try:
            # Split the response into main sections
            sections = re.split(r'\n(?=ACCOMMODATION:|DAILY ITINERARY:|TRAVEL TIPS:)', response_text)
            parsed_data = {
                "accommodation": [],
                "daily_schedule": [],
                "travel_tips": {}
            }
            
            # Parse each section
            for section in sections:
                if section.strip().startswith('ACCOMMODATION:'):
                    parsed_data["accommodation"] = parse_accommodation(section)
                elif section.strip().startswith('DAILY ITINERARY:'):
                    parsed_data["daily_schedule"] = parse_daily_activities(section)
                elif section.strip().startswith('TRAVEL TIPS:'):
                    parsed_data["travel_tips"] = parse_travel_tips(section)

            print("\n=== Parsed Data Structure ===")
            print(json.dumps(parsed_data, indent=2))
            
            return parsed_data
            
        except Exception as e:
            print(f"Error parsing response: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return {
                "accommodation": [],
                "daily_schedule": [],
                "travel_tips": {
                    "weather": "",
                    "transportation": "",
                    "cultural_notes": "",
                    "seasonal_events": ""
                }
            }