import chromadb
import hashlib
from concurrent.futures import ThreadPoolExecutor
from services.embeddings import EmbeddingService
from datetime import datetime
from typing import List, Dict, Set

class ChromaClient:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./data/chroma")
        self.collection = self.client.get_or_create_collection(
            name="pm_documents",
            metadata={"hnsw:space": "cosine"}
        )
        self.embedding_service = EmbeddingService()
        self._embedding_cache = {}
    
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
    
    def _process_single_document(self, doc: Dict, existing_hashes: Set[str]) -> Dict:
        try: 
            title = doc.get('title') 
            if not title and 'properties' in doc:
                title = doc['properties'].get('title', 'Untitled')
                
            if not title:
                title = 'Untitled'
                
            chunks = self._chunk_document(doc.get('content', ''))
            chunk_data = {
                'texts': [],
                'metadatas': [],
                'ids': [],
                'content_hashes': []
            }
            
            for i, chunk in enumerate(chunks):
                content_hash = self._generate_content_hash(chunk)
                
                if content_hash in existing_hashes:
                    continue
                
                language = self.embedding_service.detect_language(chunk)
                chunk_id = f"{doc['id']}_{i}"
                
                chunk_data['texts'].append(chunk)
                chunk_data['metadatas'].append({
                    'source_id': doc['id'],
                    'source_url': doc['url'],
                    'title': title,
                    'chunk_index': i,
                    'language': language,
                    'content_hash': content_hash
                })
                chunk_data['ids'].append(chunk_id)
                chunk_data['content_hashes'].append(content_hash)
            
            return chunk_data
        except Exception:
            return {'texts': [], 'metadatas': [], 'ids': [], 'content_hashes': []}
    
    def add_documents(self, documents: List[Dict], batch_size: int = 200) -> int:
        if not documents:
            return 0
        
        existing_hashes = self._get_existing_hashes()
        
        all_chunk_data = {
            'texts': [],
            'metadatas': [],
            'ids': [],
            'content_hashes': []
        }
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for doc in documents:
                future = executor.submit(self._process_single_document, doc, existing_hashes)
                futures.append(future)
            
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
            batch_hashes = all_chunk_data['content_hashes'][i:i + batch_size]
            
            embeddings = self._get_cached_embeddings(batch_texts, batch_hashes)
            
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
    
    def _get_cached_embeddings(self, texts: List[str], hashes: List[str]) -> List[List[float]]:
        embeddings = []
        texts_to_generate = []
        hash_indices = []
        
        for i, content_hash in enumerate(hashes):
            if content_hash in self._embedding_cache:
                embeddings.append(self._embedding_cache[content_hash])
            else:
                texts_to_generate.append(texts[i])
                hash_indices.append(i)
        
        if texts_to_generate:
            new_embeddings = self.embedding_service.generate_embeddings(texts_to_generate)
            
            for j, embedding in enumerate(new_embeddings):
                original_index = hash_indices[j]
                content_hash = hashes[original_index]
                self._embedding_cache[content_hash] = embedding
                embeddings.append(embedding)
       
        sorted_embeddings = []
        for content_hash in hashes:
            for i, emb in enumerate(embeddings):
                if content_hash == hashes[i % len(hashes)]:
                    sorted_embeddings.append(emb)
                    break
        
        return sorted_embeddings
    
    def _chunk_document(self, text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
        if not text:
            return []
       
        try:
            if isinstance(text, str):
                text = text.encode('utf-8', errors='replace').decode('utf-8')
        except Exception:
            return []
        
        words = text.split()
        if len(words) <= chunk_size:
            return [text] if text.strip() else []
        
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            chunk_text = " ".join(chunk_words)
            if chunk_text.strip():
                chunks.append(chunk_text)
            
            if i + chunk_size >= len(words):
                break
        
        return chunks
    
    def search(self, query: str, n_results: int = 10) -> Dict:
        try:
            query_embedding = self.embedding_service.generate_embeddings([query])
            
            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            return results
        except Exception:
            return {'documents': [], 'metadatas': [], 'distances': []}
    
    def get_unique_sources(self, search_results: Dict, max_sources: int = 5) -> List[Dict]:
        try:
            unique_sources = {}
            
            distances = search_results.get('distances', [[]])[0]
            metadatas = search_results.get('metadatas', [[]])[0]
            
            for i, metadata in enumerate(metadatas):
                source_id = metadata.get('source_id')
                if not source_id:
                    continue
                    
                distance = distances[i] if i < len(distances) else 1.0
                similarity = round(1.0 - distance, 4)
                
                if source_id not in unique_sources or similarity > unique_sources[source_id]['score']:
                    unique_sources[source_id] = {
                        'url': metadata.get('source_url', ''),
                        'title': metadata.get('title', 'Untitled'),
                        'score': similarity
                    }
            
            sorted_sources = sorted(
                unique_sources.values(),
                key=lambda x: x['score'],
                reverse=True
            )[:max_sources]
            
            return sorted_sources
        except Exception:
            return []
    
    def clear_collection(self) -> bool:
        try:
            all_results = self.collection.get(limit=10000)
            if all_results and all_results['ids']:
                self.collection.delete(ids=all_results['ids'])
            self._embedding_cache.clear()
            return True
        except Exception as e:
            print(f"Error clearing collection: {e}")
            return False
    
    def update_documents(self, documents: List[Dict]) -> int:
        if not documents:
            return 0
        
        try:
            source_ids_to_remove = [doc['id'] for doc in documents]
            
            for source_id in source_ids_to_remove:
                try:
                    self.collection.delete(where={"source_id": source_id})
                except Exception:
                    pass
            
            return self.add_documents(documents)
        except Exception:
            return 0
    
    def get_collection_stats(self) -> Dict:
        try:
            count = self.collection.count()
            return {
                'total_chunks': count,
                'embedding_cache_size': len(self._embedding_cache)
            }
        except Exception:
            return {'total_chunks': 0, 'embedding_cache_size': 0}

    def set_last_update_time(self):
        current_time = datetime.utcnow().isoformat() + "Z"
        self.collection.upsert(
            ids=["__last_update__"],
            metadatas=[{"last_update_time": current_time}],
            documents=["system_record"]
        )

    def get_last_update_time(self):
        results = self.collection.get(ids=["__last_update__"])
        if results and "metadatas" in results and results["metadatas"]:
            meta = results["metadatas"][0]
            if meta and "last_update_time" in meta:
                return meta["last_update_time"]
        return None

