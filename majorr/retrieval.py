import hashlib

import chromadb


class CodeIndex:
    """Stores code chunks as embeddings in ChromaDB and retrieves the most similar ones."""

    def __init__(self, chunks, repo_key="default", db_path="chroma_db"):
        self.chunks = chunks
        self.client = chromadb.PersistentClient(path=db_path)
        name = "code_" + hashlib.md5(repo_key.encode()).hexdigest()[:12]
        try:
            self.client.delete_collection(name)
        except Exception:
            pass
        self.collection = self.client.create_collection(
            name=name, metadata={"hnsw:space": "cosine"})
        if chunks:
            docs = [f"{c['file']} {c['name']}\n{c['code']}" for c in chunks]
            ids = [str(i) for i in range(len(chunks))]
            for start in range(0, len(docs), 500):
                self.collection.add(ids=ids[start:start + 500],
                                    documents=docs[start:start + 500])

    def search(self, query, k=4, prefer_file=None):
        if not self.chunks:
            return []
        n = min(len(self.chunks), k * 3 if prefer_file else k)
        res = self.collection.query(query_texts=[query], n_results=n)
        ranked = []
        for idx, dist in zip(res["ids"][0], res["distances"][0]):
            chunk = self.chunks[int(idx)]
            score = 1.0 - dist
            if prefer_file and chunk["file"] == prefer_file:
                score += 0.25
            ranked.append(dict(chunk, score=round(score, 3)))
        ranked.sort(key=lambda c: c["score"], reverse=True)
        return ranked[:k]