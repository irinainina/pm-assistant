from flask import Blueprint, request, jsonify, Response, stream_with_context
from services.chroma_client import ChromaClient
from services.ai_engine import AIEngine
import asyncio
import json

chroma_client = ChromaClient()
ai_engine = AIEngine()
ask_blueprint = Blueprint('ask', __name__)

def run_async(async_func):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(async_func)
    finally:
        loop.close()

@ask_blueprint.route('/ask-stream', methods=['POST'])
def ask_question_stream():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid or missing JSON body"}), 400

        query = data.get('query')
        history = data.get('history', [])

        if not query:
            return jsonify({'error': 'Field "query" is required'}), 400

        normalized_query = run_async(ai_engine.normalize_query(query))
        search_results = chroma_client.search(normalized_query, n_results=10)
        
        if not search_results or not search_results.get('results'):
            return jsonify({
                'query': query,
                'answer': 'I could not find any relevant information to answer your question.',
                'sources': []
            })

        sources = [
            {'title': r['title'], 'url': r['url'], 'score': r['relevance_score']}
            for r in search_results.get('results', [])[:5]
        ]

        def generate():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def process_stream():
                    async for chunk in ai_engine.generate_answer_stream(
                        query=query,
                        search_results=search_results,
                        history=history
                    ):
                        yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"
                    
                    yield f"data: {json.dumps({'chunk': '', 'done': True, 'sources': sources})}\n\n"
                
                stream_processor = process_stream()
                
                while True:
                    try:
                        chunk = loop.run_until_complete(stream_processor.__anext__())
                        yield chunk
                    except StopAsyncIteration:
                        break
                        
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# from flask import Blueprint, request, jsonify, Response, stream_with_context
# from services.chroma_client import ChromaClient
# from services.ai_engine import AIEngine
# import asyncio
# import concurrent.futures
# import json

# chroma_client = ChromaClient()
# ai_engine = AIEngine()
# ask_blueprint = Blueprint('ask', __name__)

# _thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)

# def run_async(async_func):
#     try:
#         try:
#             loop = asyncio.get_event_loop()
#         except RuntimeError:
#             loop = asyncio.new_event_loop()
#             asyncio.set_event_loop(loop)
        
#         if loop.is_running():
#             future = _thread_pool.submit(lambda: loop.run_until_complete(async_func))
#             return future.result()
#         else:
#             return loop.run_until_complete(async_func)
#     except Exception as e:
#         raise Exception(f"Async execution failed: {str(e)}")

# @ask_blueprint.route('/ask-stream', methods=['POST'])
# def ask_question_stream():
#     try:
#         data = request.get_json(silent=True)
#         if not data:
#             return jsonify({"error": "Invalid or missing JSON body"}), 400

#         query = data.get('query')
#         history = data.get('history', [])

#         if not query:
#             return jsonify({'error': 'Field "query" is required'}), 400

#         def generate():
#             try:
#                 loop = asyncio.new_event_loop()
#                 asyncio.set_event_loop(loop)
                
#                 try:
#                     normalized_query = loop.run_until_complete(ai_engine.normalize_query(query))
              
#                     search_results = chroma_client.search(normalized_query, n_results=10)
                    
#                     if not search_results or not search_results.get('results'):
#                         yield f"data: {json.dumps({'error': 'No relevant information found', 'done': True})}\n\n"
#                         return

#                     sources = [
#                         {'title': r['title'], 'url': r['url'], 'score': r['relevance_score']}
#                         for r in search_results.get('results', [])[:5]
#                     ]

#                     stream_gen = ai_engine.generate_answer_stream(
#                         query=query,
#                         search_results=search_results,
#                         history=history
#                     )

#                     full_answer = ""
               
#                     async def process_stream():
#                         async for chunk in stream_gen:
#                             yield chunk
                    
#                     stream_processor = process_stream()
                    
#                     while True:
#                         try:
#                             chunk = loop.run_until_complete(stream_processor.__anext__())
#                             full_answer += chunk
#                             yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"
#                         except StopAsyncIteration:
#                             break
                  
#                     yield f"data: {json.dumps({'chunk': '', 'done': True, 'sources': sources})}\n\n"
                        
#                 except Exception as e:
#                     yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
#                 finally:
#                     loop.close()
                    
#             except Exception as e:
#                 yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

#         return Response(stream_with_context(generate()), mimetype='text/plain')
        
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500
