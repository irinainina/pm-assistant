from flask import Blueprint, request, jsonify
import os
import traceback
import stat

# модули для отображения владельца (в linux)
try:
    import pwd
    import grp
except Exception:
    pwd = None
    grp = None

from services.chroma_client import ChromaClient

chroma_blueprint = Blueprint('chroma', __name__)


def _is_running_in_docker() -> bool:
    """Простая эвристика: /.dockerenv или cgroup содержит 'docker' / 'kubepods'"""
    try:
        if os.path.exists('/.dockerenv'):
            return True
        # проверяем /proc/1/cgroup
        if os.path.exists('/proc/1/cgroup'):
            with open('/proc/1/cgroup', 'rt') as f:
                content = f.read()
                if 'docker' in content or 'kubepods' in content or 'containerd' in content:
                    return True
    except Exception:
        pass
    return False


def _mount_info_for_path(path: str) -> dict:
    """
    Пытается найти точку монтирования для path и вернуть опции монтирования.
    Возвращает {'mount_point': ..., 'options': 'rw,relatime', 'is_ro': True/False} или {}
    """
    try:
        path = os.path.abspath(path)
        best_match = {'mount_point': None, 'options': None, 'is_ro': None}
        if os.path.exists('/proc/mounts'):
            with open('/proc/mounts', 'rt') as f:
                mounts = [line.split() for line in f.readlines()]
            # находим наиболее длинный mountpoint, являющийся префиксом пути
            candidate = None
            for parts in mounts:
                if len(parts) >= 4:
                    mount_point = parts[1]
                    options = parts[3]
                    if path.startswith(mount_point.rstrip('/')) or mount_point == '/':
                        if candidate is None or len(mount_point) > len(candidate[1]):
                            candidate = (parts[0], mount_point, parts[2], options)
            if candidate:
                options = candidate[3]
                is_ro = 'ro' in options.split(',')
                return {
                    'mount_point': candidate[1],
                    'filesystem': candidate[2],
                    'options': options,
                    'is_readonly': is_ro
                }
    except Exception:
        pass
    return {}


