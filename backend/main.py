from flask import Flask, jsonify
from flask_cors import CORS
from services.notion_client import NotionClient

app = Flask(__name__)
CORS(app)

notion_client = NotionClient()

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)


# from flask import Flask, jsonify
# from flask_cors import CORS
# from services.notion_client import NotionClient

# app = Flask(__name__)
# CORS(app)

# notion_client = NotionClient()

# @app.route('/api/notion/test', methods=['GET'])
# def test_notion_connection():
#     success = notion_client.test_connection()
#     return jsonify({'success': success})

# @app.route('/api/notion/properties', methods=['GET'])
# def get_database_properties():
#     properties = notion_client.get_database_properties()
#     return jsonify({'properties': properties})

# @app.route('/api/notion/documents', methods=['GET'])
# def get_documents_metadata():
#     metadata = notion_client.get_all_documents_metadata()
#     return jsonify({'documents': metadata})

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000)
