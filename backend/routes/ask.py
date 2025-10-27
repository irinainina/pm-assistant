from flask import Blueprint, request, jsonify, Response, stream_with_context
from services.chroma_client import ChromaClient
from services.ai_engine import AIEngine
import asyncio
import json
import psycopg2
import os
from datetime import datetime
import uuid

chroma_client = ChromaClient()
ai_engine = AIEngine()
ask_blueprint = Blueprint('ask', __name__)

def get_db_connection():
    return psycopg2.connect(os.environ.get('DATABASE_URL'))

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
        conversation_id = data.get('conversation_id')
        user_id = request.headers.get('User-Id')

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
                
                accumulated_answer = ""
                
                async def process_stream():
                    nonlocal accumulated_answer
                    async for chunk in ai_engine.generate_answer_stream(
                        query=query,
                        search_results=search_results,
                        history=history
                    ):
                        accumulated_answer += chunk
                        yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"
                    
                    if user_id:
                        save_conversation_to_db(user_id, conversation_id, query, accumulated_answer, sources)
                    
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
        
        return conversation_id
        
    except Exception as e:
        print(f"Error saving conversation to DB: {e}")
        return None



# from flask import Blueprint, request, jsonify, Response, stream_with_context
# from services.chroma_client import ChromaClient
# from services.ai_engine import AIEngine
# import asyncio
# import json
# import psycopg2
# import os
# from datetime import datetime
# import uuid

# chroma_client = ChromaClient()
# ai_engine = AIEngine()
# ask_blueprint = Blueprint('ask', __name__)

# def get_db_connection():
#     return psycopg2.connect(os.environ.get('DATABASE_URL'))

# def run_async(async_func):
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     try:
#         return loop.run_until_complete(async_func)
#     finally:
#         loop.close()

# @ask_blueprint.route('/ask-stream', methods=['POST'])
# def ask_question_stream():
#     try:
#         data = request.get_json(silent=True)
#         if not data:
#             return jsonify({"error": "Invalid or missing JSON body"}), 400

#         query = data.get('query')
#         history = data.get('history', [])
#         conversation_id = data.get('conversation_id')
#         user_id = request.headers.get('User-Id')

#         if not query:
#             return jsonify({'error': 'Field "query" is required'}), 400

#         normalized_query = run_async(ai_engine.normalize_query(query))
#         search_results = chroma_client.search(normalized_query, n_results=10)
        
#         if not search_results or not search_results.get('results'):
#             return jsonify({
#                 'query': query,
#                 'answer': 'I could not find any relevant information to answer your question.',
#                 'sources': []
#             })

#         sources = [
#             {'title': r['title'], 'url': r['url'], 'score': r['relevance_score']}
#             for r in search_results.get('results', [])[:5]
#         ]

#         def generate():
#             try:
#                 loop = asyncio.new_event_loop()
#                 asyncio.set_event_loop(loop)
                
#                 accumulated_answer = ""
                
#                 async def process_stream():
#                     nonlocal accumulated_answer
#                     async for chunk in ai_engine.generate_answer_stream(
#                         query=query,
#                         search_results=search_results,
#                         history=history
#                     ):
#                         accumulated_answer += chunk
#                         yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"
                    
#                     if user_id:
#                         save_conversation_to_db(user_id, conversation_id, query, accumulated_answer)
                    
#                     yield f"data: {json.dumps({'chunk': '', 'done': True, 'sources': sources})}\n\n"
                
#                 stream_processor = process_stream()
                
#                 while True:
#                     try:
#                         chunk = loop.run_until_complete(stream_processor.__anext__())
#                         yield chunk
#                     except StopAsyncIteration:
#                         break
                        
#             except Exception as e:
#                 yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

#         return Response(
#             stream_with_context(generate()),
#             mimetype='text/event-stream',
#             headers={
#                 "Cache-Control": "no-cache",
#                 "X-Accel-Buffering": "no"
#             }
#         )
        
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

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
        
#         return conversation_id
        
#     except Exception as e:
#         print(f"Error saving conversation to DB: {e}")
#         return None
    