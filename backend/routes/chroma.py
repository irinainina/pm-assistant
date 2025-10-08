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
    
    if not search_results or not search_results['results']:
        return jsonify({
            'query': query,
            'sources': [],
            'chunks': [],
            'message': 'No results found'
        })

    response = {
        'query': query,
        'sources': [],
        'chunks': [],
        'total_pages': search_results['total_pages']
    }

    for result in search_results['results']:
        source = {
            'url': result['url'],
            'title': result['title'],
            'score': result['relevance_score'],
            'page_id': result['page_id']
        }
        response['sources'].append(source)

        chunk = {
            'text': result['content_snippet'],
            'source': result['title'],
            'url': result['url'],
            'similarity': result['relevance_score'],
            'match_type': result['match_type'],
            'title_score': result['title_similarity'],
            'content_score': result['content_similarity']
        }
        response['chunks'].append(chunk)
    
    return jsonify(response)
