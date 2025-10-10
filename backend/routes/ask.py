from flask import Blueprint, request, jsonify
from services.chroma_client import ChromaClient
from services.ai_engine import AIEngine
import asyncio
import concurrent.futures
import time

chroma_client = ChromaClient()
ai_engine = AIEngine()
ask_blueprint = Blueprint('ask', __name__)

_thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)

def run_async(async_func):
    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            future = _thread_pool.submit(lambda: loop.run_until_complete(async_func))
            return future.result()
        else:
            return loop.run_until_complete(async_func)
    except Exception as e:
        raise Exception(f"Async execution failed: {str(e)}")

@ask_blueprint.route('/ask', methods=['GET'])
def ask_question():
    total_start_time = time.time()
    
    try:
        query = request.args.get('q')
        history = request.args.get('history', '')
        
        if not query:
            return jsonify({'error': 'Query parameter "q" is required'}), 400

        search_start_time = time.time()
        search_results = chroma_client.search(query, n_results=10)
        search_time = int((time.time() - search_start_time) * 1000)

        if not search_results or not search_results['results']:
            total_time = int((time.time() - total_start_time) * 1000)
            return jsonify({
                'query': query,
                'answer': 'I could not find any relevant information to answer your question.',
                'sources': [],
                'timing': {
                    'search': search_time,
                    'ai_processing': 0,
                    'total': total_time
                }
            })

        ai_start_time = time.time()
        answer = run_async(ai_engine.generate_answer(
            query=query, 
            search_results=search_results,
            history=history.split('|') if history else []
        ))
        ai_time = int((time.time() - ai_start_time) * 1000)

        sources = []
        if search_results and search_results.get('results'):
            for result in search_results['results'][:5]:
                sources.append({
                    'title': result['title'],
                    'url': result['url'],
                    'score': result['relevance_score']
                })

        total_time = int((time.time() - total_start_time) * 1000)
        
        return jsonify({
            'query': query,
            'answer': answer,
            'sources': sources,
            'timing': {
                'search': search_time,
                'ai_processing': ai_time,
                'total': total_time
            }
        })
        
    except Exception as e:
        total_time = int((time.time() - total_start_time) * 1000)
        return jsonify({
            'error': str(e),
            'timing': {
                'total': total_time
            }
        }), 500
    