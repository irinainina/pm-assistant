from flask import Blueprint, jsonify
from services.notion_client import NotionClient
import asyncio
import time

notion_parsed_blueprint = Blueprint('notion_parsed', __name__)

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@notion_parsed_blueprint.route('/notion/documents/parsed', methods=['GET'])
def get_parsed_documents():
    async def async_handler():
        start_time = time.time()

        notion_client = NotionClient()
        try:
            documents = await notion_client.get_all_documents_metadata()
            
            parsed_documents = []
            for doc in documents:
                parsed_documents.append({
                    'id': doc['id'],
                    'url': doc['url'],
                    'content': doc['content'],
                    'title': doc['properties'].get('title'),
                    'post_id': doc['properties'].get('post')
                })

            execution_time = int(time.time() - start_time)
            
            return jsonify({
                'total_count': len(parsed_documents),
                'execution_time': execution_time,                
                'documents': parsed_documents                
            })
        finally:
            await notion_client.close()
    
    return run_async(async_handler())
