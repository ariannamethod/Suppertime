import os
import glob
import json
import hashlib
from pinecone import Pinecone, ServerlessSpec
import openai
from tenacity import retry, stop_after_attempt, wait_fixed

VECTOR_META_PATH = "vector_store.meta.json"
EMBED_DIM = 1536

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-west-2")  # или твой регион
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")          # или твой cloud

pc = Pinecone(api_key=PINECONE_API_KEY)

# Проверяем, есть ли индекс. Если нет — создаём.
if PINECONE_INDEX not in [x["name"] for x in pc.list_indexes()]:
    pc.create_index(
        name=PINECONE_INDEX,
        dimension=EMBED_DIM,
        metric="cosine",
        spec=ServerlessSpec(
            cloud=PINECONE_CLOUD,
            region=PINECONE_REGION
        )
    )

index = pc.Index(PINECONE_INDEX)
