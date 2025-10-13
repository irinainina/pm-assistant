from flask import Blueprint, request, jsonify, Response, stream_with_context
from services.chroma_client import ChromaClient
from services.ai_engine import AIEngine
import asyncio
import concurrent.futures
import time
import json

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
    total_start_time = time.time()
    
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid or missing JSON body"}), 400

        query = data.get('query')
        history = data.get('history', [])

        if not query:
            return jsonify({'error': 'Field "query" is required'}), 400

        search_start_time = time.time()
        search_results = chroma_client.search(query, n_results=10)
        search_time = int((time.time() - search_start_time) * 1000)
        
        if not search_results or not search_results.get('results'):
            total_time = int((time.time() - total_start_time) * 1000)
            return jsonify({
                'query': query,
                'answer': 'I could not find any relevant information to answer your question.',
                'sources': [],
                'timing': {
                    'search': search_time,
                    'total': total_time
                }
            })

        ai_processing_start = time.time()
        
        detected_language = run_async(ai_engine._detect_language_async(query))
        extracted_context = run_async(ai_engine._extract_context_async(search_results))
        system_prompt = ai_engine._create_system_prompt(detected_language)
        user_prompt = ai_engine._create_user_prompt(query, extracted_context, detected_language)
        
        prompt_construction_time = int((time.time() - ai_processing_start) * 1000)
        
        ai_generation_start = time.time()
        answer = run_async(ai_engine.generate_answer(
            query=query, 
            search_results=search_results,
            history=history
        ))
        ai_generation_time = int((time.time() - ai_generation_start) * 1000)
        
        ai_total_time = int((time.time() - ai_processing_start) * 1000)

        sources = [
            {'title': r['title'], 'url': r['url'], 'score': r['relevance_score']}
            for r in search_results.get('results', [])[:5]
        ]

        total_time = int((time.time() - total_start_time) * 1000)

        debug_info = {
            'ai_engine_input': {
                'query': query,
                'search_results_count': len(search_results.get('results', [])),
                'history_length': len(history),
                'search_results_details': [
                    {
                        'title': result.get('title'),
                        'relevance_score': result.get('relevance_score'),
                        'content_snippet_length': len(result.get('content_snippet', '')),
                        'content_snippet': result.get('content_snippet', ''),
                        'language': result.get('language'),
                        'match_type': result.get('match_type')
                    }
                    for result in search_results.get('results', [])[:5]
                ]
            },
            'ai_engine_processing': {
                'detected_language': detected_language,
                'extracted_context_length': len(extracted_context),
                'system_prompt_length': len(system_prompt),
                'user_prompt_length': len(user_prompt),
                'system_prompt': system_prompt,
                'user_prompt': user_prompt
            },
            'ai_engine_output': {
                'answer_length': len(answer),
                'sources_count': len(sources)
            }
        }
        
        return jsonify({
            'query': query,
            'answer': answer,
            'sources': sources,
            'timing': {
                'search': search_time,
                'ai_prompt_construction': prompt_construction_time,
                'ai_generation': ai_generation_time,
                'ai_total': ai_total_time,
                'total': total_time
            },
            'debug': debug_info
        })
        
    except Exception as e:
        total_time = int((time.time() - total_start_time) * 1000)
        return jsonify({
            'error': str(e)
        }), 500
    

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

        search_results = chroma_client.search(query, n_results=10)
        
        if not search_results or not search_results.get('results'):
            return jsonify({
                'query': query,
                'answer': 'I could not find any relevant information to answer your question.',
                'sources': []
            })

        def generate():
            try:
                sources = [
                    {'title': r['title'], 'url': r['url'], 'score': r['relevance_score']}
                    for r in search_results.get('results', [])[:5]
                ]

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    stream_gen = ai_engine.generate_answer_stream(
                        query=query, 
                        search_results=search_results,
                        history=history
                    )
               
                    full_answer = ""                    
               
                    async def stream_processor():
                        async for chunk in stream_gen:
                            yield chunk
                   
                    processor = stream_processor()
                    
                    while True:
                        try:
                            chunk = loop.run_until_complete(processor.__anext__())
                            full_answer += chunk
                            yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"
                        except StopAsyncIteration:
                            break
                 
                    yield f"data: {json.dumps({'chunk': '', 'done': True, 'sources': sources})}\n\n"
                        
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
                finally:
                    loop.close()
                    
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

        return Response(stream_with_context(generate()), mimetype='text/plain')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    