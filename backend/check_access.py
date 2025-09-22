# backend/debug_pages.py
import sys
import os
import time
from notion_client import Client
from utils.config import Config

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class NotionDebugger:
    def __init__(self):
        self.client = Client(auth=Config.NOTION_API_KEY)
        self.root_page_id = Config.NOTION_ROOT_PAGE_ID
    
    def debug_root_page(self):
        """Детальная информация о корневой папке"""
        print("=== DEBUG ROOT PAGE ===")
        
        try:
            # Получаем информацию о корневой странице
            root_page = self.client.pages.retrieve(page_id=self.root_page_id)
            print(f"Root page title: {self._safe_string(self._extract_title(root_page))}")
            print(f"Root page ID: {root_page['id']}")
            print(f"Created time: {root_page['created_time']}")
            print(f"Last edited: {root_page['last_edited_time']}")
            print(f"URL: https://www.notion.so/{root_page['id'].replace('-', '')}")
            print()
            
            # Смотрим все блоки в корневой папке
            self._debug_blocks(self.root_page_id, "Root page")
            
        except Exception as e:
            print(f"Error getting root page: {e}")
    
    def _debug_blocks(self, page_id: str, context: str):
        """Детально анализирует все блоки на странице"""
        print(f"=== BLOCKS IN {context} ===")
        
        try:
            has_more = True
            next_cursor = None
            block_count = 0
            page_count = 0
            database_count = 0
            other_count = 0
            
            while has_more:
                response = self.client.blocks.children.list(
                    block_id=page_id,
                    page_size=100,
                    start_cursor=next_cursor
                )
                
                blocks = response.get('results', [])
                has_more = response.get('has_more', False)
                next_cursor = response.get('next_cursor')
                
                for block in blocks:
                    block_count += 1
                    block_type = block.get('type')
                    
                    print(f"{block_count}. {block_type.upper()}: {block['id']}")
                    
                    if block_type == 'child_page':
                        page_count += 1
                        title = self._safe_string(self._extract_block_text(block))
                        print(f"   - Page: {title}")
                    elif block_type == 'child_database':
                        database_count += 1
                        title = self._safe_string(self._extract_block_text(block))
                        print(f"   - Database: {title}")
                    else:
                        other_count += 1
                        content = self._safe_string(self._extract_block_text(block))
                        if len(content) > 50:
                            content = content[:50] + "..."
                        print(f"   - Content: {content}")
                
                print(f"--- {block_count} blocks processed ---")
            
            print(f"\nTOTAL in {context}:")
            print(f"All blocks: {block_count}")
            print(f"Child pages: {page_count}")
            print(f"Databases: {database_count}")
            print(f"Other blocks: {other_count}")
            
            # Если нашли страницы, проверяем их рекурсивно
            if page_count > 0:
                print(f"\n=== RECURSIVE CHECK OF PAGES ===")
                for block in blocks:
                    if block.get('type') == 'child_page':
                        page_id = block['id']
                        title = self._safe_string(self._extract_block_text(block))
                        print(f"Checking page: {title}")
                        self._debug_blocks(page_id, f"Page {page_id}")
            
        except Exception as e:
            print(f"Error debugging blocks: {e}")
    
    def _extract_title(self, page_data):
        """Извлекает заголовок страницы"""
        try:
            properties = page_data.get('properties', {})
            for prop_value in properties.values():
                if prop_value.get('type') == 'title':
                    title_parts = prop_value.get('title', [])
                    return ''.join([part.get('plain_text', '') for part in title_parts])
            return "No title"
        except:
            return "Error extracting title"
    
    def _extract_block_text(self, block):
        """Извлекает текст из блока"""
        try:
            block_type = block.get('type')
            block_content = block.get(block_type, {})
            
            if 'rich_text' in block_content:
                texts = [rt.get('plain_text', '') for rt in block_content['rich_text']]
                return ''.join(texts)
            
            return "No text content"
        except:
            return "Error extracting text"
    
    def _safe_string(self, text):
        """Безопасно обрабатывает строки для вывода в Windows"""
        if isinstance(text, str):
            # Заменяем проблемные символы
            text = text.encode('ascii', 'ignore').decode('ascii')
            return text
        return str(text)

def main():
    print("Starting Notion debug analysis...")
    print("=" * 60)
    
    debugger = NotionDebugger()
    debugger.debug_root_page()

if __name__ == "__main__":
    main()