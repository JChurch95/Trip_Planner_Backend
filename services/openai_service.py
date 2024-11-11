import os
from openai import OpenAI
from typing import Optional
import re
import traceback
import json
from datetime import datetime, date

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

class OpenAIService:
    # Keep your original system instructions exactly as they were
    SYSTEM_INSTRUCTIONS = """You are a travel planner. Create personalized, easy-to-read itinerary based on the user's:
- Destination city
- Trip duration
- Interests and travel preferences
- Profile settings
- Local events during their stay
- Weather conditions

For each itinerary, provide the following:

1. ACCOMMODATION (List exactly 3 hotels)
- List 3 highly-rated hotels with ratings of 4.4 and higher
- Include brief description, location, and unique features
- Make hotel names clickable links to their websites
- For each hotel provide: name, URL, description, location, rating, and any unique features

2. DAILY ITINERARY
For each day, organize recommendations into three sections:

Morning:
- Breakfast: Popular local spot (4.4+ rating)
- Activity (Time): Description and location with clickable website link

Afternoon:
- Lunch: Top-rated spot (4.4+ rating)
- Activity (Time): Description and location with clickable website link

Evening:
- Dinner: Popular spot (4.4+ rating)
- Activity (Time): Description and location with clickable website link

3. TRAVEL TIPS
- Weather Considerations: Expected conditions and clothing suggestions
- Local Transportation: Navigation tips
- Cultural Etiquette: Essential customs and practices
- Seasonal Events: Special events during the visit

Ensure all recommendations are:
- Verified with 4.4+ ratings
- Include accurate timings
- Geographically logical to minimize travel time
- Aligned with user preferences and budget
- Include clickable website links where applicable"""

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
                temperature=0.7,
                max_tokens=3500
            )
            
            if not response.choices:
                raise Exception("No response generated from OpenAI")
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error generating trip plan: {str(e)}")
            raise

    @staticmethod
    def parse_itinerary_response(response_text: str) -> dict:
        """Parse OpenAI response to match database models exactly."""
        print("\n=== Starting Response Parsing ===")
        
        def extract_link_data(text: str) -> tuple[str, Optional[str]]:
            """Extract name and URL from markdown link."""
            match = re.match(r'\[(.*?)\]\((.*?)\)', text)
            return (match.group(1).strip(), match.group(2).strip()) if match else (text.strip(), None)
        
        def extract_rating(text: str) -> float:
            """Extract rating value from text."""
            try:
                match = re.search(r'\((\d+\.\d+)\)', text)
                return float(match.group(1)) if match else 0.0
            except (ValueError, AttributeError):
                return 0.0

        def parse_accommodation(text: str) -> dict:
            """Parse hotel details to match Accommodation model."""
            lines = text.strip().split('\n')
            hotel = {
                'name': '',
                'description': '',
                'location': '',
                'rating': 0.0,
                'website_url': None,
                'unique_features': None,
                'price_range': None
            }
            
            name_line = next((line for line in lines if '[' in line and ']' in line), None)
            if name_line:
                hotel['name'], hotel['website_url'] = extract_link_data(name_line)
                
            description_text = []
            for line in lines:
                line = line.strip()
                if line.startswith('-'):
                    line = line[1:].strip()
                    
                if 'rating' in line.lower():
                    hotel['rating'] = extract_rating(line)
                elif 'location' in line.lower():
                    hotel['location'] = line.split(':', 1)[1].strip() if ':' in line else ''
                elif 'unique features' in line.lower():
                    hotel['unique_features'] = line.split(':', 1)[1].strip() if ':' in line else ''
                elif 'description' in line.lower():
                    description_text.append(line.split(':', 1)[1].strip() if ':' in line else '')
            
            hotel['description'] = ' '.join(description_text)
            return hotel

        def parse_activity(text: str) -> tuple[str, str, str, Optional[str]]:
            """Parse activity details to match model fields exactly."""
            activity = ""
            time = ""
            location = ""
            url = None
            
            # Extract name and URL
            name_match = re.search(r'\[(.*?)\]\((.*?)\)', text)
            if name_match:
                activity = name_match.group(1).strip()
                url = name_match.group(2).strip()
            
            # Extract time (HH:MM AM/PM format)
            time_match = re.search(r'\(([\d:]+(?:\s*[AaPp][Mm])?(?:\s*-\s*[\d:]+(?:\s*[AaPp][Mm])?)?)\)', text)
            if time_match:
                time = time_match.group(1).strip()
            
            # Extract location after @
            location_match = re.search(r'@\s*([^(]+)', text)
            if location_match:
                location = location_match.group(1).strip()
            
            return activity, time, location, url

        def parse_meal(text: str) -> tuple[str, float, Optional[str]]:
            """Parse meal details to match model fields exactly."""
            name, url = extract_link_data(text)
            rating = extract_rating(text)
            return name, rating, url

        try:
            sections = {
                'accommodation': [],
                'daily_itinerary': [],
                'travel_tips': {
                    'weather_summary': '',
                    'transportation_tips': '',
                    'cultural_notes': '',
                    'seasonal_events': None
                }
            }
            
            current_section = None
            current_hotel = []
            current_day = None
            day_count = 0
            
            for line in response_text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                # Detect sections
                if 'ACCOMMODATION' in line.upper():
                    current_section = 'accommodation'
                    continue
                elif 'DAILY ITINERARY' in line.upper():
                    if current_hotel:
                        sections['accommodation'].append(parse_accommodation('\n'.join(current_hotel)))
                        current_hotel = []
                    current_section = 'daily_itinerary'
                    continue
                elif 'TRAVEL TIPS' in line.upper():
                    if current_hotel:
                        sections['accommodation'].append(parse_accommodation('\n'.join(current_hotel)))
                        current_hotel = []
                    if current_day:
                        sections['daily_itinerary'].append(current_day)
                    current_section = 'travel_tips'
                    continue

                # Process each section
                if current_section == 'accommodation':
                    if line.startswith('[') and current_hotel:
                        sections['accommodation'].append(parse_accommodation('\n'.join(current_hotel)))
                        current_hotel = []
                    current_hotel.append(line)
                
                elif current_section == 'daily_itinerary':
                    if line.startswith('Day'):
                        day_count += 1
                        if current_day:
                            sections['daily_itinerary'].append(current_day)
                        
                        current_day = {
                            'day_number': day_count,
                            'date': datetime.strptime(re.search(r'\d{4}-\d{2}-\d{2}', line).group(), '%Y-%m-%d').date() if re.search(r'\d{4}-\d{2}-\d{2}', line) else None,
                            'breakfast_spot': '',
                            'breakfast_rating': 0.0,
                            'morning_activity': '',
                            'morning_activity_time': '',
                            'morning_activity_location': '',
                            'morning_activity_url': None,
                            'lunch_spot': '',
                            'lunch_rating': 0.0,
                            'afternoon_activity': '',
                            'afternoon_activity_time': '',
                            'afternoon_activity_location': '',
                            'afternoon_activity_url': None,
                            'dinner_spot': '',
                            'dinner_rating': 0.0,
                            'evening_activity': '',
                            'evening_activity_time': '',
                            'evening_activity_location': '',
                            'evening_activity_url': None
                        }
                    
                    elif current_day and line.startswith('-'):
                        if ': ' in line:
                            key, value = line.split(': ', 1)
                            key = key.strip('- ').lower()
                            
                            if 'breakfast' in key:
                                name, rating, url = parse_meal(value)
                                current_day['breakfast_spot'] = name
                                current_day['breakfast_rating'] = rating
                            elif 'morning activity' in key:
                                activity, time, location, url = parse_activity(value)
                                current_day['morning_activity'] = activity
                                current_day['morning_activity_time'] = time
                                current_day['morning_activity_location'] = location
                                current_day['morning_activity_url'] = url
                            elif 'lunch' in key:
                                name, rating, url = parse_meal(value)
                                current_day['lunch_spot'] = name
                                current_day['lunch_rating'] = rating
                            elif 'afternoon activity' in key:
                                activity, time, location, url = parse_activity(value)
                                current_day['afternoon_activity'] = activity
                                current_day['afternoon_activity_time'] = time
                                current_day['afternoon_activity_location'] = location
                                current_day['afternoon_activity_url'] = url
                            elif 'dinner' in key:
                                name, rating, url = parse_meal(value)
                                current_day['dinner_spot'] = name
                                current_day['dinner_rating'] = rating
                            elif 'evening activity' in key:
                                activity, time, location, url = parse_activity(value)
                                current_day['evening_activity'] = activity
                                current_day['evening_activity_time'] = time
                                current_day['evening_activity_location'] = location
                                current_day['evening_activity_url'] = url
                
                elif current_section == 'travel_tips' and ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if 'weather' in key:
                        sections['travel_tips']['weather_summary'] = value
                    elif 'transportation' in key:
                        sections['travel_tips']['transportation_tips'] = value
                    elif 'cultural' in key or 'etiquette' in key:
                        sections['travel_tips']['cultural_notes'] = value
                    elif 'seasonal' in key:
                        sections['travel_tips']['seasonal_events'] = value

            # Add final hotel if exists
            if current_hotel:
                sections['accommodation'].append(parse_accommodation('\n'.join(current_hotel)))
            
            # Add final day if exists
            if current_day:
                sections['daily_itinerary'].append(current_day)

            print("\n=== Parsed Data Structure ===")
            print(json.dumps(sections, indent=2))
            
            return sections
            
        except Exception as e:
            print(f"Error parsing response: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return {
                'accommodation': [],
                'daily_itinerary': [],
                'travel_tips': {
                    'weather_summary': '',
                    'transportation_tips': '',
                    'cultural_notes': '',
                    'seasonal_events': None
                }
            }