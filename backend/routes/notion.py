from flask import Blueprint, jsonify
from services.notion_client import NotionClient
from services.chroma_client import ChromaClient
import datetime
import asyncio
import time

notion_blueprint = Blueprint('notion', __name__)
chroma_client = ChromaClient()

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def parse_timestamp(timestamp_str):
    if not timestamp_str:
        return 0
    dt = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    return dt.timestamp()

def timestamp_to_iso(timestamp):
    return datetime.datetime.utcfromtimestamp(timestamp).isoformat() + 'Z'

@notion_blueprint.route('/notion/status', methods=['GET'])
def get_notion_status():
    async def async_handler():
        async with NotionClient() as client:
            notion_last_edited = await client.get_last_edited_time()
            chroma_last_update = chroma_client.get_last_update_time()

            notion_ts = parse_timestamp(notion_last_edited)
            chroma_ts = parse_timestamp(chroma_last_update)

            is_actual = False
            if notion_ts and chroma_ts:
                is_actual = chroma_ts >= notion_ts

            chroma_stats = chroma_client.get_collection_stats()

            return jsonify({
                "is_actual": is_actual,
                "notion_last_edited": notion_last_edited,
                "chroma_last_update": chroma_last_update,
                "chroma_stats": chroma_stats
            })

    return run_async(async_handler())

@notion_blueprint.route('/notion/update_vector_db', methods=['GET'])
def update_vector_db():
    async def async_handler():
        total_start_time = time.time()
        timing_info = {}
        
        client = NotionClient()
        try:
            start_get_docs = time.time()
            documents = await client.get_all_documents_metadata()
            timing_info['get_documents_time'] = round(time.time() - start_get_docs, 2)
        
            start_clear = time.time()
            clear_result = chroma_client.clear_collection()
            timing_info['clear_collection_time'] = round(time.time() - start_clear, 2)
            
            start_add_docs = time.time()
            chunks_added = chroma_client.add_documents(documents)
            timing_info['add_documents_time'] = round(time.time() - start_add_docs, 2)
          
            start_stats = time.time()
            chroma_stats = chroma_client.get_collection_stats()
            timing_info['get_stats_time'] = round(time.time() - start_stats, 2)
            
            added_count = len(documents)    
          
            start_update_time = time.time()
            chroma_client.set_last_update_time()
            timing_info['update_time_time'] = round(time.time() - start_update_time, 2)

            total_execution_time = round(time.time() - total_start_time, 2)
            
            return jsonify({
                'status': 'success',
                'message': f'Vector database updated with {added_count} documents',
                'documents_processed': added_count,
                'update_type': 'full',
                'execution_time': total_execution_time,
                'timing_breakdown': timing_info,
                'chroma_stats': {
                    'chunks_added': chunks_added,
                    'total_chunks': chroma_stats.get('total_chunks', 0),
                    'clear_success': clear_result
                }
            })
        except Exception as e:
            total_execution_time = round(time.time() - total_start_time, 2)
            return jsonify({
                'status': 'error',
                'message': f'Error updating vector database: {str(e)}',
                'execution_time': total_execution_time,
                'timing_breakdown': timing_info if timing_info else {}
            }), 500
        finally:
            await client.close()
    
    return run_async(async_handler())




# from flask import Blueprint, jsonify
# from services.notion_client import NotionClient
# from services.chroma_client import ChromaClient
# import datetime
# import asyncio

# notion_blueprint = Blueprint('notion', __name__)
# chroma_client = ChromaClient()

# def run_async(coro):
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     try:
#         return loop.run_until_complete(coro)
#     finally:
#         loop.close()

# def parse_timestamp(timestamp_str):
#     if not timestamp_str:
#         return 0
#     dt = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
#     return dt.timestamp()

# def timestamp_to_iso(timestamp):
#     return datetime.datetime.utcfromtimestamp(timestamp).isoformat() + 'Z'

# @notion_blueprint.route('/notion/status', methods=['GET'])
# def get_notion_status():
#     async def async_handler():
#         async with NotionClient() as client:
#             notion_last_edited = await client.get_last_edited_time()
#             chroma_last_update = chroma_client.get_last_update_time()

#             notion_ts = parse_timestamp(notion_last_edited)
#             chroma_ts = parse_timestamp(chroma_last_update)

#             is_actual = False
#             if notion_ts and chroma_ts:
#                 is_actual = chroma_ts >= notion_ts

#             chroma_stats = chroma_client.get_collection_stats()

#             return jsonify({
#                 "is_actual": is_actual,
#                 "notion_last_edited": notion_last_edited,
#                 "chroma_last_update": chroma_last_update,
#                 "chroma_stats": chroma_stats
#             })

#     return run_async(async_handler())

# @notion_blueprint.route('/notion/update_vector_db', methods=['GET'])
# def update_vector_db():
#     async def async_handler():
#         client = NotionClient()
#         try:
#             documents = await client.get_all_documents_metadata()

#             clear_result = chroma_client.clear_collection()
#             chunks_added = chroma_client.add_documents(documents)

#             chroma_stats = chroma_client.get_collection_stats()
            
#             added_count = len(documents)
    
#             chroma_client.set_last_update_time()
            
#             return jsonify({
#                 'status': 'success',
#                 'message': f'Vector database updated with {added_count} documents',
#                 'documents_processed': added_count,
#                 'update_type': 'full',
#                 'chroma_stats': {
#                     'chunks_added': chunks_added,
#                     'total_chunks': chroma_stats.get('total_chunks', 0),
#                     'clear_success': clear_result
#                 }
#             })
#         except Exception as e:
#             return jsonify({
#                 'status': 'error',
#                 'message': f'Error updating vector database: {str(e)}'
#             }), 500
#         finally:
#             await client.close()
    
#     return run_async(async_handler())
