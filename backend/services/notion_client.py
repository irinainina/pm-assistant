from notion_client import Client
from utils.config import Config

class NotionClient:
    def __init__(self):
        self.client = Client(auth=Config.NOTION_API_KEY)
        self.database_id = Config.NOTION_DATABASE_ID
    
    def test_connection(self):
        response = self.client.databases.retrieve(database_id=self.database_id)
        return True
    
    def get_database_properties(self):
        database = self.client.databases.retrieve(database_id=self.database_id)
        return database.get('properties', {})
    
    def query_database(self, page_size=100):
        response = self.client.databases.query(
            database_id=self.database_id,
            page_size=page_size
        )
        return response.get('results', [])
    
    def get_page_content(self, page_id):
        blocks = self.client.blocks.children.list(block_id=page_id)
        return self._extract_text_from_blocks(blocks.get('results', []))
    
    def _extract_text_from_blocks(self, blocks):
        text_content = []
        
        for block in blocks:
            block_type = block.get('type')
            content = block.get(block_type, {})
            
            if 'rich_text' in content:
                for rich_text in content['rich_text']:
                    text_content.append(rich_text.get('plain_text', ''))
            
            if block.get('has_children', False):
                child_blocks = self.client.blocks.children.list(block_id=block['id'])
                text_content.extend(self._extract_text_from_blocks(child_blocks.get('results', [])))
        
        return "\n".join(text_content)
    
    def get_all_documents_metadata(self):
        pages = self.query_database()
        documents_metadata = []
        
        for page in pages:
            metadata = {
                'id': page.get('id'),
                'url': page.get('url'),
                'properties': {}
            }
            
            properties = page.get('properties', {})
            for prop_name, prop_value in properties.items():
                prop_type = prop_value.get('type')
                
                if prop_type == 'title':
                    metadata['properties'][prop_name] = ''.join([
                        text.get('plain_text', '') 
                        for text in prop_value.get('title', [])
                    ])
                elif prop_type == 'rich_text':
                    metadata['properties'][prop_name] = ''.join([
                        text.get('plain_text', '') 
                        for text in prop_value.get('rich_text', [])
                    ])
            
            documents_metadata.append(metadata)
        
        return documents_metadata
    