from flask import Blueprint, request, jsonify
from services.chroma_client import ChromaClient
from services.ai_engine import AIEngine
import asyncio
import time
import psycopg2
import os
from datetime import datetime
import uuid
import json

chroma_client = ChromaClient()
ai_engine = AIEngine()
search_blueprint = Blueprint('search', __name__)

def get_db_connection():
    return psycopg2.connect(os.environ.get('DATABASE_URL'))

def run_async(async_func):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(async_func)
    finally:
        loop.close()

@search_blueprint.route('/search', methods=['GET'])
def search_question():
    total_start_time = time.time()
    
    try:
        query = request.args.get('query') or request.args.get('q')
        history = request.args.get('history', '')
        user_id = "cmgtqz8b40000viwgjsqavitm"
        conversation_id = request.args.get('conversation_id')
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400

        normalization_start_time = time.time()
        normalized_query = run_async(ai_engine.normalize_query(query))
        normalization_time = int((time.time() - normalization_start_time) * 1000)

        search_start_time = time.time()
        search_results = chroma_client.search(normalized_query, n_results=10)
        search_time = int((time.time() - search_start_time) * 1000)
        
        if not search_results or not search_results.get('results'):
            total_time = int((time.time() - total_start_time) * 1000)
            return jsonify({
                'original_query': query,
                'normalized_query': normalized_query,
                'answer': 'I could not find any relevant information to answer your question.',
                'sources': [],
                'timing': {
                    'normalization': normalization_time,
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
            history=history.split('|') if history else []
        ))
        ai_generation_time = int((time.time() - ai_generation_start) * 1000)
        
        ai_total_time = int((time.time() - ai_processing_start) * 1000)

        sources = [
            {'title': r['title'], 'url': r['url'], 'score': r['relevance_score']}
            for r in search_results.get('results', [])[:5]
        ]

        total_time = int((time.time() - total_start_time) * 1000)

        db_save_result = save_conversation_to_db(user_id, conversation_id, query, answer, sources)

        debug_info = {
            'ai_engine_input': {
                'original_query': query,
                'normalized_query': normalized_query,
                'search_results_count': len(search_results.get('results', [])),
                'history_length': len(history.split('|')) if history else 0,
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
                'user_prompt_length': len(user_prompt)
            },
            'ai_engine_output': {
                'answer_length': len(answer),
                'sources_count': len(sources)
            },
            'database_save': db_save_result
        }
        
        return jsonify({
            'original_query': query,
            'normalized_query': normalized_query,
            'answer': answer,
            'sources': sources,
            'timing': {
                'normalization': normalization_time,
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

def save_conversation_to_db(user_id, conversation_id, user_query, ai_response, sources):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            title = user_query[:50] + "..." if len(user_query) > 50 else user_query
            
            cursor.execute("""
                INSERT INTO conversations (id, user_id, title, last_activity_at, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (conversation_id, user_id, title, datetime.now(), datetime.now(), datetime.now()))
            
            conn.commit()
        
        user_message_id = str(uuid.uuid4())
        ai_message_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO messages (id, conversation_id, role, content, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_message_id, conversation_id, 'user', user_query, datetime.now()))
        
        cursor.execute("""
            INSERT INTO messages (id, conversation_id, role, content, sources, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (ai_message_id, conversation_id, 'assistant', ai_response, json.dumps(sources), datetime.now()))
        
        cursor.execute("""
            UPDATE conversations 
            SET last_activity_at = %s, updated_at = %s
            WHERE id = %s
        """, (datetime.now(), datetime.now(), conversation_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            'conversation_id': conversation_id,
            'user_message_saved': True,
            'ai_message_saved': True
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'conversation_id': conversation_id,
            'user_message_saved': False,
            'ai_message_saved': False
        }


# from flask import Blueprint, request, jsonify
# from services.chroma_client import ChromaClient
# from services.ai_engine import AIEngine
# import asyncio
# import time
# import psycopg2
# import os
# from datetime import datetime
# import uuid

# chroma_client = ChromaClient()
# ai_engine = AIEngine()
# search_blueprint = Blueprint('search', __name__)

# def get_db_connection():
#     return psycopg2.connect(os.environ.get('DATABASE_URL'))

# def run_async(async_func):
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     try:
#         return loop.run_until_complete(async_func)
#     finally:
#         loop.close()

# @search_blueprint.route('/search', methods=['GET'])
# def search_question():
#     total_start_time = time.time()
    
#     try:
#         query = request.args.get('query') or request.args.get('q')
#         history = request.args.get('history', '')
#         user_id = "cmgtqz8b40000viwgjsqavitm"
#         conversation_id = request.args.get('conversation_id')
        
#         if not query:
#             return jsonify({'error': 'Query is required'}), 400

#         normalization_start_time = time.time()
#         normalized_query = run_async(ai_engine.normalize_query(query))
#         normalization_time = int((time.time() - normalization_start_time) * 1000)

#         search_start_time = time.time()
#         search_results = chroma_client.search(normalized_query, n_results=10)
#         search_time = int((time.time() - search_start_time) * 1000)
        
#         if not search_results or not search_results.get('results'):
#             total_time = int((time.time() - total_start_time) * 1000)
#             return jsonify({
#                 'original_query': query,
#                 'normalized_query': normalized_query,
#                 'answer': 'I could not find any relevant information to answer your question.',
#                 'sources': [],
#                 'timing': {
#                     'normalization': normalization_time,
#                     'search': search_time,
#                     'total': total_time
#                 }
#             })

#         ai_processing_start = time.time()
        
#         detected_language = run_async(ai_engine._detect_language_async(query))
#         extracted_context = run_async(ai_engine._extract_context_async(search_results))
#         system_prompt = ai_engine._create_system_prompt(detected_language)
#         user_prompt = ai_engine._create_user_prompt(query, extracted_context, detected_language)
        
#         prompt_construction_time = int((time.time() - ai_processing_start) * 1000)
        
#         ai_generation_start = time.time()
#         answer = run_async(ai_engine.generate_answer(
#             query=query, 
#             search_results=search_results,
#             history=history.split('|') if history else []
#         ))
#         ai_generation_time = int((time.time() - ai_generation_start) * 1000)
        
#         ai_total_time = int((time.time() - ai_processing_start) * 1000)

#         sources = [
#             {'title': r['title'], 'url': r['url'], 'score': r['relevance_score']}
#             for r in search_results.get('results', [])[:5]
#         ]

#         total_time = int((time.time() - total_start_time) * 1000)

#         db_save_result = save_conversation_to_db(user_id, conversation_id, query, answer)

#         debug_info = {
#             'ai_engine_input': {
#                 'original_query': query,
#                 'normalized_query': normalized_query,
#                 'search_results_count': len(search_results.get('results', [])),
#                 'history_length': len(history.split('|')) if history else 0,
#                 'search_results_details': [
#                     {
#                         'title': result.get('title'),
#                         'relevance_score': result.get('relevance_score'),
#                         'content_snippet_length': len(result.get('content_snippet', '')),
#                         'content_snippet': result.get('content_snippet', ''),
#                         'language': result.get('language'),
#                         'match_type': result.get('match_type')
#                     }
#                     for result in search_results.get('results', [])[:5]
#                 ]
#             },
#             'ai_engine_processing': {
#                 'detected_language': detected_language,
#                 'extracted_context_length': len(extracted_context),
#                 'system_prompt_length': len(system_prompt),
#                 'user_prompt_length': len(user_prompt)
#             },
#             'ai_engine_output': {
#                 'answer_length': len(answer),
#                 'sources_count': len(sources)
#             },
#             'database_save': db_save_result
#         }
        
#         return jsonify({
#             'original_query': query,
#             'normalized_query': normalized_query,
#             'answer': answer,
#             'sources': sources,
#             'timing': {
#                 'normalization': normalization_time,
#                 'search': search_time,
#                 'ai_prompt_construction': prompt_construction_time,
#                 'ai_generation': ai_generation_time,
#                 'ai_total': ai_total_time,
#                 'total': total_time
#             },
#             'debug': debug_info
#         })
        
#     except Exception as e:
#         total_time = int((time.time() - total_start_time) * 1000)
#         return jsonify({
#             'error': str(e)
#         }), 500

# def save_conversation_to_db(user_id, conversation_id, user_query, ai_response):
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
        
#         if not conversation_id:
#             conversation_id = str(uuid.uuid4())
#             title = user_query[:50] + "..." if len(user_query) > 50 else user_query
            
#             cursor.execute("""
#                 INSERT INTO conversations (id, user_id, title, last_activity_at, created_at, updated_at)
#                 VALUES (%s, %s, %s, %s, %s, %s)
#             """, (conversation_id, user_id, title, datetime.now(), datetime.now(), datetime.now()))
            
#             conn.commit()
        
#         user_message_id = str(uuid.uuid4())
#         ai_message_id = str(uuid.uuid4())
        
#         cursor.execute("""
#             INSERT INTO messages (id, conversation_id, role, content, created_at)
#             VALUES (%s, %s, %s, %s, %s)
#         """, (user_message_id, conversation_id, 'user', user_query, datetime.now()))
        
#         cursor.execute("""
#             INSERT INTO messages (id, conversation_id, role, content, created_at)
#             VALUES (%s, %s, %s, %s, %s)
#         """, (ai_message_id, conversation_id, 'assistant', ai_response, datetime.now()))
        
#         cursor.execute("""
#             UPDATE conversations 
#             SET last_activity_at = %s, updated_at = %s
#             WHERE id = %s
#         """, (datetime.now(), datetime.now(), conversation_id))
        
#         conn.commit()
#         cursor.close()
#         conn.close()
        
#         return {
#             'conversation_id': conversation_id,
#             'user_message_saved': True,
#             'ai_message_saved': True
#         }
        
#     except Exception as e:
#         return {
#             'error': str(e),
#             'conversation_id': conversation_id,
#             'user_message_saved': False,
#             'ai_message_saved': False
#         }
    