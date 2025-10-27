import psycopg2
import os

class DatabaseService:
    def __init__(self):
        self.connection_string = os.environ.get('DATABASE_URL')
    
    def get_connection(self):
        return psycopg2.connect(self.connection_string)

db_service = DatabaseService()
