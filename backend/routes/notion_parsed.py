from flask import Blueprint, jsonify
from services.notion_client import NotionClient
import asyncio

notion_parsed_blueprint = Blueprint('notion_parsed', __name__)

def run_async(coro):
    """Run async function in sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@notion_parsed_blueprint.route('/notion/documents/parsed', methods=['GET'])
def get_parsed_documents():
    async def async_handler():
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
            
            return jsonify({
                'documents': parsed_documents,
                'total_count': len(parsed_documents)
            })
        finally:
            await notion_client.close()
    
    return run_async(async_handler())
