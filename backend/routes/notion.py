from flask import Blueprint, jsonify
from services.notion_client import NotionClient
from services.chroma_client import ChromaClient
from utils.db_state import get_last_update_time, set_last_update_time
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
            our_last_update_ts = get_last_update_time()
            
            if our_last_update_ts:
                # Incremental update - only modified pages
                modified_pages = await client.get_modified_pages_since(our_last_update_ts)
                if modified_pages:
                    documents = []
                    tasks = [client._process_single_page_async(page) for page in modified_pages]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    documents = [result for result in results if result and not isinstance(result, Exception)]
                    
                    # Update only modified documents in ChromaDB
                    chroma_client.update_documents(documents)
                    added_count = len(documents)
                    update_type = "incremental"
                else:
                    # No changes - database is up to date
                    added_count = 0
                    update_type = "no_changes"
            else:
                # Full initial sync
                documents = await client.get_all_documents_metadata()
                chroma_client.clear_collection()
                chroma_client.add_documents(documents)
                added_count = len(documents)
                update_type = "full"

            set_last_update_time()
            
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
        client = NotionClient()
        try:
            # Fast check - get only the latest edit time
            latest_edit_time = await client.get_last_edited_time()
            our_last_update_ts = get_last_update_time()
            
            if not our_last_update_ts:
                return jsonify({
                    'is_actual': False,
                    'notion_last_edited': latest_edit_time,
                    'our_last_update': None,
                    'message': 'Database never synced'
                })

            if latest_edit_time:
                notion_last_edited_ts = parse_timestamp(latest_edit_time)
                is_actual = notion_last_edited_ts <= our_last_update_ts
            else:
                is_actual = True

            our_last_update_iso = timestamp_to_iso(our_last_update_ts)
            
            return jsonify({
                'is_actual': is_actual,
                'notion_last_edited': latest_edit_time,
                'our_last_update': our_last_update_iso,
                'check_type': 'fast'
            })
        finally:
            await client.close()
    
    return run_async(async_handler())

@notion_blueprint.route('/notion/status/detailed', methods=['GET'])
def get_detailed_status():
    async def async_handler():
        client = NotionClient()
        try:
            our_last_update_ts = get_last_update_time()
            
            if not our_last_update_ts:
                latest_edit_time = await client.get_last_edited_time()
                return jsonify({
                    'is_actual': False,
                    'notion_last_edited': latest_edit_time,
                    'our_last_update': None,
                    'changes_count': 0,
                    'check_type': 'detailed'
                })

            modified_pages = await client.get_modified_pages_since(our_last_update_ts)
            latest_edit_time = await client.get_last_edited_time()
            
            is_actual = len(modified_pages) == 0
            our_last_update_iso = timestamp_to_iso(our_last_update_ts)
            
            return jsonify({
                'is_actual': is_actual,
                'notion_last_edited': latest_edit_time,
                'our_last_update': our_last_update_iso,
                'changes_count': len(modified_pages),
                'check_type': 'detailed'
            })
        finally:
            await client.close()
    
    return run_async(async_handler())
