from sentence_transformers import SentenceTransformer
from lingua import Language, LanguageDetectorBuilder
import re
import emoji

class EmbeddingService:
    _model = None

    def __init__(self):
        if EmbeddingService._model is None:
            EmbeddingService._model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.model = EmbeddingService._model
        self.language_detector = LanguageDetectorBuilder.from_languages(
            Language.ENGLISH, Language.RUSSIAN, Language.UKRAINIAN
        ).build()

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

    def generate_embeddings(self, texts, batch_size: int = 32):
        if not texts:
            return []
        if isinstance(texts, str):
            texts = [texts]
        texts = [self._clean_text(t) for t in texts if t and isinstance(t, str)]
        if not texts:
            return []
        if len(texts) == 1:
            return [self.model.encode(texts[0], show_progress_bar=False, convert_to_tensor=False).tolist()]
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

    def detect_language(self, text):
        try:
            language = self.language_detector.detect_language_of(text)
            return language.iso_code_639_1.name.lower() if language else 'unknown'
        except Exception:
            return 'unknown'
