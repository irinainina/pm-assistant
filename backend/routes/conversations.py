from flask import Blueprint, request, jsonify
import psycopg2
import os
import json

conversations_bp = Blueprint('conversations', __name__)

def get_db_connection():
    return psycopg2.connect(os.environ.get('DATABASE_URL'))

@conversations_bp.route('/conversations', methods=['GET'])
def get_conversations():    
    user_id = request.headers.get('User-Id')

    if not user_id:
        return jsonify({'error': 'User ID header is required'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'User not found'}), 404

        cursor.execute("""
            SELECT c.id, c.title, c.is_useful, c.last_activity_at, c.created_at,
                   COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            WHERE c.user_id = %s
            GROUP BY c.id, c.title, c.is_useful, c.last_activity_at, c.created_at
            ORDER BY c.last_activity_at DESC
        """, (user_id,))
        
        conversations = []
        for row in cursor.fetchall():
            conversations.append({
                'id': row[0],
                'title': row[1],
                'is_useful': row[2],
                'last_activity_at': row[3].isoformat(),
                'created_at': row[4].isoformat(),
                'message_count': row[5]
            })
        
        cursor.close()
        conn.close()
        
        return jsonify(conversations)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@conversations_bp.route('/conversations/<conversation_id>/messages', methods=['GET'])
def get_conversation_messages(conversation_id):
    user_id = request.headers.get('User-Id')
    
    if not user_id:
        return jsonify({'error': 'User ID header is required'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id FROM conversations 
            WHERE id = %s AND user_id = %s
        """, (conversation_id, user_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'Conversation not found or access denied'}), 404

        cursor.execute("""
            SELECT id, role, content, sources, created_at 
            FROM messages 
            WHERE conversation_id = %s 
            ORDER BY created_at ASC
        """, (conversation_id,))
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                'id': row[0],
                'role': row[1],
                'content': row[2],
                'sources': row[3],
                'created_at': row[4].isoformat()
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'conversation_id': conversation_id,
            'messages': messages
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500