@chroma_blueprint.route('/chroma/diagnostic', methods=['GET'])
def chroma_diagnostic():
    """
    Возвращает подробную диагностику окружения и состояния ChromaDB.
    Проверяет:
      - cwd
      - наличие ./data и ./data/chroma
      - флаги докера
      - права (uid, gid, mode), доступ на чтение/запись
      - информацию о точке монтирования (ro/rw)
      - инициализацию ChromaClient и базовые операции (count, embedding, search)
    """
    diagnostic_info = {
        'status': 'checking',
        'environment': {},
        'path_checks': {},
        'mount': {},
        'chroma_init': {},
        'errors': []
    }

    try:
        # окружение
        diagnostic_info['environment'] = {
            'cwd': os.getcwd(),
            'running_in_docker': _is_running_in_docker(),
            'CHROMA_DB_PATH_env': os.environ.get('CHROMA_DB_PATH', None),
            'PYTHON_VERSION': os.environ.get('PYTHON_VERSION', None)
        }

        # вычислим путь аналогично ChromaClient
        chroma_path = os.path.abspath(os.environ.get('CHROMA_DB_PATH', './data/chroma'))
        data_path = os.path.abspath(os.environ.get('DATA_PATH', './data'))

        diagnostic_info['path_checks'] = {
            'data_path': data_path,
            'data_exists': os.path.exists(data_path),
            'chroma_path': chroma_path,
            'chroma_exists': os.path.exists(chroma_path)
        }

        # права и владение
        try:
            st = os.stat(chroma_path)
            uid = st.st_uid
            gid = st.st_gid
            mode = stat.S_IMODE(st.st_mode)
            owner = None
            group = None
            if pwd and grp:
                try:
                    owner = pwd.getpwuid(uid).pw_name
                    group = grp.getgrgid(gid).gr_name
                except Exception:
                    owner = None
                    group = None

            diagnostic_info['path_checks'].update({
                'uid': uid,
                'gid': gid,
                'owner': owner,
                'group': group,
                'mode_octal': oct(mode),
                'is_readable': os.access(chroma_path, os.R_OK),
                'is_writable': os.access(chroma_path, os.W_OK),
            })
        except FileNotFoundError:
            diagnostic_info['path_checks']['note'] = 'chroma_path not found on filesystem'
        except Exception as e:
            diagnostic_info['path_checks']['stat_error'] = str(e)

        # информация о точке монтирования
        try:
            mount_info = _mount_info_for_path(chroma_path)
            diagnostic_info['mount'] = mount_info
        except Exception as e:
            diagnostic_info['mount'] = {'error': str(e)}

        # Пытаемся инициализировать клиент и выполнить базовые операции
        try:
            chroma_client = ChromaClient()
            diagnostic_info['chroma_init']['initialization'] = 'success'
            # добавляем путь, который использует клиент
            diagnostic_info['chroma_init']['client_chroma_path'] = getattr(chroma_client, 'chroma_path', None)

            # count
            try:
                count = chroma_client.collection.count()
                diagnostic_info['chroma_init']['count'] = f"success: {count}"
            except Exception as e:
                diagnostic_info['chroma_init']['count'] = f"failed: {str(e)}"
                diagnostic_info['errors'].append(f"count failed: {str(e)}")

            # генерация single embedding (если есть метод)
            try:
                if hasattr(chroma_client.embedding_service, 'generate_single_embedding'):
                    emb = chroma_client.embedding_service.generate_single_embedding("diagnostic test")
                else:
                    emb_list = chroma_client.embedding_service.generate_embeddings(["diagnostic test"])
                    emb = emb_list[0] if isinstance(emb_list, list) and emb_list else []
                diagnostic_info['chroma_init']['embedding'] = f"success: dims={len(emb)}"
            except Exception as e:
                diagnostic_info['chroma_init']['embedding'] = f"failed: {str(e)}"
                diagnostic_info['errors'].append(f"embedding generation failed: {str(e)}")

            # короткий поиск
            try:
                search_results = chroma_client.search("diagnostic test", n_results=1)
                # определяем количество найденных документов в ответе
                docs = search_results.get('documents', [[]])
                doc_count = len(docs[0]) if docs and isinstance(docs, list) and docs[0] else 0
                diagnostic_info['chroma_init']['search'] = f"success: {doc_count} docs"
            except Exception as e:
                diagnostic_info['chroma_init']['search'] = f"failed: {str(e)}"
                diagnostic_info['errors'].append(f"search failed: {str(e)}")

        except Exception as e:
            diagnostic_info['chroma_init']['initialization'] = f"failed: {str(e)}"
            diagnostic_info['errors'].append(f"initialization failed: {str(e)}")
            diagnostic_info['chroma_init']['traceback'] = traceback.format_exc()

        diagnostic_info['status'] = 'completed'

    except Exception as e:
        diagnostic_info['status'] = 'error'
        diagnostic_info['errors'].append(str(e))
        diagnostic_info['traceback'] = traceback.format_exc()

    return jsonify(diagnostic_info)


@chroma_blueprint.route('/chroma/simple-test', methods=['GET'])
def chroma_simple_test():
    """Минимальная проверка: инициализация клиента и генерация эмбеддинга"""
    try:
        client = ChromaClient()
        if hasattr(client.embedding_service, 'generate_single_embedding'):
            emb = client.embedding_service.generate_single_embedding("simple test")
        else:
            emb_list = client.embedding_service.generate_embeddings(["simple test"])
            emb = emb_list[0] if emb_list else []
        return jsonify({
            'status': 'success',
            'embedding_generated': bool(emb),
            'embedding_dimensions': len(emb) if emb else 0,
            'chroma_path': getattr(client, 'chroma_path', None)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc()
        })


