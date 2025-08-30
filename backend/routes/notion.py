from flask import Blueprint, jsonify
from services.notion_client import NotionClient
from services.chroma_client import ChromaClient
from utils.db_state import get_last_update_time, set_last_update_time
import datetime

notion_blueprint = Blueprint('notion', __name__)
notion_client = NotionClient()
chroma_client = ChromaClient()

@notion_blueprint.route('/notion/update_vector_db', methods=['POST'])
def update_vector_db():
    try:
        documents = notion_client.get_all_documents_metadata()
        
        chroma_client.clear_collection()
        added_count = chroma_client.add_documents(documents)

        set_last_update_time()
        
        return jsonify({
            'status': 'success',
            'message': f'Vector database updated successfully with {added_count} chunks',
            'documents_processed': len(documents)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notion_blueprint.route('/notion/status', methods=['GET'])
def get_notion_status():
    try:
        notion_last_edited_str = notion_client.get_last_edited_time() 
        our_last_update_ts = get_last_update_time()
      
        if not our_last_update_ts:
            return jsonify({
                'is_actual': False,
                'notion_last_edited': notion_last_edited_str,
                'our_last_update': None
            })
       
        if notion_last_edited_str:
            dt = datetime.datetime.fromisoformat(notion_last_edited_str.replace('Z', '+00:00'))
            notion_last_edited_ts = dt.timestamp()
        else:
            notion_last_edited_ts = 0

        is_actual = notion_last_edited_ts <= our_last_update_ts

        our_last_update_iso = datetime.datetime.utcfromtimestamp(our_last_update_ts).isoformat() + 'Z'
        
        return jsonify({
            'is_actual': is_actual,
            'notion_last_edited': notion_last_edited_str,
            'our_last_update': our_last_update_iso
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    