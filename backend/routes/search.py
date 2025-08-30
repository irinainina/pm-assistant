from flask import Blueprint, request, jsonify
from services.chroma_client import ChromaClient
from services.ai_engine import AIEngine
import asyncio

search_blueprint = Blueprint('search', __name__)
chroma_client = ChromaClient()
ai_engine = AIEngine()

@search_blueprint.route('/search', methods=['GET'])
def get_answer():
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'})
    
    search_results = chroma_client.search(query, n_results=15)
    
    if not search_results or not search_results['documents']:
        return jsonify({
            'query': query,
            'answer': 'No relevant information found.',
            'sources': [],
            'message': 'No results found'
        })    
    
    answer = asyncio.run(ai_engine.generate_answer(query, search_results))
    
    sources = chroma_client.get_unique_sources(search_results, max_sources=5)
    
    return jsonify({
        'query': query,
        'answer': answer,
        'sources': sources
    })
