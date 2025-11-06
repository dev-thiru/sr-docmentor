from dataclasses import dataclass

import asyncpg
import pydantic_core
from pydantic_ai import Agent, RunContext

from src.models import model, embedding_model


@dataclass
class Deps:
    conn: asyncpg.Connection


agent = Agent(model)


@agent.tool
async def retrieve(context: RunContext[Deps], search_query: str) -> str:
    try:
        embeddings_list = list(embedding_model.embed([search_query]))
        embedding = embeddings_list[0]

        embedding_json = pydantic_core.to_json(embedding.tolist()).decode()

        rows = await context.deps.conn.fetch(
            'SELECT file_path, title, content FROM doc_sections ORDER BY embedding <-> $1 LIMIT 8',
            embedding_json,
        )

        return '\n\n'.join(
            f'# {row["title"]}\nFile: {row["file_path"]}\n\n{row["content"]}\n'
            for row in rows
        )
    except Exception as e:
        print(f"Error in retrieve function: {e}")
        return f"Sorry, I encountered an error while searching: {str(e)}"
