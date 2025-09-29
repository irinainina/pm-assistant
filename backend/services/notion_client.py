from notion_client import AsyncClient
from utils.config import Config
from typing import List, Dict, Any, Optional
import asyncio

class NotionClient:
    def __init__(self):
        self.async_client = AsyncClient(auth=Config.NOTION_API_KEY)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def get_all_documents_metadata(self) -> List[Dict[str, Any]]:
        pages = await self._get_all_pages_via_search_async()
        tasks = [self._process_single_page_async(page) for page in pages]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [result for result in results if result and not isinstance(result, Exception)]

    async def _get_all_pages_via_search_async(self) -> List[Dict[str, Any]]:
        pages = []
        has_more, cursor = True, None

        while has_more:
            params = {
                "filter": {"property": "object", "value": "page"},
                "page_size": 100
            }
            if cursor:
                params["start_cursor"] = cursor

            response = await self.async_client.search(**params)
            results = response.get("results", [])

            for page in results:
                if self._extract_title(page):
                    pages.append(page)

            has_more = response.get("has_more", False)
            cursor = response.get("next_cursor")

        return pages

    async def _process_single_page_async(self, page: Dict) -> Dict[str, Any]:
        try:
            page_id = page["id"]
            title = self._extract_title(page)
            if not title:
                return None

            content = await self.get_page_content_async(page_id)
            if not content:
                return None
            
            page_url = f"https://www.notion.so/{page_id.replace('-', '')}"

            return {
                "id": page_id,
                "url": page_url,
                "content": content,
                "properties": {
                    "title": title,
                    "post": page_id.replace('-', '')
                }
            }
        except Exception:
            return None

    async def get_page_content_async(self, page_id: str) -> str:
        try:
            blocks = await self._get_all_blocks_async(page_id)
            return self._extract_text_from_blocks(blocks)
        except Exception:
            return ""

    async def _get_all_blocks_async(self, page_id: str) -> List[Dict]:
        blocks = []
        has_more, cursor = True, None
        
        while has_more:
            params = {"block_id": page_id, "page_size": 100}
            if cursor:
                params["start_cursor"] = cursor
                
            response = await self.async_client.blocks.children.list(**params)
            blocks.extend(response.get("results", []))
            has_more = response.get("has_more", False)
            cursor = response.get("next_cursor")
            
        return blocks

    def _extract_title(self, page: Dict[str, Any]) -> str:
        properties = page.get("properties", {})
        if "title" in properties:
            title_prop = properties["title"].get("title", [])
            if title_prop:
                text = title_prop[0].get("plain_text", "").strip()
                if text and text.lower() != "page":
                    return text
        return None

    def _extract_text_from_blocks(self, blocks: List[Dict]) -> str:
        texts = []
        for block in blocks:
            block_type = block.get("type")
            if not block_type:
                continue
                
            block_content = block.get(block_type, {})
            rich_texts = block_content.get("rich_text", [])
            
            for rich_text in rich_texts:
                text = rich_text.get("plain_text", "").strip()
                if text:
                    texts.append(text)
                    
        return " ".join(texts)

    async def close(self):
        await self.async_client.aclose()

    async def get_last_edited_time(self) -> Optional[str]:
        try:
            response = await self.async_client.search(
                filter={"property": "object", "value": "page"},
                sort={"direction": "descending", "timestamp": "last_edited_time"},
                page_size=1
            )
            results = response.get("results", [])
            if not results:
                return None
            return results[0].get("last_edited_time")
        except Exception:
            return None

    async def close(self):
        await self.async_client.aclose()


# from notion_client import AsyncClient
# from utils.config import Config
# from typing import List, Dict, Any
# import asyncio
# import datetime

# class NotionClient:
#     def __init__(self):
#         self.async_client = AsyncClient(auth=Config.NOTION_API_KEY)

#     async def __aenter__(self):
#         return self

#     async def __aexit__(self, exc_type, exc_val, exc_tb):
#         await self.close()

#     async def get_all_documents_metadata(self) -> List[Dict[str, Any]]:
#         pages = await self._get_all_pages_via_search_async()
#         tasks = [self._process_single_page_async(page) for page in pages]
#         results = await asyncio.gather(*tasks, return_exceptions=True)
#         return [result for result in results if result and not isinstance(result, Exception)]

