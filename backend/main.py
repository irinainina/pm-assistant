from flask import Flask, jsonify, request
from flask_cors import CORS
from services.notion_client import NotionClient
from services.chroma_client import ChromaClient

app = Flask(__name__)
CORS(app)

notion_client = NotionClient()
chroma_client = ChromaClient()

db_initialized = False

@app.before_request
def initialize_vector_db():
    global db_initialized
    if not db_initialized:
        documents = notion_client.get_all_documents_metadata()
        added_count = chroma_client.add_documents(documents)
        print(f"Added {added_count} new chunks to vector DB")
        db_initialized = True

@app.route('/api/search', methods=['GET'])
def search_documents():
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'})
 
    search_results = chroma_client.search(query, n_results=15)
   
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
            'author': doc['properties'].get('author'),
            'date': doc['properties'].get('date'),
            'post_id': doc['properties'].get('post')
        })
    
    return jsonify({'documents': parsed_documents})

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': 'PM Assistant API is running'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
