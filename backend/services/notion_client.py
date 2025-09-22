from notion_client import Client
from utils.config import Config
from typing import List, Dict, Any

class NotionClient:
    def __init__(self):
        self.client = Client(auth=Config.NOTION_API_KEY)
        self.root_page_id = Config.NOTION_ROOT_PAGE_ID
    
    def get_all_documents_metadata(self):
        documents_metadata = []
        
        all_page_ids = self._get_top_level_page_ids(self.root_page_id)
        
        for page_id in all_page_ids:
            try:
                metadata = self.get_page_metadata(page_id)
                if metadata:
                    documents_metadata.append(metadata)
            except Exception:
                continue
        
        return documents_metadata
    
    def _get_top_level_page_ids(self, page_id: str) -> List[str]:        
        page_ids = []
        next_cursor = None

        while True:
            try:
                params = {"block_id": page_id, "page_size": 100}
                if next_cursor:
                    params["start_cursor"] = next_cursor
                
                response = self.client.blocks.children.list(**params)
                blocks = response.get('results', [])
                
                for block in blocks:
                    if block.get('type') == 'child_page':
                        page_ids.append(block.get('id'))

                next_cursor = response.get('next_cursor')
                if not next_cursor or not response.get('has_more'):
                    break
                    
            except Exception:
                break
        
        return page_ids
    
    def get_page_metadata(self, page_id: str) -> Dict[str, Any]:
        try:
            page_data = self.client.pages.retrieve(page_id=page_id)
            properties = page_data.get('properties', {})          
            title = "Untitled"
            for prop_value in properties.values():
                if prop_value.get('type') == 'title':
                    title = ''.join([text.get('plain_text', '') for text in prop_value.get('title', [])])
                    break
            
            content = self.get_page_content(page_id)
            page_url = f"https://www.notion.so/{page_id.replace('-', '')}"
            
            return {
                'id': page_id,
                'url': page_url,
                'content': content,
                'properties': {
                    'title': title,
                    'post': page_id
                },
                'last_edited_time': page_data.get('last_edited_time')
            }
            
        except Exception:
            return None
    
    def get_page_content(self, page_id: str) -> str:
        try:
            blocks = self.client.blocks.children.list(block_id=page_id)
            content = self._extract_text_only(blocks.get('results', []))
            return self._normalize_text(content)
        except Exception:
            return ""
    
    def _extract_text_only(self, blocks: List[Dict]) -> List[str]:
        content_lines = []
        
        for block in blocks:
            try:
                block_type = block.get('type')
                block_content = block.get(block_type, {})
                
                if 'rich_text' in block_content:
                    for rich_text in block_content['rich_text']:
                        text = rich_text.get('plain_text', '')
                        if text:
                            content_lines.append(text)
            except Exception:
                continue
        
        return content_lines
    
    def _normalize_text(self, content_lines: List[str]) -> str:
        content = " ".join(content_lines)
        content = " ".join(content.split())
        return content

    def get_last_edited_time(self) -> str:
        all_page_ids = self._get_top_level_page_ids(self.root_page_id)
        
        if not all_page_ids:
            return None
        
        latest_time = None
        
        for page_id in all_page_ids:
            try:
                page_data = self.client.pages.retrieve(page_id=page_id)
                page_time = page_data.get('last_edited_time')
                
                if not latest_time or page_time > latest_time:
                    latest_time = page_time
            except Exception:
                continue
        
        return latest_time



# from notion_client import Client
# from utils.config import Config
# import time

# class NotionClient:
#     def __init__(self):
#         self.client = Client(auth=Config.NOTION_API_KEY)
#         self.database_id = Config.NOTION_DATABASE_ID
    
#     def get_all_documents_metadata(self):
#         documents_metadata = []
#         next_cursor = None
#         has_more = True
        
