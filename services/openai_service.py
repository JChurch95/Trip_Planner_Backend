import os
from openai import OpenAI
from typing import Optional
import re
import unicodedata
import traceback
import json
from datetime import datetime, date

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

class OpenAIService:
    SYSTEM_INSTRUCTIONS = """You are a travel planning API that MUST return responses in this exact JSON format. Your response must be valid JSON only - no other text or content is allowed.

Required format:
{
  "accommodation": [
    {
      "name": "string (required)",
      "description": "string (2-3 sentences, required)",
      "location": "string (required)",
      "rating": "number between 4.2 and 5.0 (required)",
      "unique_features": "string (required)",
      "nightly_rate": "number (required, NEVER use currency symbols, just the numeric value)",
      "url": "string URL (required)"
    }
  ],
  "daily_schedule": [
    {
      "day_number": "number (required)",
      "date": "YYYY-MM-DD (required)",
      "breakfast": {
        "spot": "string (required)",
        "rating": "number between 4.2 and 5.0 (required)",
        "description": "string (1-2 sentences, required)",
        "url": "string URL (required)"
      },
      "morning_activity": {
        "activity": "string (required)",
        "description": "string (2-3 sentences, required)",
        "url": "string URL (required)"
      },
      "lunch": {
        "spot": "string (required)",
        "rating": "number between 4.2 and 5.0 (required)",
        "description": "string (1-2 sentences, required)",
        "url": "string URL (required)"
      },
      "afternoon_activity": {
        "activity": "string (required)",
        "description": "string (2-3 sentences, required)",
        "url": "string URL (required)"
      },
      "dinner": {
        "spot": "string (required)",
        "rating": "number between 4.2 and 5.0 (required)",
        "description": "string (1-2 sentences, required)",
        "url": "string URL (required)"
      },
      "evening_activity": {
        "activity": "string (required)",
        "description": "string (2-3 sentences, required)",
        "url": "string URL (required)"
      }
    }
  ],
  "travel_tips": {
    "weather": "string (required)",
    "transportation": "string (required)",
    "cultural_notes": "string (required)"
  }
}

STRICT REQUIREMENTS:
1. Response MUST be valid JSON and ONLY JSON
2. ALL fields marked (required) MUST be present and non-empty
3. ALL dates must be in YYYY-MM-DD format
4. ALL ratings must be between 4.2 and 5.0
5. Include exactly 3 hotels in accommodation array
6. URLs must be real, official websites for the mentioned places/activities
7. URLs should link to the official business website or a reliable booking/information page
8. URLs do not need to match the business name exactly
9. Include a daily_schedule entry for EACH day of the trip
10. NEVER include additional fields or objects
11. NEVER include explanatory text or comments
12. NEVER use null values - use empty strings for optional fields
13. Each day must have different activities and dining spots
14. Nightly rate should be a **numeric value ONLY** with **no currency symbols**, such as `100`. The value should be a whole number, not a decimal.
15. NEVER use control characters or non-printable characters in the JSON response.

STRICT BUDGET RESTRICTIONS:
1. For budget_preference "BUDGET": total daily cost including accommodation must be $100-200
2. For budget_preference "COMFORT": total daily cost including accommodation must be $200-400
3. For budget_preference "PREMIUM": total daily cost including accommodation must be $400-800
4. For budget_preference "LUXURY": total daily cost including accommodation must be $800-1500
5. For budget_preference "ULTRA_LUXURY": total daily cost including accommodation must be $1500+
6. ALL accommodation and dining choices must fit within these daily budget ranges
7. Daily budget must cover accommodation, meals, and activities
8. Restaurant and activity choices should align with the budget tier
"""

    # Add this right after SYSTEM_INSTRUCTIONS and before generate_trip_plan
    @staticmethod
    def validate_response_structure(data: dict) -> bool:
        """Validate the OpenAI response matches our required schema."""
        try:
            # Validate accommodation
            if not isinstance(data.get('accommodation'), list) or len(data['accommodation']) == 0:
                return False
            
            for hotel in data['accommodation']:
                required_hotel_fields = ['name', 'description', 'location', 'rating', 'unique_features', 'nightly_rate', 'url']
                if not all(field in hotel for field in required_hotel_fields):
                    return False
                if not (4.2 <= float(hotel['rating']) <= 5.0):
                    return False

            # Validate daily_schedule
            if not isinstance(data.get('daily_schedule'), list) or len(data['daily_schedule']) == 0:
                return False
                    
            for day in data['daily_schedule']:
                required_day_fields = ['day_number', 'date', 'breakfast', 'morning_activity', 
                                    'lunch', 'afternoon_activity', 'dinner', 'evening_activity']
                if not all(field in day for field in required_day_fields):
                    return False
                    
                # Validate date format
                try:
                    datetime.strptime(day['date'], '%Y-%m-%d')
                except ValueError:
                    return False
                    
                # Validate meal entries
                for meal in ['breakfast', 'lunch', 'dinner']:
                    if not all(field in day[meal] for field in ['spot', 'rating', 'description', 'url']):
                        return False
                    if not (4.2 <= float(day[meal]['rating']) <= 5.0):
                        return False
                    
                # Validate activities
                for activity in ['morning_activity', 'afternoon_activity', 'evening_activity']:
                    if not all(field in day[activity] for field in ['activity', 'description', 'url']):
                        return False

            # Validate travel_tips
            required_tips_fields = ['weather', 'transportation', 'cultural_notes']
            if not all(field in data.get('travel_tips', {}) for field in required_tips_fields):
                return False

            return True

        except (TypeError, ValueError, KeyError):
            return False

    @staticmethod
    async def generate_trip_plan(prompt: str) -> str:
        """Generate itinerary using OpenAI."""
        try:
            response = client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=[
                    {"role": "system", "content": OpenAIService.SYSTEM_INSTRUCTIONS},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            if not response.choices:
                raise Exception("No response generated from OpenAI")
            
            # The response is already valid JSON, just return it directly
            return response.choices[0].message.content
                
        except Exception as e:
            print(f"Error generating trip plan: {str(e)}")
            raise



    @staticmethod
    def parse_itinerary_response(response_text: str) -> dict:
        """Parse OpenAI response from JSON format into structured data."""
        try:
            # Direct parse of the JSON response
            parsed_data = json.loads(response_text)
            
            # Add validation check
            if OpenAIService.validate_response_structure(parsed_data):
                print("\n=== Successfully parsed and validated JSON response ===")
                return parsed_data
                
            print("\n=== JSON parsed but failed validation, returning default structure ===")
            return {
                "accommodation": [{
                    "name": "Default Hotel",
                    "description": "Hotel information not available",
                    "location": "Location not available",
                    "rating": 4.2,
                    "unique_features": [],
                    "nightly_rate": "Price not available",
                    "website": None
                }],
                "daily_schedule": [{
                    "day_number": 1,
                    "date": date.today().isoformat(),
                    "breakfast": {"spot": "", "rating": 4.2, "description": "", "url": None},
                    "morning_activity": {"activity": "", "description": "", "url": None},
                    "lunch": {"spot": "", "rating": 4.2, "description": "", "url": None},
                    "afternoon_activity": {"activity": "", "description": "", "url": None},
                    "dinner": {"spot": "", "rating": 4.2, "description": "", "url": None},
                    "evening_activity": {"activity": "", "description": "", "url": None}
                }],
                "travel_tips": {
                    "weather": "Weather information not available",
                    "transportation": "Transportation information not available",
                    "cultural_notes": "Cultural information not available"
                }
            }
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {str(e)}")
            # Return the default structure if parsing fails
            return {
                # Same default structure as above
            }


    @staticmethod
    def _parse_meal(text: str) -> dict:
        """Parse meal details from text into structured format."""
        result = {
            "spot": "",
            "rating": 0.0,
            "description": "",
            "url": None
        }
        
        # Remove the prefix (e.g., "Breakfast:", "Lunch:", "Dinner:")
        text = re.sub(r'^[^:]+:\s*', '', text)
        
        # Extract URL if present
        url_match = re.search(r'\((https?://[^\s)]+)\)', text)
        if url_match:
            result['url'] = url_match.group(1)
            text = re.sub(r'\([^)]+\)', '', text)
        
        # Extract rating if present
        rating_match = re.search(r'(\d+\.?\d*)', text)
        if rating_match:
            try:
                result['rating'] = float(rating_match.group(1))
            except ValueError:
                pass
            text = re.sub(r'\(.*?\)', '', text)
        
        # Split remaining text into spot and description
        parts = text.split(' - ', 1)
        result['spot'] = parts[0].strip()
        if len(parts) > 1:
            result['description'] = parts[1].strip()
        
        return result

    @staticmethod
    def _parse_activity(text: str) -> dict:
        """Parse activity details from text into structured format."""
        result = {
            "activity": "",
            "description": "",
            "url": None
        }
        
        # Remove the prefix (e.g., "Morning Activity:", etc.)
        text = re.sub(r'^[^:]+:\s*', '', text)
        
        # Extract URL if present
        url_match = re.search(r'\((https?://[^\s)]+)\)', text)
        if url_match:
            result['url'] = url_match.group(1)
            text = re.sub(r'\([^)]+\)', '', text)
        
        # Split remaining text into activity and description
        parts = text.split(' - ', 1)
        result['activity'] = parts[0].strip()
        if len(parts) > 1:
            result['description'] = parts[1].strip()
        
        return result

    @staticmethod
    def _parse_accommodation(text: str) -> list[dict]:
        """Parse hotel details into structured format."""
        hotels = []
        current_hotel = {}
        
        for line in text.split('\n'):
            line = line.strip()
            if not line or line == 'ACCOMMODATION:':
                continue
                
            # Parse hotel details
            if line.startswith('- Name:'):
                if current_hotel:
                    hotels.append(current_hotel)
                current_hotel = {
                    "name": line.replace('- Name:', '').strip(),
                    "description": "",
                    "location": "",
                    "rating": 0.0,
                    "unique_features": [],
                    "nightly_rate": "",
                    "website": None
                }
            elif 'Description:' in line:
                current_hotel['description'] = line.split('Description:', 1)[1].strip()
            elif 'Location:' in line:
                current_hotel['location'] = line.split('Location:', 1)[1].strip()
            elif 'Rating:' in line:
                try:
                    current_hotel['rating'] = float(re.search(r'(\d+\.?\d*)', line).group(1))
                except (AttributeError, ValueError):
                    pass
            elif 'Unique Features:' in line:
                current_hotel['unique_features'] = [
                    f.strip() for f in line.split('Unique Features:', 1)[1].split(',')
                ]
            elif 'Nightly Rate:' in line:
                current_hotel['nightly_rate'] = line.split('Nightly Rate:', 1)[1].strip()
            elif 'Website:' in line:
                website_match = re.search(r'\((.*?)\)', line)
                if website_match:
                    current_hotel['website'] = website_match.group(1)
        
        if current_hotel:
            hotels.append(current_hotel)
        
        return hotels

    @staticmethod
    def _parse_daily_activities(text: str) -> list[dict]:
        """Parse daily activities into structured format."""
        days = []
        current_day = None
        
        for line in text.split('\n'):
            line = line.strip()
            if not line or line == 'DAILY ITINERARY:':
                continue
                
            day_match = re.match(r'Day (\d+) - (\d{4}-\d{2}-\d{2}):', line)
            if day_match:
                if current_day:
                    days.append(current_day)
                current_day = {
                    "day_number": int(day_match.group(1)),
                    "date": day_match.group(2),
                    "breakfast": {"spot": "", "rating": 0.0, "description": "", "url": None},
                    "morning_activity": {"activity": "", "description": "", "url": None},
                    "lunch": {"spot": "", "rating": 0.0, "description": "", "url": None},
                    "afternoon_activity": {"activity": "", "description": "", "url": None},
                    "dinner": {"spot": "", "rating": 0.0, "description": "", "url": None},
                    "evening_activity": {"activity": "", "description": "", "url": None}
                }
            elif current_day:
                if line.startswith('Breakfast:'):
                    current_day['breakfast'] = OpenAIService._parse_meal(line)
                elif line.startswith('Morning Activity:'):
                    current_day['morning_activity'] = OpenAIService._parse_activity(line)
                elif line.startswith('Lunch:'):
                    current_day['lunch'] = OpenAIService._parse_meal(line)
                elif line.startswith('Afternoon Activity:'):
                    current_day['afternoon_activity'] = OpenAIService._parse_activity(line)
                elif line.startswith('Dinner:'):
                    current_day['dinner'] = OpenAIService._parse_meal(line)
                elif line.startswith('Evening Activity:'):
                    current_day['evening_activity'] = OpenAIService._parse_activity(line)
        
        if current_day:
            days.append(current_day)
        
        return days

    @staticmethod
    def _parse_travel_tips(text: str) -> dict:
        """Parse travel tips into structured format."""
        tips = {}
        current_tip = None
        
        for line in text.split('\n'):
            line = line.strip()
            if not line or line == 'TRAVEL TIPS:':
                continue
                
            if line.startswith('Weather:'):
                current_tip = 'weather'
                tips['weather'] = line.split('Weather:', 1)[1].strip()
            elif line.startswith('Transportation:'):
                current_tip = 'transportation'
                tips['transportation'] = line.split('Transportation:', 1)[1].strip()
            elif line.startswith('Cultural Notes:'):
                current_tip = 'cultural_notes'
                tips['cultural_notes'] = line.split('Cultural Notes:', 1)[1].strip()
            elif current_tip and line:
                tips[current_tip] += ' ' + line
        
        return tips
