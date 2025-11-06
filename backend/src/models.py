import os

from fastembed import TextEmbedding
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

print("Loading embedding model")
embedding_model = TextEmbedding(
    model_name="BAAI/bge-large-en-v1.5",
    cache_dir="models"
)

model = OpenAIChatModel(
    'llama3.1:8b-instruct-q5_K_M',
    provider=OpenAIProvider(
        base_url=os.getenv('OLLAMA_URL'),
        api_key='ollama',
    ),
)
