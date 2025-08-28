from notion_client import Client
from utils.config import Config

class NotionClient:
    def __init__(self):
        self.client = Client(auth=Config.NOTION_API_KEY)
        self.database_id = Config.NOTION_DATABASE_ID
    
    def get_all_documents_metadata(self):
        pages = self.query_database()
        documents_metadata = []
        
        for page in pages:
            properties = page.get('properties', {})
            
            post_id = self._extract_property(properties, 'post')            
            content_source_id = post_id
            content = self.get_page_content(content_source_id)
            page_url = f"https://www.notion.so/{post_id}"
                        
            metadata = {
                'id': page.get('id'),
                'url': page_url,
                'content': content,
                'properties': {
                  'title': self._extract_property(properties, 'title'),
                  'post': post_id
              }
            }
            
            documents_metadata.append(metadata)
        
        return documents_metadata
    
    def _extract_property(self, properties, prop_name):        
        if prop_name not in properties:
            return None
        
        prop_value = properties[prop_name]
        prop_type = prop_value.get('type')
        
        if prop_type == 'title':
            return ''.join([text.get('plain_text', '') for text in prop_value.get('title', [])])
        elif prop_type == 'rich_text':
            return ''.join([text.get('plain_text', '') for text in prop_value.get('rich_text', [])])        
        else:
            return None
    
    def query_database(self, page_size=100):
        response = self.client.databases.query(
            database_id=self.database_id,
            page_size=page_size
        )
        return response.get('results', [])
    
    def get_page_content(self, page_id):
        blocks = self.client.blocks.children.list(block_id=page_id)
        content = self._parse_blocks(blocks.get('results', []))
        return self._normalize_text(content)
    
    def _parse_blocks(self, blocks, level=0):
        content = []
        
        for block in blocks:
            block_type = block.get('type')
            block_content = block.get(block_type, {})            
            
            text = ""
            if 'rich_text' in block_content:
                for rich_text in block_content['rich_text']:
                    text += rich_text.get('plain_text', '')            
            
            indent = "  " * level
            content.append(f"{indent}{text}")            
            
            if block.get('has_children', False):
                child_blocks = self.client.blocks.children.list(block_id=block['id'])
                content.extend(self._parse_blocks(child_blocks.get('results', []), level + 1))
        
        return content
    
    def _normalize_text(self, content_lines):
        content = "\n".join(content_lines)
        content = " ".join(content.split())
        return content