#     async def get_last_edited_time(self) -> str:
#         """Get only the latest edited time (optimized)"""
#         params = {
#             "filter": {"property": "object", "value": "page"},
#             "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}],
#             "page_size": 1
#         }
        
#         response = await self.async_client.search(**params)
#         results = response.get("results", [])
        
#         if results:
#             return results[0].get('last_edited_time')
#         return None

#     async def get_modified_pages_since(self, since_timestamp: float) -> List[Dict]:
#         """Get pages modified since timestamp using client-side filtering"""
#         all_pages = await self._get_all_pages_via_search_async()
        
#         if not since_timestamp:
#             return all_pages
        
#         modified_pages = []
#         for page in all_pages:
#             last_edited = page.get('last_edited_time')
#             if last_edited and self._extract_title(page):
#                 page_timestamp = self._parse_timestamp(last_edited)
#                 if page_timestamp > since_timestamp:
#                     modified_pages.append(page)
        
#         return modified_pages

#     async def _get_all_pages_via_search_async(self) -> List[Dict[str, Any]]:
#         pages = []
#         has_more, cursor = True, None

#         while has_more:
#             params = {
#                 "filter": {"property": "object", "value": "page"},
#                 "page_size": 100
#             }
#             if cursor:
#                 params["start_cursor"] = cursor

#             response = await self.async_client.search(**params)
#             results = response.get("results", [])

#             for page in results:
#                 if self._extract_title(page):
#                     pages.append(page)

#             has_more = response.get("has_more", False)
#             cursor = response.get("next_cursor")

#         return pages

#     async def _process_single_page_async(self, page: Dict) -> Dict[str, Any]:
#         try:
#             page_id = page["id"]
#             title = self._extract_title(page)
#             if not title:
#                 return None

#             content = await self.get_page_content_async(page_id)
#             if not content:
#                 return None
            
#             page_url = f"https://www.notion.so/{page_id.replace('-', '')}"

#             return {
#                 "id": page_id,
#                 "url": page_url,
#                 "content": content,
#                 "properties": {
#                     "title": title,
#                     "post": page_id.replace('-', '')
#                 },
#                 "last_edited_time": page.get("last_edited_time")
#             }
#         except Exception:
#             return None

#     async def get_page_content_async(self, page_id: str) -> str:
#         try:
#             blocks = await self._get_all_blocks_async(page_id)
#             return self._extract_text_from_blocks(blocks)
#         except Exception:
#             return ""

#     async def _get_all_blocks_async(self, page_id: str) -> List[Dict]:
#         blocks = []
#         has_more, cursor = True, None
        
#         while has_more:
#             params = {"block_id": page_id, "page_size": 100}
#             if cursor:
#                 params["start_cursor"] = cursor
                
#             response = await self.async_client.blocks.children.list(**params)
#             blocks.extend(response.get("results", []))
#             has_more = response.get("has_more", False)
#             cursor = response.get("next_cursor")
            
#         return blocks

#     def _extract_title(self, page: Dict[str, Any]) -> str:
#         properties = page.get("properties", {})
#         if "title" in properties:
#             title_prop = properties["title"].get("title", [])
#             if title_prop:
#                 text = title_prop[0].get("plain_text", "").strip()
#                 if text and text.lower() != "page":
#                     return text
#         return None

#     def _extract_text_from_blocks(self, blocks: List[Dict]) -> str:
#         texts = []
#         for block in blocks:
#             block_type = block.get("type")
#             if not block_type:
#                 continue
                
#             block_content = block.get(block_type, {})
#             rich_texts = block_content.get("rich_text", [])
            
#             for rich_text in rich_texts:
#                 text = rich_text.get("plain_text", "").strip()
#                 if text:
#                     texts.append(text)
                    
#         return " ".join(texts)

#     def _parse_timestamp(self, timestamp_str: str) -> float:
#         """Convert ISO timestamp to UNIX timestamp"""
#         if not timestamp_str:
#             return 0
#         try:
#             dt = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
#             return dt.timestamp()
#         except ValueError:
#             return 0

#     async def close(self):
#         await self.async_client.aclose()
        