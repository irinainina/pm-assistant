from flask import Flask, jsonify, request
from flask_cors import CORS
from services.notion_client import NotionClient
from services.chroma_client import ChromaClient
from services.ai_engine import AIEngine
from routes.ask import ask_blueprint
from utils.db_state import get_last_update_time, set_last_update_time
import datetime
import asyncio

app = Flask(__name__)
CORS(app)

notion_client = NotionClient()
chroma_client = ChromaClient()
ai_engine = AIEngine()

db_initialized = False

app.register_blueprint(ask_blueprint, url_prefix='/api')

def run_async(async_func):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(async_func)
    finally:
        loop.close()

@app.route('/api/search', methods=['GET'])
def get_answer():
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'})
    
    search_results = chroma_client.search(query, n_results=15)
    
    if not search_results or not search_results['documents']:
        return jsonify({
            'query': query,
            'answer': 'No relevant information found.',
            'sources': [],
            'message': 'No results found'
        })
   
    answer = run_async(ai_engine.generate_answer(query, search_results))
    
    sources = chroma_client.get_unique_sources(search_results, max_sources=5)
    
    return jsonify({
        'query': query,
        'answer': answer,
        'sources': sources
    })

@app.route('/api/chroma', methods=['GET'])
def search_documents():
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'})
 
    search_results = chroma_client.search(query, n_results=10)
   
    if not search_results or not search_results['documents']:
        return jsonify({
            'query': query,
            'sources': [],
            'chunks': [],
            'message': 'No results found'
        })
   
    sources = chroma_client.get_unique_sources(search_results, max_sources=5)    
   
    response = {
        'query': query,
        'sources': sources,
        'chunks': []
    }
       
    documents = search_results['documents'][0] if search_results['documents'] else []
    metadatas = search_results['metadatas'][0] if search_results['metadatas'] else []
    distances = search_results['distances'][0] if search_results['distances'] else []
    
    for i, (chunk, metadata, distance) in enumerate(zip(documents, metadatas, distances)):
        response['chunks'].append({
            'text': chunk[:200] + '...' if len(chunk) > 200 else chunk,
            'source': metadata.get('title', 'Unknown'),
            'url': metadata.get('source_url', ''),
            'similarity': round(1.0 - distance, 4),
            'language': metadata.get('language', 'unknown')
        })
    
    return jsonify(response)

@app.route('/api/notion/documents/parsed', methods=['GET'])
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

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': 'PM Assistant API is running'})

@app.route('/api/notion/update_vector_db', methods=['POST'])
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

@app.route('/api/notion/status', methods=['GET'])
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
