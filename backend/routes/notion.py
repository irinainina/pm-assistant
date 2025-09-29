from flask import Blueprint, jsonify
from services.notion_client import NotionClient
from services.chroma_client import ChromaClient
import datetime
import asyncio

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

@notion_blueprint.route('/notion/update_vector_db', methods=['GET'])
def update_vector_db():
    async def async_handler():
        client = NotionClient()
        try:
            documents = await client.get_all_documents_metadata()
 
            chroma_client.clear_collection()
            chroma_client.add_documents(documents)
            
            added_count = len(documents)
            update_type = "full"
    
            chroma_client.set_last_update_time()
            
            return jsonify({
                'status': 'success',
                'message': f'Vector database updated with {added_count} documents',
                'documents_processed': added_count,
                'update_type': update_type
            })
        finally:
            await client.close()
    
    return run_async(async_handler())

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

            return jsonify({
                "is_actual": is_actual,
                "notion_last_edited": notion_last_edited,
                "chroma_last_update": chroma_last_update
            })

    return run_async(async_handler())
