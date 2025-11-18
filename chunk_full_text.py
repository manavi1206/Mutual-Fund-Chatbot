"""
Chunk full text from data_processed/ and add to index
This enables answering ANY question about funds, not just the 7 specific fields
"""
import json
import csv
import re
from pathlib import Path
from typing import List, Dict

# Paths
DATA_PROCESSED_DIR = Path("data_processed")
CHUNKS_CLEAN_DIR = Path("chunks_clean")
SOURCES_CSV = Path("sources.csv")
CHUNK_SIZE = 600
OVERLAP = 100

def load_sources() -> Dict[str, Dict]:
    """Load sources.csv"""
    sources = {}
    with open(SOURCES_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sources[row["source_id"]] = {
                "source_url": row["source_url"],
                "source_type": row["source_type"],
                "scheme_tag": row["scheme_tag"],
                "authority": row.get("authority", ""),
                "last_fetched_date": row.get("last_fetched_date", ""),
            }
    return sources

# Removed clean_text function - doing it inline for speed

def chunk_text(text: str, source_id: str, source_meta: Dict, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP, max_chunks: int = 200) -> List[Dict]:
    """Chunk text into overlapping segments (optimized)"""
    chunks = []
    
    # Clean text first (faster - just normalize whitespace)
    text = re.sub(r"\s+", " ", text).strip()
    
    if len(text) < chunk_size:
        # Single chunk for short text
        chunk = {
            "id": f"{source_id}::fulltext::0",
            "source_id": source_id,
            "source_url": source_meta["source_url"],
            "source_type": source_meta["source_type"],
            "scheme_tag": source_meta["scheme_tag"],
            "chunk_index": 0,
            "text": text[:1500],  # Max 1500 chars
            "char_count": len(text),
            "token_estimate": len(text) // 4,
            "page_no": None,
            "last_fetched_date": source_meta["last_fetched_date"],
            "confidence": 0.85,
            "notes": "full_text_chunk",
            "field": None
        }
        chunks.append(chunk)
        return chunks
    
    # For very large files, limit chunks to avoid slowdown
    if len(text) > chunk_size * max_chunks:
        # Take first N chunks worth of text
        text = text[:chunk_size * max_chunks]
    
    # Fast chunking without sentence boundary detection (for speed)
    start = 0
    chunk_idx = 0
    step = chunk_size - overlap
    
    while start < len(text) and chunk_idx < max_chunks:
        end = min(start + chunk_size, len(text))
        chunk_text_segment = text[start:end].strip()
        
        if len(chunk_text_segment) > 100:
            chunk = {
                "id": f"{source_id}::fulltext::{chunk_idx}",
                "source_id": source_id,
                "source_url": source_meta["source_url"],
                "source_type": source_meta["source_type"],
                "scheme_tag": source_meta["scheme_tag"],
                "chunk_index": chunk_idx,
                "text": chunk_text_segment[:1500],  # Truncate if needed
                "char_count": len(chunk_text_segment),
                "token_estimate": len(chunk_text_segment) // 4,
                "page_no": None,
                "last_fetched_date": source_meta["last_fetched_date"],
                "confidence": 0.85,
                "notes": "full_text_chunk",
                "field": None
            }
            chunks.append(chunk)
            chunk_idx += 1
        
        start += step
    
    return chunks

def main():
    """Chunk all full text files and add to chunks_clean"""
    print("Chunking full text from data_processed/ files...")
    print("=" * 70)
    
    sources = load_sources()
    
    # Load existing clean chunks (fact-focused)
    existing_chunks = []
    chunks_file = CHUNKS_CLEAN_DIR / "chunks_clean.jsonl"
    if chunks_file.exists():
        with open(chunks_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    existing_chunks.append(json.loads(line))
        print(f"Loaded {len(existing_chunks)} existing fact-focused chunks")
    
    # Process all text files
    all_chunks = existing_chunks.copy()
    total_new_chunks = 0
    
    txt_files = sorted(DATA_PROCESSED_DIR.glob("*.txt"))
    total_files = len(txt_files)
    
    for idx, txt_file in enumerate(txt_files, 1):
        source_id = txt_file.stem
        if source_id not in sources:
            continue
        
        source_meta = sources[source_id]
        
        try:
            # Show progress
            print(f"[{idx}/{total_files}] Processing {source_id}...", end=" ", flush=True)
            
            with open(txt_file, "r", encoding="utf-8") as f:
                text = f.read()
            
            if len(text.strip()) < 200:
                print("⊘ Too short, skipping")
                continue
            
            # Chunk the text (limit to 200 chunks per file for speed)
            chunks = chunk_text(text, source_id, source_meta, max_chunks=200)
            all_chunks.extend(chunks)
            total_new_chunks += len(chunks)
            
            print(f"✓ {len(chunks)} chunks ({len(text)//1000}K chars)")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            continue
    
    # Write all chunks (existing + new)
    CHUNKS_CLEAN_DIR.mkdir(exist_ok=True)
    with open(chunks_file, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    
    print("=" * 70)
    print(f"✓ Complete!")
    print(f"  - Existing fact-focused chunks: {len(existing_chunks)}")
    print(f"  - New full-text chunks: {total_new_chunks}")
    print(f"  - Total chunks: {len(all_chunks)}")
    print(f"\nNext step: Run 'python rebuild_index.py' to update the FAISS index")

if __name__ == "__main__":
    main()