#         while has_more:
#             try:
#                 response = self.query_database(page_size=100, start_cursor=next_cursor)
#                 pages = response.get('results', [])
#                 has_more = response.get('has_more', False)
#                 next_cursor = response.get('next_cursor')
                
#                 for page in pages:
#                     try:
#                         properties = page.get('properties', {})
                        
#                         post_id = self._extract_property(properties, 'post')            
#                         content_source_id = post_id
#                         content = self.get_page_content(content_source_id)
#                         page_url = f"https://www.notion.so/{post_id}"
                                    
#                         metadata = {
#                             'id': page.get('id'),
#                             'url': page_url,
#                             'content': content,
#                             'properties': {
#                               'title': self._extract_property(properties, 'title'),
#                               'post': post_id
#                           }
#                         }
                        
#                         documents_metadata.append(metadata)
                        
#                     except Exception as e:
#                         continue
                        
#             except Exception as e:
#                 if self._is_rate_limit_error(e):
#                     time.sleep(1)
#                     continue
#                 raise
        
#         return documents_metadata
    
#     def _extract_property(self, properties, prop_name):        
#         if prop_name not in properties:
#             return None
        
#         prop_value = properties[prop_name]
#         prop_type = prop_value.get('type')
        
#         if prop_type == 'title':
#             return ''.join([text.get('plain_text', '') for text in prop_value.get('title', [])])
#         elif prop_type == 'rich_text':
#             return ''.join([text.get('plain_text', '') for text in prop_value.get('rich_text', [])])        
#         else:
#             return None
    
#     def query_database(self, page_size=100, start_cursor=None):
#         params = {
#             'database_id': self.database_id,
#             'page_size': page_size
#         }
        
#         if start_cursor:
#             params['start_cursor'] = start_cursor
        
#         try:
#             response = self.client.databases.query(**params)
#             return response
#         except Exception as e:
#             if self._is_rate_limit_error(e):
#                 time.sleep(1)
#                 return self.query_database(page_size, start_cursor)  # Retry
#             raise
    
#     def get_page_content(self, page_id):
#         for attempt in range(3):
#             try:
#                 blocks = self.client.blocks.children.list(block_id=page_id)
#                 content = self._parse_blocks(blocks.get('results', []))
#                 return self._normalize_text(content)
#             except Exception as e:
#                 if self._is_rate_limit_error(e) and attempt < 2:
#                     time.sleep(1)
#                     continue
#                 return ""
    
#     def _parse_blocks(self, blocks, level=0):
#         content = []
        
#         for block in blocks:
#             try:
#                 block_type = block.get('type')
#                 block_content = block.get(block_type, {})            
                
#                 text = ""
#                 if 'rich_text' in block_content:
#                     for rich_text in block_content['rich_text']:
#                         text += rich_text.get('plain_text', '')            
                
#                 indent = "  " * level
#                 content.append(f"{indent}{text}")            
                
#                 if block.get('has_children', False):
#                     child_blocks = self.client.blocks.children.list(block_id=block['id'])
#                     content.extend(self._parse_blocks(child_blocks.get('results', []), level + 1))
                    
#             except Exception:
#                 continue
        
#         return content
    
#     def _normalize_text(self, content_lines):
#         content = "\n".join(content_lines)
#         content = " ".join(content.split())
#         return content

#     def get_last_edited_time(self):
#         try:
#             response = self.client.databases.query(
#                 database_id=self.database_id,
#                 page_size=1,
#                 sorts=[{
#                     "timestamp": "last_edited_time",
#                     "direction": "descending"
#                 }]
#             )
            
#             if response.get('results'):
#                 page = response['results'][0]
#                 last_edited = page.get('last_edited_time')
#                 return last_edited
                
#         except Exception as e:
#             if self._is_rate_limit_error(e):
#                 time.sleep(1)
#                 return self.get_last_edited_time()
        
#         return None

#     def _is_rate_limit_error(self, error):
#         return hasattr(error, 'status') and getattr(error, 'status') == 429
