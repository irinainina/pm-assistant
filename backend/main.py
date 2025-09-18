from flask import Flask
from flask_cors import CORS
from services.ai_engine import AIEngine
from routes.ask import ask_blueprint
from routes.health import health_blueprint
import asyncio
import os

app = Flask(__name__)
CORS(app)

ai_engine = AIEngine()

app.register_blueprint(ask_blueprint, url_prefix='/api')
app.register_blueprint(health_blueprint, url_prefix='/api')

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
