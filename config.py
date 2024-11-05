import os 
from dotenv import load_dotenv
from pathlib import Path

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# # Validate required environment variables
# if not all([DATABASE_URL, SUPABASE_SECRET_KEY, OPENAI_API_KEY]):
#     raise ValueError("Missing required environment variables")