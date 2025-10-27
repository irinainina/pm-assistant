from flask import Flask
from flask_cors import CORS
from services.chroma_client import ChromaClient
from services.ai_engine import AIEngine
from routes.ask import ask_blueprint
from routes.notion import notion_blueprint
from routes.health import health_blueprint
from routes.conversations import conversations_bp
import os

app = Flask(__name__)
CORS(app)

chroma_client = ChromaClient()
ai_engine = AIEngine()

db_initialized = False

app.register_blueprint(ask_blueprint, url_prefix='/api')
app.register_blueprint(notion_blueprint, url_prefix='/api')
app.register_blueprint(health_blueprint, url_prefix='/api')
app.register_blueprint(conversations_bp, url_prefix='/api')

if os.environ.get('FLASK_ENV') == 'development':
    from routes.search import search_blueprint
    from routes.chroma import chroma_blueprint    
    from routes.notion_parsed import notion_parsed_blueprint
    from routes.embeddings_info import embeddings_blueprint
    
    app.register_blueprint(search_blueprint, url_prefix='/api')
    app.register_blueprint(chroma_blueprint, url_prefix='/api')
    app.register_blueprint(notion_parsed_blueprint, url_prefix='/api')
    app.register_blueprint(embeddings_blueprint, url_prefix='/api')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, threaded=False)
