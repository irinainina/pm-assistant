import chromadb
import hashlib
from services.embeddings import EmbeddingService

class ChromaClient:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./data/chroma")
        self.collection = self.client.get_or_create_collection(
            name="pm_documents",
            metadata={"hnsw:space": "cosine"}
        )
        self.embedding_service = EmbeddingService()
    
    def _generate_document_hash(self, content, metadata):
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        metadata_str = str(sorted(metadata.items()))
        metadata_hash = hashlib.sha256(metadata_str.encode()).hexdigest()
        return f"{content_hash}_{metadata_hash}"
    
    def add_documents(self, documents):
        texts = []
        metadatas = []
        ids = []
      
        existing_hashes = set()
        if self.collection.count() > 0:
            all_metadatas = self.collection.get(include=['metadatas'])['metadatas']
            for metadata in all_metadatas:
                if 'document_hash' in metadata:
                    existing_hashes.add(metadata['document_hash'])
        
        for doc in documents:
            chunks = self._chunk_document(doc['content'])
            
            for i, chunk in enumerate(chunks):
                language = self.embedding_service.detect_language(chunk)
               
                chunk_id = f"{doc['id']}_{i}"
                document_hash = self._generate_document_hash(chunk, {
                    'source_id': doc['id'],
                    'chunk_index': i
                })
              
                if document_hash in existing_hashes:
                    continue
                
                texts.append(chunk)
                metadatas.append({
                    'source_id': doc['id'],
                    'source_url': doc['url'],
                    'title': doc['properties'].get('title', 'Untitled'),
                    'chunk_index': i,
                    'language': language,
                    'document_hash': document_hash
                })
                ids.append(chunk_id)        
        
        if texts:
            embeddings = self.embedding_service.generate_embeddings(texts)
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
        
        return len(ids)
    
    def _chunk_document(self, text, chunk_size=500, overlap=50):
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)
            
            if i + chunk_size >= len(words):
                break
        
        return chunks
    
    def search(self, query, n_results=10):
        query_embedding = self.embedding_service.generate_embeddings([query])
        
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        
        return results
    
    def get_unique_sources(self, search_results, max_sources=5):
        unique_sources = {}        
        
        distances = search_results['distances'][0] if search_results['distances'] else []
        metadatas = search_results['metadatas'][0] if search_results['metadatas'] else []
        
        for i, metadata in enumerate(metadatas):
            source_id = metadata['source_id']
            distance = distances[i] if i < len(distances) else 1.0
            
            if source_id not in unique_sources:
                unique_sources[source_id] = {
                    'url': metadata['source_url'],
                    'title': metadata['title'],
                    'score': round(1.0 - distance, 4)  # Convert distance to similarity
                }
            else:
                current_score = 1.0 - distance
                if current_score > unique_sources[source_id]['score']:
                    unique_sources[source_id]['score'] = round(current_score, 4)
        
        sorted_sources = sorted(
            unique_sources.values(),
            key=lambda x: x['score'],
            reverse=True
        )[:max_sources]
        
        return sorted_sources
    
    def clear_collection(self):
      try:         
          self.client.reset()
          print("ChromaDB collection cleared successfully")
          return True
          
      except Exception as e:
          print(f"Error clearing collection: {e}")
          return False
    