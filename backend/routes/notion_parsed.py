from flask import Blueprint, jsonify
from services.notion_client import NotionClient

notion_parsed_blueprint = Blueprint('notion_parsed', __name__)
notion_client = NotionClient()

@notion_parsed_blueprint.route('/notion/documents/parsed', methods=['GET'])
def get_parsed_documents():
    documents = notion_client.get_all_documents_metadata()
    
    parsed_documents = []
    for doc in documents:
        parsed_documents.append({
            'id': doc['id'],
            'url': doc['url'],
            'content': doc['content'],
            'title': doc['properties'].get('title'),
            'post_id': doc['properties'].get('post')
        })
    
    return jsonify({'documents': parsed_documents})
