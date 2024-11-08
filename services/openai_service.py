import os
from dotenv import load_dotenv
from openai import OpenAI
from typing import Optional

load_dotenv()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

class OpenAIService:
    SYSTEM_INSTRUCTIONS = """You are a travel planner. Create personalized travel itineraries based on the user's:
- Destination city
- Length of stay
- Travel preferences/interests

For each itinerary, provide:

1. ACCOMMODATION
- Recommend 2-3 highly-rated hotels (4.4+ rating or higher)

2. DAILY ITINERARY
For each day, break down by:
Morning:
- Activity recommendations with times
- Local breakfast spot (4.4+ rated or higher)

Afternoon:
- Activity recommendations with times
- Local lunch spot (4.4+ rated or higher)

Evening:
- Activity recommendations with times
- Local dinner spot (4.4+ rated or higher)

3. TRAVEL TIPS
- Weather considerations
- Local transportation tips
- Important local customs
- Any seasonal events during their visit

Keep recommendations focused on local experiences and maintain a professional tone."""
    
    @staticmethod
    async def generate_trip_plan(
        user_prompt: str,
        model: str = "gpt-4",
        temperature: float = 0.10
    ) -> str:
        """
        This is our main method for generating new trip plans.
        
        How it works step by step:
        1. Takes in the user's trip request
        2. Combines it with our system instructions
        3. Sends it to GPT-4
        4. Returns the AI-generated itinerary
        """
        try:
            print(f"Generating trip plan with prompt: {user_prompt[:100]}...")
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": OpenAIService.SYSTEM_INSTRUCTIONS},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=2185
            )
            
            if not response.choices:
                raise Exception("No response generated from OpenAI")
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error generating trip plan: {str(e)}")
            raise

    @staticmethod
    async def generate_chat_response(
        messages: list,
        model: str = "gpt-4",
        temperature: float = 0.10
    ) -> str:
        """
        This method is for ongoing conversations about a trip plan.
        It lets users ask follow-up questions and get more details.
        """
        try:
            if not messages:
                raise ValueError("No messages provided")
                
            if not any(msg.get('role') == 'system' for msg in messages):
                messages.insert(0, {
                    "role": "system",
                    "content": OpenAIService.SYSTEM_INSTRUCTIONS
                })

            print(f"Generating chat response for {len(messages)} messages...")
            
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=2185
            )
            
            if not response.choices:
                raise Exception("No response generated from OpenAI")
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error generating chat response: {str(e)}")
            raise