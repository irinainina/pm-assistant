from flask import Blueprint, request, jsonify
from services.chroma_client import ChromaClient
from services.ai_engine import AIEngine
import asyncio

chroma_client = ChromaClient()
ask_blueprint = Blueprint('ask', __name__)
ai_engine = AIEngine()

def run_async(async_func):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(async_func)
    finally:
        loop.close()

@ask_blueprint.route('/ask', methods=['POST'])
def ask_question():
    try:
        data = request.get_json()
        query = data.get('query')
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        search_results = chroma_client.search(query, n_results=10)
        
        if not search_results or not search_results['documents']:
            return jsonify({
                'query': query,
                'answer': 'I could not find any relevant information to answer your question.',
                'sources': []
            })
      
        answer = run_async(ai_engine.generate_answer(query, search_results))
        
        sources = chroma_client.get_unique_sources(search_results, max_sources=5)
        
        return jsonify({
            'query': query,
            'answer': answer,
            'sources': sources
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    