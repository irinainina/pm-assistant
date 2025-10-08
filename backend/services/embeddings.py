from sentence_transformers import SentenceTransformer
from lingua import Language, LanguageDetectorBuilder
import re
import emoji
import tiktoken
from typing import List, Dict

class EmbeddingService:
    _model = None

    def __init__(self):
        if EmbeddingService._model is None:
            EmbeddingService._model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.model = EmbeddingService._model
        self.language_detector = LanguageDetectorBuilder.from_languages(
            Language.ENGLISH, Language.RUSSIAN, Language.UKRAINIAN
        ).build()
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def _clean_text(self, text: str) -> str:
        if not text or not isinstance(text, str):
            return ""
        try:
            text = text.encode('utf-8', errors='replace').decode('utf-8')
        except:
            return ""        
        text = re.sub(r'\\"', '"', text)
        text = emoji.replace_emoji(text, replace="")
        text = re.sub(r"<.*?>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _split_into_chunks(self, text: str, max_tokens: int = 100) -> List[str]:
        tokens = self.tokenizer.encode(text)
        chunks = []
        
        for i in range(0, len(tokens), max_tokens):
            chunk_tokens = tokens[i:i + max_tokens]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text)
        
        return chunks

    def generate_hybrid_embeddings(self, pages: List[Dict]) -> List[Dict]:
        all_embeddings = []
        
        for page in pages:
            if not page.get('id') or not page.get('content'):
                continue
                
            title = page['properties'].get('title', '')
            url = page['url']
            content = page['content']
            page_id = page['id']

            clean_title = self._clean_text(title)
            clean_content = self._clean_text(content)
            
            if not clean_title and not clean_content:
                continue

            if clean_title:
                title_embedding = self.model.encode(
                    clean_title, 
                    show_progress_bar=False, 
                    convert_to_tensor=False
                ).tolist()
                
                all_embeddings.append({
                    'type': 'title',
                    'embedding': title_embedding,
                    'content': clean_title,
                    'page_id': page_id,
                    'url': url
                })

            if clean_content:
                content_chunks = self._split_into_chunks(clean_content, max_tokens=100)
                
                for i, chunk in enumerate(content_chunks):
                    if not chunk.strip():
                        continue
                        
                    content_embedding = self.model.encode(
                        chunk,
                        show_progress_bar=False,
                        convert_to_tensor=False
                    ).tolist()
                    
                    all_embeddings.append({
                        'type': 'content',
                        'embedding': content_embedding,
                        'content': chunk,
                        'page_id': page_id,
                        'url': url,
                        'chunk_index': i
                    })
        
        return all_embeddings

    def detect_language(self, text):
        try:
            language = self.language_detector.detect_language_of(text)
            return language.iso_code_639_1.name.lower() if language else 'unknown'
        except Exception:
            return 'unknown'

    def generate_embeddings(self, texts, batch_size: int = 32):
        if not texts:
            return []
        if isinstance(texts, str):
            texts = [texts]
        texts = [self._clean_text(t) for t in texts if t and isinstance(t, str)]
        if not texts:
            return []
        
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.model.encode(
                batch,
                show_progress_bar=False,
                convert_to_tensor=False
            )
            embeddings.extend(batch_embeddings.tolist())
        return embeddings
