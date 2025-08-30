from flask import Blueprint, request, jsonify
from services.chroma_client import ChromaClient

chroma_blueprint = Blueprint('chroma', __name__)
chroma_client = ChromaClient()

@chroma_blueprint.route('/chroma', methods=['GET'])
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
