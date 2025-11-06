import os

import asyncpg


async def database_connect():
    server_dsn = os.getenv("DATABASE_DSN")
    pool = await asyncpg.connect(
        server_dsn,
        command_timeout=60,
        server_settings={
            'application_name': 'rag_app',
        }
    )
    return pool


async def initialize_database_schema(conn: asyncpg.Connection):
    await conn.execute(DB_SCHEMA)


DB_SCHEMA = """
            CREATE
            EXTENSION IF NOT EXISTS vector;

            CREATE TABLE IF NOT EXISTS doc_sections
            (
                id
                serial
                PRIMARY
                KEY,
                file_path
                text
                NOT
                NULL,
                title
                text
                NOT
                NULL,
                content
                text
                NOT
                NULL,
                embedding
                vector
            (
                1024
            ) NOT NULL
                );

            CREATE INDEX IF NOT EXISTS idx_doc_sections_embedding ON doc_sections USING hnsw (embedding vector_l2_ops); \
            """
