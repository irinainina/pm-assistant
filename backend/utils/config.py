import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    NOTION_API_KEY = os.getenv('NOTION_API_KEY')
    NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    @classmethod
    def validate(cls):
        missing = []
        if not cls.NOTION_API_KEY:
            missing.append('NOTION_API_KEY')
        if not cls.NOTION_DATABASE_ID:
            missing.append('NOTION_DATABASE_ID')
        if not cls.OPENAI_API_KEY:
            missing.append('OPENAI_API_KEY')
        
        if missing:
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")