import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    NOTION_API_KEY = os.getenv('NOTION_API_KEY')
    NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')    
    