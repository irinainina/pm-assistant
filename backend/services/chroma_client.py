import chromadb
import hashlib
from concurrent.futures import ThreadPoolExecutor
from services.embeddings import EmbeddingService
from typing import List, Dict, Set
import tiktoken
import datetime

class ChromaClient:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./data/chroma")
        self.collection = self.client.get_or_create_collection(
            name="pm_documents",
            metadata={"hnsw:space": "cosine"}
        )
        self.embedding_service = EmbeddingService()
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self._last_update_time = None

    def set_last_update_time(self):
        self._last_update_time = datetime.datetime.utcnow().isoformat() + "Z"

    def get_last_update_time(self):
        return self._last_update_time

    def _generate_content_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_existing_hashes(self) -> Set[str]:
        existing_hashes = set()
        try:
            results = self.collection.get(include=['metadatas'], limit=10000)
            for metadata in results['metadatas']:
                if 'content_hash' in metadata:
                    existing_hashes.add(metadata['content_hash'])
        except Exception:
            pass
        return existing_hashes

    def _split_into_chunks(self, text: str, max_tokens: int = 100) -> List[str]:
        tokens = self.tokenizer.encode(text)
        chunks = []
        for i in range(0, len(tokens), max_tokens):
            chunk_tokens = tokens[i:i + max_tokens]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text)
        return chunks

    def _process_single_document(self, doc: Dict, existing_hashes: Set[str]) -> Dict:
        try: 
            title = doc.get('title', '') or doc.get('properties', {}).get('title', 'Untitled') or 'Untitled'
            content = doc.get('content', '')
            page_id = doc['id']
            url = doc['url']
            full_content = content
            page_language = self.embedding_service.detect_language(f"{title} {content}")

            chunk_data = {'texts': [], 'metadatas': [], 'ids': [], 'content_hashes': []}

            if title:
                title_text = title.strip()
                title_hash = self._generate_content_hash(title_text)
                if title_hash not in existing_hashes:
                    chunk_data['texts'].append(title_text)
                    chunk_data['metadatas'].append({
                        'source_id': page_id,
                        'source_url': url,
                        'title': title,
                        'chunk_type': 'title',
                        'language': page_language,
                        'content_hash': title_hash,
                        'full_content': full_content
                    })
                    chunk_data['ids'].append(f"{page_id}_title")
                    chunk_data['content_hashes'].append(title_hash)

            if content:
                content_chunks = self._split_into_chunks(content, max_tokens=100)
                for i, chunk in enumerate(content_chunks):
                    if not chunk.strip():
                        continue
                    chunk_text = chunk.strip()
                    content_hash = self._generate_content_hash(chunk_text)
                    if content_hash in existing_hashes:
                        continue
                    chunk_data['texts'].append(chunk_text)
                    chunk_data['metadatas'].append({
                        'source_id': page_id,
                        'source_url': url,
                        'title': title,
                        'chunk_type': 'content',
                        'chunk_index': i,
                        'language': page_language,
                        'content_hash': content_hash,
                        'full_content': full_content
                    })
                    chunk_data['ids'].append(f"{page_id}_content_{i}")
                    chunk_data['content_hashes'].append(content_hash)

            return chunk_data
        except Exception:
            return {'texts': [], 'metadatas': [], 'ids': [], 'content_hashes': []}

    def add_documents(self, documents: List[Dict], batch_size: int = 200) -> int:
        if not documents:
            return 0
        existing_hashes = self._get_existing_hashes()
        all_chunk_data = {'texts': [], 'metadatas': [], 'ids': [], 'content_hashes': []}
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(self._process_single_document, doc, existing_hashes) for doc in documents]
            for future in futures:
                try:
                    chunk_data = future.result()
                    all_chunk_data['texts'].extend(chunk_data['texts'])
                    all_chunk_data['metadatas'].extend(chunk_data['metadatas'])
                    all_chunk_data['ids'].extend(chunk_data['ids'])
                    all_chunk_data['content_hashes'].extend(chunk_data['content_hashes'])
                except Exception:
                    pass
        if not all_chunk_data['texts']:
            return 0
        total_added = 0
        for i in range(0, len(all_chunk_data['texts']), batch_size):
            batch_texts = all_chunk_data['texts'][i:i + batch_size]
            batch_metadatas = all_chunk_data['metadatas'][i:i + batch_size]
            batch_ids = all_chunk_data['ids'][i:i + batch_size]
            embeddings = self.embedding_service.generate_embeddings(batch_texts)
            if embeddings:
                try:
                    self.collection.add(
                        embeddings=embeddings,
                        documents=batch_texts,
                        metadatas=batch_metadatas,
                        ids=batch_ids
                    )
                    total_added += len(batch_texts)
                except Exception:
                    pass
        return total_added

    def search(self, query: str, n_results: int = 20) -> Dict:
        try:
            query_embeddings = self.embedding_service.generate_embeddings([
                query,
                f"{query} (у назві або темі статті)"
            ])
            semantic_results = self.collection.query(
                query_embeddings=[query_embeddings[0]],
                n_results=min(n_results * 5, 100),
                include=["documents", "metadatas", "distances"]
            )
            title_results = self.collection.query(
                query_embeddings=[query_embeddings[1]],
                n_results=min(n_results * 5, 100),
                include=["documents", "metadatas", "distances"]
            )
            merged = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
            if semantic_results and semantic_results.get("metadatas"):
                merged["documents"][0].extend(semantic_results["documents"][0])
                merged["metadatas"][0].extend(semantic_results["metadatas"][0])
                merged["distances"][0].extend(semantic_results["distances"][0])
            if title_results and title_results.get("metadatas"):
                merged["documents"][0].extend(title_results["documents"][0])
                merged["metadatas"][0].extend(title_results["metadatas"][0])
                merged["distances"][0].extend(title_results["distances"][0])
            return self._group_results_by_page(merged, n_results)
        except Exception:
            return {"results": [], "total_pages": 0}

    def _group_results_by_page(self, raw_results: Dict, max_pages: int = 10) -> Dict:
        try:
            pages = {}
            distances = raw_results.get('distances', [[]])[0]
            metadatas = raw_results.get('metadatas', [[]])[0]
            documents = raw_results.get('documents', [[]])[0]

            for i, metadata in enumerate(metadatas):
                if i >= len(distances) or i >= len(documents):
                    continue
                source_id = metadata.get('source_id')
                if not source_id:
                    continue
                distance = distances[i]
                similarity = 1.0 / (1.0 + float(distance))
                chunk_type = metadata.get('chunk_type', 'content')

                if source_id not in pages:
                    pages[source_id] = {
                        'url': metadata.get('source_url', ''),
                        'title': metadata.get('title', 'Untitled'),
                        'page_id': source_id,
                        'title_similarity': 0.0,
                        'content_similarities': [],
                        'language': metadata.get('language', 'unknown'),
                        'full_content': metadata.get('full_content', '')
                    }

                if chunk_type == 'title':
                    pages[source_id]['title_similarity'] = max(pages[source_id]['title_similarity'], similarity)
                elif chunk_type == 'content':
                    pages[source_id]['content_similarities'].append(similarity)

            final_results = []
            for page_id, p in pages.items():
                title_similarity = p['title_similarity']
                content_similarities = sorted(p['content_similarities'], reverse=True)
                chunk_count = len(content_similarities)

                if chunk_count == 0:
                    best_content_similarity = 0.0
                elif chunk_count == 1:
                    best_content_similarity = content_similarities[0]
                elif chunk_count <= 5:
                    best_content_similarity = sum(content_similarities[:chunk_count]) / chunk_count
                elif chunk_count < 10:
                    best_content_similarity = sum(content_similarities[:3]) / 3.0
                else:
                    best_content_similarity = sum(content_similarities[:5]) / 5.0

                if chunk_count < 3:
                    title_weight = 2.0
                elif chunk_count < 10:
                    title_weight = 3.0
                else:
                    title_weight = 4.0

                if title_similarity > 0.6:
                    title_bonus = 1 + (title_similarity - 0.6) * 2.0
                elif title_similarity > 0.5:
                    title_bonus = 1 + (title_similarity - 0.5) * 1.0
                else:
                    title_bonus = 1.0

                raw_score = ((best_content_similarity * title_bonus) + (title_similarity * title_weight)) / (title_weight + 1)

                match_type = 'none'
                if title_similarity >= best_content_similarity and title_similarity > 0:
                    match_type = 'title'
                elif best_content_similarity > 0:
                    match_type = 'content'

                final_results.append({
                    'page_id': page_id,
                    'url': p['url'],
                    'title': p['title'],
                    'raw_score': raw_score,
                    'title_similarity': round(title_similarity, 4),
                    'content_similarity': round(best_content_similarity, 4),
                    'content_snippet': p['full_content'],
                    'language': p['language'],
                    'match_type': match_type
                })

            if not final_results:
                return {'results': [], 'total_pages': 0}

            min_score = min(r['raw_score'] for r in final_results)
            max_score = max(r['raw_score'] for r in final_results)
            for r in final_results:
                r['relevance_score'] = round((r['raw_score'] - min_score) / (max_score - min_score), 4) if max_score != min_score else 0.0

            final_results.sort(key=lambda x: x['relevance_score'], reverse=True)
            return {'results': final_results[:max_pages], 'total_pages': len(final_results)}
        except Exception:
            return {'results': [], 'total_pages': 0}
        
    def get_collection_stats(self) -> dict:
        try:
            collection_info = self.collection.count()
            return {
                "total_chunks": collection_info.get("count", 0)
            }
        except Exception:
            return {"total_chunks": 0}

    def clear_collection(self) -> bool:
        try:
            self.collection.delete()
            return True
        except Exception:
            return False