@chroma_blueprint.route('/chroma', methods=['GET'])
def search_documents():
    """Поиск с обработкой ошибок (использовать ?q=...)"""
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400

    try:
        client = ChromaClient()
        search_results = client.search(query, n_results=10)

        documents = search_results.get('documents', [[]])[0] if search_results.get('documents') else []
        metadatas = search_results.get('metadatas', [[]])[0] if search_results.get('metadatas') else []
        distances = search_results.get('distances', [[]])[0] if search_results.get('distances') else []

        if not documents:
            return jsonify({
                'query': query,
                'sources': [],
                'chunks': [],
                'message': 'No results found'
            })

        sources = client.get_unique_sources(search_results, max_sources=5)

        response = {
            'query': query,
            'sources': sources,
            'chunks': []
        }

        for i, (chunk, metadata, distance) in enumerate(zip(documents, metadatas, distances)):
            response['chunks'].append({
                'text': chunk[:200] + '...' if isinstance(chunk, str) and len(chunk) > 200 else chunk,
                'source': metadata.get('title', 'Unknown') if isinstance(metadata, dict) else 'Unknown',
                'url': metadata.get('source_url', '') if isinstance(metadata, dict) else '',
                'similarity': round(1.0 - distance, 4) if isinstance(distance, (int, float)) else None,
                'language': metadata.get('language', 'unknown') if isinstance(metadata, dict) else 'unknown'
            })

        return jsonify(response)

    except Exception as e:
        return jsonify({
            'error': f'Search failed: {str(e)}',
            'query': query,
            'suggestion': 'Check /api/chroma/diagnostic for details',
            'traceback': traceback.format_exc()
        }), 500
    
@chroma_blueprint.route('/chroma/performance-test', methods=['GET'])
def performance_test():
    """Быстрый тест производительности поиска"""
    import time
    
    test_queries = [
        "test",
        "проект",
        "управление",
        "дизайн"
    ]
    
    results = []
    
    for query in test_queries:
        try:
            start_time = time.time()
            client = ChromaClient()
            search_results = client.search(query, n_results=3)
            end_time = time.time()
            
            results.append({
                'query': query,
                'response_time_ms': round((end_time - start_time) * 1000, 2),
                'documents_found': len(search_results.get('documents', [[]])[0]),
                'status': 'success'
            })
        except Exception as e:
            results.append({
                'query': query,
                'response_time_ms': None,
                'documents_found': 0,
                'status': 'error',
                'error': str(e)
            })
    
    return jsonify({
        'performance_test': results,
        'environment': 'docker' if _is_running_in_docker() else 'local'
    })



# from flask import Blueprint, request, jsonify
# from services.chroma_client import ChromaClient

# chroma_blueprint = Blueprint('chroma', __name__)
# chroma_client = ChromaClient()

# @chroma_blueprint.route('/chroma', methods=['GET'])
# def search_documents():
#     query = request.args.get('q')
#     if not query:
#         return jsonify({'error': 'Query parameter "q" is required'})
 
#     search_results = chroma_client.search(query, n_results=10)
   
#     if not search_results or not search_results['documents']:
#         return jsonify({
#             'query': query,
#             'sources': [],
#             'chunks': [],
#             'message': 'No results found'
#         })
   
#     sources = chroma_client.get_unique_sources(search_results, max_sources=5)    
   
#     response = {
#         'query': query,
#         'sources': sources,
#         'chunks': []
#     }
       
#     documents = search_results['documents'][0] if search_results['documents'] else []
#     metadatas = search_results['metadatas'][0] if search_results['metadatas'] else []
#     distances = search_results['distances'][0] if search_results['distances'] else []
    
#     for i, (chunk, metadata, distance) in enumerate(zip(documents, metadatas, distances)):
#         response['chunks'].append({
#             'text': chunk[:200] + '...' if len(chunk) > 200 else chunk,
#             'source': metadata.get('title', 'Unknown'),
#             'url': metadata.get('source_url', ''),
#             'similarity': round(1.0 - distance, 4),
#             'language': metadata.get('language', 'unknown')
#         })
    
#     return jsonify(response)
