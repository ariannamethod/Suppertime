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
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-west-2")
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")

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

def file_hash(fname):
    with open(fname, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def scan_files(path="config/*.md"):
    files = {}
    for fname in glob.glob(path):
        files[fname] = file_hash(fname)
    return files

def load_vector_meta():
    if os.path.isfile(VECTOR_META_PATH):
        with open(VECTOR_META_PATH, "r") as f:
            return json.load(f)
    return {}

def save_vector_meta(meta):
    with open(VECTOR_META_PATH, "w") as f:
        json.dump(meta, f)

@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def safe_embed(text, openai_api_key):
    return get_embedding(text, openai_api_key)

def get_embedding(text, openai_api_key):
    openai.api_key = openai_api_key
    res = openai.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    return res.data[0].embedding

def chunk_text(text, chunk_size=900, overlap=120):
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

def vectorize_all_files(openai_api_key, force=False, on_message=None):
    current = scan_files()
    previous = load_vector_meta()
    changed = [f for f in current if (force or current[f] != previous.get(f))]
    new = [f for f in current if f not in previous]
    removed = [f for f in previous if f not in current]

    upserted_ids = []
    for fname in current:
        if fname not in changed and fname not in new and not force:
            continue
        with open(fname, "r", encoding="utf-8") as f:
            text = f.read()
        chunks = chunk_text(text)
        for idx, chunk in enumerate(chunks):
            meta_id = f"{fname}:{idx}"
            try:
                emb = safe_embed(chunk, openai_api_key)
                index.upsert(
                    vectors=[(meta_id, emb, {"file": fname, "chunk": idx, "hash": current[fname]})]
                )
                upserted_ids.append(meta_id)
            except Exception as e:
                if on_message:
                    on_message(f"Pinecone error: {e}")
                continue

    deleted_ids = []
    for fname in removed:
        for idx in range(50):  # грубая оценка макс. чанков на файл
            meta_id = f"{fname}:{idx}"
            try:
                index.delete(ids=[meta_id])
                deleted_ids.append(meta_id)
            except Exception:
                pass

    save_vector_meta(current)
    if on_message:
        on_message(
            f"Vectorization complete. New/changed: {', '.join(changed + new) if changed or new else '-'}; deleted: {', '.join(removed) if removed else '-'}"
        )
    return {"upserted": upserted_ids, "deleted": deleted_ids}

def semantic_search(query, openai_api_key, top_k=5):
    emb = safe_embed(query, openai_api_key)
    res = index.query(vector=emb, top_k=top_k, include_metadata=True)
    # Новый pinecone может возвращать matches как list или через res['matches']
    matches = res.get("matches", []) if isinstance(res, dict) else getattr(res, "matches", [])
    chunks = []
    for match in matches:
        metadata = match.get("metadata", {})
        fname = metadata.get("file")
        chunk_idx = metadata.get("chunk")
        try:
            with open(fname, "r", encoding="utf-8") as f:
                all_chunks = chunk_text(f.read())
                chunk_text_ = all_chunks[chunk_idx] if chunk_idx is not None and chunk_idx < len(all_chunks) else ""
        except Exception:
            chunk_text_ = ""
        if chunk_text_:
            chunks.append(chunk_text_)
    return chunks
