import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from services.notion_client import NotionClient
from services.chroma_client import ChromaClient

def prepare_database():
    print("Preparing database...")
    
    notion = NotionClient()
    chroma = ChromaClient()
    
    # Очищаем старые данные
    chroma.clear_collection()
    
    # Загружаем документы из Notion
    documents = notion.get_all_documents_metadata()
    print(f"Loaded {len(documents)} documents")
    
    # Сохраняем в ChromaDB
    chunks_count = chroma.add_documents(documents)
    print(f"Saved {chunks_count} chunks to database")
    
    print("Database ready! Now deploy to production.")

if __name__ == "__main__":
    prepare_database()
    