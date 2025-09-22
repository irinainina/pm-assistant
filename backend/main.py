from flask import Flask
from flask_cors import CORS
from services.notion_client import NotionClient
from services.chroma_client import ChromaClient
from services.ai_engine import AIEngine
from routes.ask import ask_blueprint
from routes.notion import notion_blueprint
from routes.health import health_blueprint
import asyncio
import os

app = Flask(__name__)
CORS(app)

notion_client = NotionClient()
chroma_client = ChromaClient()
ai_engine = AIEngine()

db_initialized = False

app.register_blueprint(ask_blueprint, url_prefix='/api')
app.register_blueprint(notion_blueprint, url_prefix='/api')
app.register_blueprint(health_blueprint, url_prefix='/api')

if os.environ.get('FLASK_ENV') == 'development':
    from routes.search import search_blueprint
    from routes.chroma import chroma_blueprint    
    from routes.notion_parsed import notion_parsed_blueprint
    
    app.register_blueprint(search_blueprint, url_prefix='/api')
    app.register_blueprint(chroma_blueprint, url_prefix='/api')
    app.register_blueprint(notion_parsed_blueprint, url_prefix='/api')

def run_async(async_func):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(async_func)
    finally:
        loop.close()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)


# from flask import Flask
# from flask_cors import CORS
# from services.ai_engine import AIEngine
# from routes.ask import ask_blueprint
# from routes.health import health_blueprint
# import asyncio
# import os

# app = Flask(__name__)
# CORS(app)

# ai_engine = AIEngine()

# app.register_blueprint(ask_blueprint, url_prefix='/api')
# app.register_blueprint(health_blueprint, url_prefix='/api')

# def run_async(async_func):
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     try:
#         return loop.run_until_complete(async_func)
#     finally:
#         loop.close()

# if __name__ == '__main__':
#     port = int(os.environ.get('PORT', 8000))
#     app.run(host='0.0.0.0', port=port)
