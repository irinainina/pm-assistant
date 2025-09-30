from flask import Blueprint, request, jsonify
from services.chroma_client import ChromaClient
from services.ai_engine import AIEngine
import asyncio

chroma_client = ChromaClient()
ai_engine = AIEngine()
search_blueprint = Blueprint('search', __name__)

def run_async(async_func):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(async_func)
    finally:
        loop.close()

@search_blueprint.route('/search', methods=['GET'])
def search_question():
    try:
        query = request.args.get('query') or request.args.get('q')
        history = request.args.get('history', [])
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400

        search_results = chroma_client.search(query, n_results=10)
        
        if not search_results or not search_results['documents']:
            return jsonify({
                'query': query,
                'answer': 'I could not find any relevant information to answer your question.',
                'sources': [],
                'debug': {
                    'search_results': search_results,
                    'message': 'No documents found in search results'
                }
            })

        detected_language = run_async(ai_engine._detect_language_async(query))
        extracted_context = run_async(ai_engine._extract_context_async(search_results))
        system_prompt = ai_engine._create_system_prompt(detected_language)
        user_prompt = ai_engine._create_user_prompt(query, extracted_context, detected_language)

        answer = run_async(ai_engine.generate_answer(
            query=query, 
            search_results=search_results,
            history=history
        ))

        sources = chroma_client.get_unique_sources(search_results, max_sources=5)
 
        debug_info = {
            'ai_engine_input': {
                'query': query,
                'search_results_raw': search_results,
                'history': history
            },
            'ai_engine_processing': {
                'detected_language': detected_language,
                'system_prompt': system_prompt,
                'user_prompt': user_prompt,
                'extracted_context': extracted_context,
                'extracted_context_length': len(extracted_context)
            },
            'ai_engine_output': {
                'answer': answer,
                'answer_length': len(answer),
                'sources_count': len(sources),
                'sources': sources
            }
        }
        
        return jsonify({
            'query': query,            
            'sources': sources,
            'answer': answer,
            'debug': debug_info
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@search_blueprint.route('/search/debug', methods=['GET'])
def debug_chroma():
    """Диагностический роут для проверки ChromaDB"""
    try:
        from services.chroma_client import ChromaClient
        chroma = ChromaClient()
        
        # 1. Проверим общее количество документов в базе
        collection = chroma.collection
        count = collection.count()
        
        # 2. Попробуем найти документ по URL ретроспективы
        target_url = "https://www.notion.so/halolab/44468d279d024f84b98ac4556680892d"
        target_id = "44468d279d024f84b98ac4556680892d"
        
        # Поиск по metadata
        results_by_url = collection.get(
            where={"source_url": {"$eq": target_url}},
            limit=1
        )
        
        results_by_id = collection.get(
            where={"source_id": {"$eq": target_id}},
            limit=1
        )
        
        # 3. Поиск по тексту "ретроспектив"
        text_results = collection.query(
            query_texts=["ретроспектив"],
            n_results=5
        )
        
        # 4. Получить несколько случайных документов для проверки
        sample_docs = collection.get(limit=5)
        
        debug_info = {
            "chroma_status": "connected",
            "total_documents": count,
            "search_by_url": {
                "url": target_url,
                "found": len(results_by_url['ids'][0]) if results_by_url['ids'] else 0,
                "documents": results_by_url['documents'] if results_by_url['documents'] else []
            },
            "search_by_id": {
                "id": target_id,
                "found": len(results_by_id['ids'][0]) if results_by_id['ids'] else 0,
                "documents": results_by_id['documents'] if results_by_id['documents'] else []
            },
            "search_by_text": {
                "query": "ретроспектив",
                "results": {
                    "documents": text_results['documents'][0] if text_results['documents'] else [],
                    "metadatas": text_results['metadatas'][0] if text_results['metadatas'] else [],
                    "distances": text_results['distances'][0] if text_results['distances'] else []
                }
            },
            "sample_documents": {
                "ids": sample_docs['ids'][:3] if sample_docs['ids'] else [],
                "titles": [meta.get('title', 'No title') for meta in sample_docs['metadatas'][:3]] if sample_docs['metadatas'] else [],
                "urls": [meta.get('source_url', 'No URL') for meta in sample_docs['metadatas'][:3]] if sample_docs['metadatas'] else []
            }
        }
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "chroma_status": "error"
        }), 500
    
@search_blueprint.route('/search/chroma_stats', methods=['GET'])
def chroma_stats():
    try:
        from services.chroma_client import ChromaClient
        chroma = ChromaClient()
        collection = chroma.collection
        
        # 1. Получить ВСЕ документы из ChromaDB
        all_docs = collection.get(limit=10000)
        
        # Проверить что данные есть
        if not all_docs or not all_docs.get('ids'):
            return jsonify({
                "chroma_status": "empty",
                "message": "No documents in ChromaDB"
            })
        
        # 2. Статистика по источникам
        source_stats = {}
        total_chunks = len(all_docs['ids'])
        
        for i in range(total_chunks):
            metadata = all_docs['metadatas'][i] if i < len(all_docs['metadatas']) else {}
            document = all_docs['documents'][i] if i < len(all_docs['documents']) else ""
            
            source_id = metadata.get('source_id', 'unknown')
            source_title = metadata.get('title', 'No Title')
            
            if source_id not in source_stats:
                source_stats[source_id] = {
                    'title': source_title,
                    'total_chunks': 0,
                    'chunk_indices': [],
                    'url': metadata.get('source_url', ''),
                    'sample_content': document[:200] if document else ''
                }
            
            source_stats[source_id]['total_chunks'] += 1
            source_stats[source_id]['chunk_indices'].append(metadata.get('chunk_index', 0))
        
        # 3. Найти статью о ретроспективах
        retro_sources = {}
        for source_id, stats in source_stats.items():
            if "44468d27" in source_id or "ретроспектив" in stats['title'].lower() or "ретроспектив" in stats['sample_content'].lower():
                retro_sources[source_id] = stats
        
        # 4. Проверить конкретную статью
        target_article = source_stats.get("44468d27-9d02-4f84-b98a-c4556680892d")
        
        diagnostic_info = {
            "chroma_status": "connected",
            "total_chunks_in_db": total_chunks,
            "unique_sources": len(source_stats),
            "sources_sample": dict(list(source_stats.items())[:5]),  # первые 5 источников
            "retrospective_sources_found": retro_sources,
            "target_article_44468d27": target_article,
            "all_source_titles": [stats['title'] for stats in source_stats.values()][:20]  # первые 20 заголовков
        }
        
        return jsonify(diagnostic_info)
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "chroma_status": "error"
        }), 500
