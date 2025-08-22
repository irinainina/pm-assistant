from sentence_transformers import SentenceTransformer
from lingua import Language, LanguageDetectorBuilder

class EmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.language_detector = LanguageDetectorBuilder.from_languages(
            Language.ENGLISH, Language.RUSSIAN, Language.UKRAINIAN
        ).build()
    
    def generate_embeddings(self, texts):
        return self.model.encode(texts).tolist()
    
    def detect_language(self, text):
        try:
            language = self.language_detector.detect_language_of(text)
            return language.iso_code_639_1.name.lower() if language else 'unknown'
        except:
            return 'unknown'
        