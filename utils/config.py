import os
import glob
import json
import hashlib
import threading
import time

from utils.whatdotheythinkiam import run_reflection, schedule_weekly_reflection

from utils.vector_store import vectorize_file, semantic_search_in_file

SUPPERTIME_DATA_PATH = os.getenv("SUPPERTIME_DATA_PATH", "./data")
LIT_DIR = os.path.join(SUPPERTIME_DATA_PATH, "lit")
SNAPSHOT_PATH = os.path.join(SUPPERTIME_DATA_PATH, "vectorized_snapshot.json")


def _load_snapshot():
    try:
        with open(SNAPSHOT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_snapshot(snapshot):
    os.makedirs(os.path.dirname(SNAPSHOT_PATH), exist_ok=True)
    with open(SNAPSHOT_PATH, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)


def _file_hash(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return hashlib.md5(f.read().encode("utf-8")).hexdigest()
    except Exception:
        return ""


def vectorize_lit_files():
    """Vectorize new or updated literary files."""
    lit_files = glob.glob(os.path.join(LIT_DIR, "*.txt")) + glob.glob(os.path.join(LIT_DIR, "*.md"))
    if not lit_files:
        return "No literary files found in the lit directory."

    snapshot = _load_snapshot()
    changed = []
    for path in lit_files:
        h = _file_hash(path)
        if not h:
            continue
        if snapshot.get(path) != h:
            try:
                vectorize_file(path, os.getenv("OPENAI_API_KEY"))
                snapshot[path] = h
                changed.append(path)
            except Exception as e:
                print(f"[SUPPERTIME][ERROR] Failed to vectorize {path}: {e}")
    if changed:
        _save_snapshot(snapshot)
        return f"Indexed {len(changed)} files."
    return "No new literary files to index."


def get_vectorized_files():
    """Return list of vectorized literary files."""
    snapshot = _load_snapshot()
    return list(snapshot.keys())


def search_lit_files(query):
    """Search vectorized literary files for a query."""
    lit_files = get_vectorized_files()
    if not lit_files:
        return "No literary files have been indexed yet."

    results = []
    for file_path in lit_files:
        try:
            chunks = semantic_search_in_file(file_path, query, os.getenv("OPENAI_API_KEY"), top_k=2)
            if chunks:
                file_name = os.path.basename(file_path)
                results.append(f"From {file_name}:\n\n" + "\n\n---\n\n".join(chunks))
        except Exception as e:
            print(f"[SUPPERTIME][ERROR] Failed to search in {file_path}: {e}")

    if results:
        return "\n\n==========\n\n".join(results)
    return "No relevant information found in the literary files."


def explore_lit_directory():
    """Return information about literary files and their status."""
    lit_files = glob.glob(os.path.join(LIT_DIR, "*.txt")) + glob.glob(os.path.join(LIT_DIR, "*.md"))
    if not lit_files:
        return "No literary files found in the lit directory."

    snapshot = _load_snapshot()
    report = [f"Found {len(lit_files)} literary files:"]
    for path in lit_files:
        file_name = os.path.basename(path)
        status = "Indexed" if path in snapshot else "Not indexed"
        try:
            size_kb = os.path.getsize(path) / 1024
            with open(path, "r", encoding="utf-8") as f:
                preview = "".join(f.readlines()[:3]).strip()
                if len(preview) > 100:
                    preview = preview[:100] + "..."
            report.append(f"\n**{file_name}** ({size_kb:.1f} KB) - {status}\nPreview: {preview}")
        except Exception:
            report.append(f"\n**{file_name}** - {status} (Error reading file)")
    return "\n".join(report)


def schedule_lit_check(interval_hours=72):
    """Periodically check the lit folder for new files."""
    def _loop():
        while True:
            vectorize_lit_files()
            time.sleep(interval_hours * 3600)

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
    return thread


def schedule_reflection(initial=True, interval_hours=168):
    """Schedule weekly self-reflection based on README and resonance."""
    if initial:
        run_reflection()
    return schedule_weekly_reflection(interval_hours)
