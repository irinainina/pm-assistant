from openai import AsyncOpenAI
from utils.config import Config
from lingua import Language, LanguageDetectorBuilder
import asyncio

class AIEngine:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
        self.language_detector = LanguageDetectorBuilder.from_languages(
            Language.ENGLISH, Language.RUSSIAN, Language.UKRAINIAN
        ).build()
      
    async def generate_answer(self, query, search_results, history=None):
        language_task = asyncio.create_task(self._detect_language_async(query))
        context_task = asyncio.create_task(self._extract_context_async(search_results))
        
        language, context_text = await asyncio.gather(language_task, context_task)
        
        system_prompt = self._create_system_prompt(language)
        user_prompt = self._create_user_prompt(query, context_text, language)
    
        messages = [{"role": "system", "content": system_prompt}]
   
        if history:
            for msg in history:
                role = msg.get("role")
                content = msg.get("content", "")
                
                if role in ["user", "assistant"]:
                    messages.append({"role": role, "content": content})
 
        messages.append({"role": "user", "content": user_prompt})
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7,
                max_tokens=800,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}"
    
    async def _extract_context_async(self, search_results, max_chunks=5, max_chars=4000):
        return self._extract_context_from_search(search_results, max_chunks, max_chars)
    
    def _extract_context_from_search(self, search_results, max_chunks=5, max_chars=4000):
        if not search_results or not search_results.get('results'):
            return "No relevant context found."
        
        context_parts = []
        total_chars = 0
        
        for i, result in enumerate(search_results['results']):
            if i >= max_chunks:
                break
                
            source_title = result.get('title', 'Unknown source')
            content_snippet = result.get('content_snippet', '')
            relevance_score = result.get('relevance_score', 0)
            
            chunk_text = f"[Source: {source_title} | Relevance: {relevance_score}]\n{content_snippet}"
            
            if total_chars + len(chunk_text) > max_chars:
                remaining_chars = max_chars - total_chars
                if remaining_chars > 100:
                    chunk_text = chunk_text[:remaining_chars] + "..."
                    context_parts.append(chunk_text)
                break
                
            context_parts.append(chunk_text)
            total_chars += len(chunk_text)
        
        return "\n\n".join(context_parts)
    
    async def _detect_language_async(self, text):
        return self._detect_language(text)
    
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
            'english': """You are a helpful Project Management Assistant. Structure response using varied HTML5 semantic tags (<div>, <section>, <h3>-<h6>, <p>, <span>, <ul>/<ol>, <li>, <blockquote>, <strong>, etc). Never start a response with a title. Start directly with content. Use the provided context to answer questions accurately. If the context doesn't contain the exact information, say so but try to provide helpful guidance.""",
            'russian': """Ты помощник по управлению проектами. Структурируй ответ с использованием HTML5 семантических тегов (<div>, <section>, <h3>-<h6>, <p>, <span>, <ul>/<ol>, <li>, <blockquote>, <strong> и др.). Никогда НЕ начинай ответ с заголовка. Начинай сразу с содержимого. Используй предоставленный контекст для точных ответов. Если в контексте есть релевантная информация, дай полный исчерпывающий ответ. Если в контексте нет точной информации, скажи об этом, но попытайся дать полезные рекомендации.""",
            'ukrainian': """Ти помічник з управління проектами. Структуруй відповідь із використанням HTML5 семантичних тегів (<div>, <section>, <h3>-<h6>, <p>, <span>, <ul>/<ol>, <li>, <blockquote>, <strong> тощо). Ніколи НЕ починай відповідь із заголовка. Починай одразу зі змісту. Використовуй наданий контекст для точних відповідей. Якщо в контексті є релевантна інформація, надай повну вичерпну відповідь. Якщо в контексті немає точної інформації, скажи про це, але намагайся надати корисні рекомендації."""
        }
        return prompts.get(language, prompts['english'])
    
    def _create_user_prompt(self, query, context, language):
        prompts = {
            'english': f"""Context information:
            {context}
            Question: {query}
            Please provide a helpful answer in HTML format based on the context above.""",

            'russian': f"""Контекстная информация:
            {context}
            Вопрос: {query}
            Пожалуйста, дай полезный ответ в формате HTML на основе контекста выше.""",

            'ukrainian': f"""Контекстна інформація:
            {context}
            Питання: {query}
            Будь ласка, надай корисну відповідь у форматі HTML на основі контексту вище."""
        }
        return prompts.get(language, prompts['english'])
    