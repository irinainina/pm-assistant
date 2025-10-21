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
                model="gpt-4-1106-preview",
                messages=messages,
                temperature=0.5,
                max_tokens=1500,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}"
    
    async def _extract_context_async(self, search_results, max_chunks=5, max_chars=25000):
        return self._extract_context_from_search(search_results, max_chunks, max_chars)
    
    def _extract_context_from_search(self, search_results, max_chunks=5, max_chars=25000):
        if not search_results or not search_results.get('results'):
            return "No relevant context found."
        
        context_parts = []
        
        top_results = sorted(search_results['results'], 
                           key=lambda x: x.get('relevance_score', 0), 
                           reverse=True)[:max_chunks]
        
        for result in top_results:
            source_title = result.get('title', 'Unknown source')
            content_snippet = result.get('content_snippet', '')
            relevance_score = result.get('relevance_score', 0)
            
            chunk_text = f"[Source: {source_title} | Relevance: {relevance_score}]\n{content_snippet}"
            context_parts.append(chunk_text)
        
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
            'english': """You are a helpful Project Management Assistant. Structure response using varied HTML tags (<div>, <section>, <h3>-<h6>, <p>, <span>, <ul>/<ol>, <li>, <blockquote>, <strong>). Never start a response with a title. Start directly with content. Use the provided context to answer questions accurately. If the context doesn't contain the exact information, say so but try to provide helpful guidance.
            IMPORTANT: RESPOND IN ENGLISH REGARDLESS OF THE LANGUAGE OF THE CONTEXT PROVIDED.""",
            'russian': """Ты помощник по управлению проектами. Структурируй ответ с использованием HTML тегов (<div>, <section>, <h3>-<h6>, <p>, <span>, <ul>/<ol>, <li>, <blockquote>, <strong>). Никогда НЕ начинай ответ с заголовка. Начинай сразу с содержимого. Используй предоставленный контекст для точных ответов. Если в контексте есть релевантная информация, дай полный исчерпывающий ответ. Если в контексте нет точной информации, скажи об этом, но попытайся дать полезные рекомендации.
            ВАЖНО: ОТВЕЧАЙ НА РУССКОМ ЯЗЫКЕ НЕЗАВИСИМО ОТ ЯЗЫКА ПРЕДОСТАВЛЕННОГО КОНТЕКСТА.""",
            'ukrainian': """Ти помічник з управління проектами. Структуруй відповідь із використанням HTML тегів (<div>, <section>, <h3>-<h6>, <p>, <span>, <ul>/<ol>, <li>, <blockquote>, <strong>). Ніколи НЕ починай відповідь із заголовка. Починай одразу зі змісту. Використовуй наданий контекст для точних відповідей. Якщо в контексті є релевантна інформація, надай повну вичерпну відповідь. Якщо в контексті немає точної інформації, скажи про це, але намагайся надати корисні рекомендації.
            ВАЖЛИВО: ВІДПОВІДАЙ УКРАЇНСЬКОЮ МОВОЮ НЕЗАЛЕЖНО ВІД МОВИ НАДАНОГО КОНТЕКСТУ."""
        }
        return prompts.get(language, prompts['english'])
    
    def _create_user_prompt(self, query, context, language):
        prompts = {
            'english': f"""Context information:
            {context}
            Question: {query}
            Respond in English. Provide a helpful answer in HTML format based on the context above.""",

            'russian': f"""Контекстная информация:
            {context}
            Вопрос: {query}
            Отвечай на русском языке. Дай полезный ответ в формате HTML на основе контекста выше.""",

            'ukrainian': f"""Контекстна інформація:
            {context}
            Питання: {query}
            Відповідай українською мовою. Надай корисну відповідь у форматі HTML на основі контексту вище."""
        }
        return prompts.get(language, prompts['english'])
    
    async def generate_answer_stream(self, query, search_results, history=None):
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
            stream = await self.client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=messages,
                temperature=0.5,
                max_tokens=1500,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"Sorry, I encountered an error: {str(e)}"

    async def normalize_query(self, original_query: str) -> str:
        language = await self._detect_language_async(original_query)
        normalization_prompt = self._create_normalization_prompt(language)
        
        full_prompt = f"{normalization_prompt}\n\nЗапрос: \"{original_query}\"\n\nНормализованный запрос:"
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": full_prompt}],
                temperature=0.1,
                max_tokens=200
            )
            
            normalized = response.choices[0].message.content.strip()
            return normalized if normalized else original_query
            
        except Exception as e:
            return original_query

    def _create_normalization_prompt(self, language):
        prompts = {
            'english': """Normalize this query to formal business style of project documentation.

    CRITICAL RULES:
    1. Keep the original language of the query (English)
    2. Correct spelling errors and typos
    3. Replace slang and colloquial expressions with standard project management terms
    4. Correct transliteration (e.g., "prajs" → "price")
    5. Do not add extra words or explanations - only the normalized query
    6. Do not change the meaning and essence of the original query""",

            'russian': """Нормализуй этот запрос к формальному деловому стилю проектной документации.

    КРИТИЧЕСКИ ВАЖНЫЕ ПРАВИЛА:
    1. Сохрани оригинальный язык запроса (русский)
    2. Исправь орфографические ошибки и опечатки
    3. Замени сленг и разговорные выражения на стандартные термины проектного менеджмента
    4. Исправляй транслитерацию (например, "прайс" → "цена")
    5. Не добавляй дополнительные слова или объяснения - только нормализованный запрос
    6. Не меняй смысл и суть исходного запроса""",

            'ukrainian': """Нормалізуй цей запит до формального ділового стилю проектної документації.

    КРИТИЧНО ВАЖЛИВІ ПРАВИЛА:
    1. Збережи оригінальну мову запиту (українську)
    2. Виправ орфографічні помилки та описки
    3. Заміни сленг та розмовні вирази на стандартні терміни проектного менеджменту
    4. Виправляй транслітерацію (наприклад, "прайс" → "ціна")
    5. Не додавай додаткові слова чи пояснення - тільки нормалізований запит
    6. Не змінюй сенс та суть початкового запиту"""
        }
        return prompts.get(language, prompts['english'])
        