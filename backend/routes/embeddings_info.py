from flask import Blueprint, jsonify
from services.embeddings import EmbeddingService
import time
import asyncio

embeddings_blueprint = Blueprint('embeddings', __name__)

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@embeddings_blueprint.route('/embeddings/model_info', methods=['GET'])
def get_model_details():
    embedding_service = EmbeddingService()
    model = embedding_service.model

    actual_model_name = getattr(model._modules['0'].auto_model.config, 'name_or_path', None)
    
    transformer_module = model._modules['0']
    auto_model = transformer_module.auto_model
    config = auto_model.config
    
    model_details = {
        'model_name': actual_model_name, 
        'embedding_dimensions': config.hidden_size,
        'max_sequence_length': transformer_module.max_seq_length,
        'vocab_size': config.vocab_size,
        'num_layers': config.num_hidden_layers,
        'num_attention_heads': config.num_attention_heads,
        'model_type': config.model_type,
        'tokenizer_type': model.tokenizer.__class__.__name__,
        'pooling_method': str(model._modules['1'])
    }

    sample_text = "This is a test sentence for tokenization."
    tokens = model.tokenizer.encode(sample_text)
    
    model_details['tokenization_test'] = {
        'sample_text': sample_text,
        'token_count': len(tokens),
        'estimated_chars_per_token': len(sample_text) / len(tokens)
    }
    
    return jsonify(model_details)

@embeddings_blueprint.route('/embeddings/documents_info', methods=['GET'])
def test_hybrid_embeddings():
    start_time = time.time()
    
    async def async_handler():
        from services.notion_client import NotionClient
        
        async with NotionClient() as notion_client:
            documents = await notion_client.get_all_documents_metadata()
            
            embedding_service = EmbeddingService()

            embeddings_data = embedding_service.generate_hybrid_embeddings(documents)

            title_embeddings = [e for e in embeddings_data if e['type'] == 'title']
            content_embeddings = [e for e in embeddings_data if e['type'] == 'content']
            
            execution_time = int(time.time() - start_time)
            
            return jsonify({
                'total_pages': len(documents),
                'title_embeddings': len(title_embeddings),
                'content_embeddings': len(content_embeddings),
                'total_embeddings': len(embeddings_data),
                'avg_chunks_per_page': len(content_embeddings) / len(documents) if documents else 0,
                'execution_time': execution_time
            })
    
    return run_async(async_handler())
