from flask import Blueprint, jsonify
from services.notion_client import NotionClient
from services.chroma_client import ChromaClient
import datetime
import asyncio
import time
from typing import Dict

notion_blueprint = Blueprint('notion', __name__)
chroma_client = ChromaClient()

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def _is_document_modified(notion_doc: Dict, existing_doc: Dict) -> bool:
    try:
        notion_title = notion_doc['properties'].get('title', '')
        existing_title = existing_doc.get('title', '')
        if notion_title != existing_title:
            return True
        
        notion_content = notion_doc.get('content', '')
        existing_content = existing_doc.get('content', '')
        if notion_content != existing_content:
            return True
            
        return False
    except Exception:
        return True

@notion_blueprint.route('/notion/status', methods=['GET'])
def get_notion_status():
    async def async_handler():
        try:
            async with NotionClient() as notion_client:
                notion_last_edited = await notion_client.get_last_edited_time()
                chroma_last_update = chroma_client.get_last_update_time()
                
                if not notion_last_edited:
                    return jsonify({
                        "status": "error",
                        "message": "Could not fetch Notion last edited time"
                    }), 500

                notion_ts = datetime.datetime.fromisoformat(
                    notion_last_edited.replace('Z', '+00:00')
                ).timestamp()
                
                if not chroma_last_update:
                    is_actual = False
                    chroma_ts = 0
                else:
                    chroma_ts = datetime.datetime.fromisoformat(
                        chroma_last_update.replace('Z', '+00:00')
                    ).timestamp()
                    is_actual = chroma_ts >= notion_ts
                
                chroma_stats = chroma_client.get_collection_stats()
                
                return jsonify({
                    "is_actual": is_actual,
                    "notion_last_edited": notion_last_edited,
                    "chroma_last_update": chroma_last_update,
                    "time_difference_seconds": chroma_ts - notion_ts,
                    "chroma_stats": chroma_stats
                })
                
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Error checking database status: {str(e)}"
            }), 500

    return run_async(async_handler())

@notion_blueprint.route('/notion/update_vector_db', methods=['GET'])
def update_vector_db():
    async def async_handler():
        total_start_time = time.time()
        stage_times = {}
        
        try:
            async with NotionClient() as notion_client:
                stage_start = time.time()
                current_docs = chroma_client.get_all_documents_metadata()
                current_page_ids = {doc['page_id'] for doc in current_docs}
                stage_times['get_current_docs'] = int(time.time() - stage_start)
                
                stage_start = time.time()
                notion_documents = await notion_client.get_all_documents_metadata()
                notion_page_ids = {doc['id'] for doc in notion_documents}
                stage_times['get_notion_docs'] = int(time.time() - stage_start)
                
                deleted_page_ids = current_page_ids - notion_page_ids
                
                stage_start = time.time()
                existing_docs_map = {doc['page_id']: doc for doc in current_docs}
                documents_to_update = []
                
                for notion_doc in notion_documents:
                    page_id = notion_doc['id']
                    
                    if page_id not in current_page_ids:
                        documents_to_update.append(notion_doc)
                        continue
                    
                    existing_doc = existing_docs_map.get(page_id)
                    if existing_doc and _is_document_modified(notion_doc, existing_doc):
                        documents_to_update.append(notion_doc)
                stage_times['analyze_changes'] = int(time.time() - stage_start)
                
                stage_start = time.time()
                deleted_count = 0
                for page_id in deleted_page_ids:
                    if chroma_client.delete_document(page_id):
                        deleted_count += 1
                stage_times['delete_documents'] = int(time.time() - stage_start)
                
                stage_start = time.time()
                chunk_count = 0
                if documents_to_update:
                    chunk_count = chroma_client.add_documents(documents_to_update)
                stage_times['add_documents'] = int(time.time() - stage_start)
                
                chroma_client.set_last_update_time()
                
                chroma_stats = chroma_client.get_collection_stats()
                
                total_documents = len(notion_documents)
                updated_documents = len(documents_to_update)
                skipped_documents = total_documents - updated_documents
                total_execution_time = int(time.time() - total_start_time)
                
                return jsonify({
                    'status': 'success',
                    'message': f'Database updated: {updated_documents} documents updated ({chunk_count} chunks), {deleted_count} documents deleted',
                    'update_type': 'incremental',
                    'execution_time': total_execution_time,
                    'stage_times': stage_times,
                    'statistics': {
                        'total_notion_documents': total_documents,
                        'documents_updated': updated_documents,
                        'chunks_added': chunk_count,
                        'documents_deleted': deleted_count,
                        'skipped_documents': skipped_documents
                    },
                    'chroma_stats': chroma_stats
                })
                
        except Exception as e:
            total_execution_time = int(time.time() - total_start_time)
            return jsonify({
                'status': 'error',
                'message': f'Error updating vector database: {str(e)}',
                'execution_time': total_execution_time
            }), 500

    return run_async(async_handler())
