from pathlib import Path

import asyncpg
import pydantic_core

from src.db import initialize_database_schema
from src.models import embedding_model
from src.rag import read_pdf_file, split_document_into_sections


async def build_search_db(conn: asyncpg.Connection):
    documents_dir = Path("documents")
    if not documents_dir.exists():
        print(f"Documents directory '{documents_dir}' does not exist!")
        return

    doc_files = []
    for ext in ['*.txt', '*.md', '*.py', '*.json', '*.pdf']:
        doc_files.extend(documents_dir.glob(ext))

    if not doc_files:
        print(f"No supported files found in '{documents_dir}' directory!")
        return

    print(f"Found {len(doc_files)} files to process")

    await initialize_database_schema(conn)

    # Process files sequentially to avoid conflicts
    for file_path in doc_files:
        await process_document_file(conn, file_path)


async def process_document_file(conn: asyncpg.Connection, file_path: Path) -> None:
    file_path_str = str(file_path)

    try:
        exists = await conn.fetchval(
            'SELECT 1 FROM doc_sections WHERE file_path = $1 LIMIT 1',
            file_path_str
        )
        if exists:
            print(f"Skipping {file_path} - already processed")
            return

        if file_path.suffix.lower() == '.pdf':
            content = read_pdf_file(file_path)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

        sections = split_document_into_sections(content, file_path.stem)

        print(f"Processing {len(sections)} sections from {file_path}")

        for i, section in enumerate(sections):
            section_title = f"{file_path.stem} - Section {i + 1}"

            embeddings_list = list(embedding_model.embed([section]))
            embedding = embeddings_list[0]

            embedding_json = pydantic_core.to_json(embedding.tolist()).decode()
            await conn.execute(
                'INSERT INTO doc_sections (file_path, title, content, embedding) VALUES ($1, $2, $3, $4)',
                file_path_str,
                section_title,
                section,
                embedding_json,
            )

        print(f"Successfully processed {file_path}")

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
