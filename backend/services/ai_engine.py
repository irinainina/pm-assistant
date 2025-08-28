from openai import OpenAI
from utils.config import Config
from lingua import Language, LanguageDetectorBuilder

class AIEngine:
    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.language_detector = LanguageDetectorBuilder.from_languages(
            Language.ENGLISH, Language.RUSSIAN, Language.UKRAINIAN
        ).build()
    
    def generate_answer(self, query, search_results):
        context_text = self._extract_context_from_search(search_results)
        language = self._detect_language(query)
        system_prompt = self._create_system_prompt(language)
        user_prompt = self._create_user_prompt(query, context_text, language)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}"
    
    def _extract_context_from_search(self, search_results, max_chunks=5, max_chars=4000):
        if not search_results or not search_results.get('documents'):
            return "No relevant context found."
        
        context_parts = []
        total_chars = 0
        documents = search_results['documents'][0]
        metadatas = search_results['metadatas'][0]
        
        for i, (document, metadata) in enumerate(zip(documents, metadatas)):
            if i >= max_chunks:
                break
                
            source_title = metadata.get('title', 'Unknown source')
            chunk_text = f"[Source: {source_title}]\n{document}"
            
            if total_chars + len(chunk_text) > max_chars:
                remaining_chars = max_chars - total_chars
                if remaining_chars > 100:
                    chunk_text = chunk_text[:remaining_chars] + "..."
                    context_parts.append(chunk_text)
                break
                
            context_parts.append(chunk_text)
            total_chars += len(chunk_text)
        
        return "\n\n".join(context_parts)
    
    def _detect_language(self, text):
        try:
            language = self.language_detector.detect_language_of(text)
            if language == Language.RUSSIAN:
                return 'russian'
            elif language == Language.UKRAINIAN:
                return 'ukrainian'
            else:
                return 'english'
        except:
            return 'english'
    
    def _create_system_prompt(self, language):
        prompts = {
            'english': """You are a helpful Project Management Assistant. Use the provided context to answer questions accurately. If the context doesn't contain the exact information, say so but try to provide helpful guidance.""",
            'russian': """Вы помощник по управлению проектами. Используйте предоставленный контекст для точных ответов. Если в контексте есть релевантная информация, дайте полный исчерпывающий ответ. Если в контексте нет точной информации, скажите об этом, но попытайтесь дать полезные рекомендации.""",
            'ukrainian': """Ви помічник з управління проектами. Використовуйте наданий контекст для точних відповідей. Якщо в контексті є релевантна інформація, надайте повну вичерпну відповідь. Якщо в контексті немає точної інформації, скажіть про це, але намагайтеся надати корисні рекомендації."""
        }
        return prompts.get(language, prompts['english'])
    
    def _create_user_prompt(self, query, context, language):
        prompts = {
            'english': f"""Context information:
{context}

Question: {query}

Please provide a helpful answer based on the context above.""",
            'russian': f"""Контекстная информация:
{context}

Вопрос: {query}

Пожалуйста, дайте полезный ответ на основе контекста выше.""",
            'ukrainian': f"""Контекстна інформація:
{context}

Питання: {query}

Будь ласка, надайте корисну відповідь на основі контексту вище."""
        }
        return prompts.get(language, prompts['english'])
    