"""
Rebuild FAISS index from clean chunks
"""
import json
import numpy as np
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer

# Paths
CHUNKS_CLEAN = Path("chunks_clean/chunks_clean.jsonl")
EMBEDDINGS_DIR = Path("embeddings")
EMBEDDINGS_DIR.mkdir(exist_ok=True)

print("Loading clean chunks...")
chunks = []
with open(CHUNKS_CLEAN, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            chunks.append(json.loads(line))

print(f"Loaded {len(chunks)} clean chunks")

print("Loading embedding model...")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

print("Generating embeddings...")
# Extract text from chunks (handle both 'chunk_text' and 'text' fields)
texts = [chunk.get('chunk_text') or chunk.get('text', '') for chunk in chunks]

# Generate embeddings
embeddings = embedding_model.encode(
    texts,
    normalize_embeddings=True,
    show_progress_bar=True
).astype('float32')

print(f"Generated {len(embeddings)} embeddings (dimension: {embeddings.shape[1]})")

# Create FAISS index
dimension = embeddings.shape[1]
index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity (normalized vectors)

# Add vectors to index
index.add(embeddings)

print(f"Index created with {index.ntotal} vectors")

# Save index
index_path = EMBEDDINGS_DIR / "faiss_index.bin"
faiss.write_index(index, str(index_path))
print(f"Saved index to {index_path}")

# Create metadata (matching format expected by RAGRetriever)
metadata = []
for chunk in chunks:
    chunk_text = chunk.get('chunk_text') or chunk.get('text', '')
    metadata.append({
        'text': chunk_text,
        'source_id': chunk['source_id'],
        'authority': chunk.get('authority', ''),
        'scheme_tag': chunk['scheme_tag'],
        'source_type': chunk['source_type'],
        'field': chunk.get('field', ''),
        'snippet_keyword': chunk.get('field', '') or 'fulltext'
    })

metadata_path = EMBEDDINGS_DIR / "faiss_metadata.json"
with open(metadata_path, "w", encoding="utf-8") as f:
    json.dump(metadata, f, ensure_ascii=False, indent=2)
print(f"Saved metadata to {metadata_path}")

# Save index metadata
index_metadata = {
    "vector_db": "faiss",
    "index_path": str(index_path),
    "metadata_path": str(metadata_path),
    "distance_metric": "cosine",
    "vector_count": index.ntotal,
    "dimension": dimension,
    "embedding_model": "all-MiniLM-L6-v2"
}

index_meta_path = EMBEDDINGS_DIR / "index_metadata.json"
with open(index_meta_path, "w", encoding="utf-8") as f:
    json.dump(index_metadata, f, indent=2)
print(f"Saved index metadata to {index_meta_path}")

print(f"\n✓ Index rebuild complete: {index.ntotal} vectors from {len(chunks)} clean chunks")

