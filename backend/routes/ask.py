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

@ask_blueprint.route('/ask', methods=['POST'])
def ask_question():
    print(">>> /api/ask hit")
    total_start_time = time.time()

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    query = data.get('query')
    history = data.get('history', [])

    if not query:
        return jsonify({'error': 'Field "query" is required'}), 400

    try:
        search_start_time = time.time()
        search_results = chroma_client.search(query, n_results=10)
        search_time = int((time.time() - search_start_time) * 1000)

        if not search_results or not search_results.get('results'):
            return jsonify({
                'query': query,
                'answer': 'No relevant information found.',
                'sources': [],
                'timing': {'search': search_time}
            })

        try:
            ai_start_time = time.time()
            answer = run_async(ai_engine.generate_answer(
                query=query,
                search_results=search_results,
                history=history
            ))
            ai_time = int((time.time() - ai_start_time) * 1000)
        except Exception as e:
            print("AIEngine error:", e)
            return jsonify({'error': str(e)}), 500

        sources = [
            {'title': r['title'], 'url': r['url'], 'score': r['relevance_score']}
            for r in search_results.get('results', [])[:5]
        ]

        print(">>> answer sent successfully")
        return jsonify({
            'query': query,
            'answer': answer,
            'sources': sources,
            'timing': {'search': search_time, 'ai': ai_time}
        })

    except Exception as e:
        print("Unhandled error:", e)
        return jsonify({'error': str(e)}), 500

    