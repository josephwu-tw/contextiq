import os
import glob


class DocuBot:
    def __init__(self, docs_folder="docs", llm_client=None):
        self.docs_folder = docs_folder
        self.llm_client = llm_client
        self.documents = self.load_documents()
        self.chunks = self.chunk_documents(self.documents)
        self.index = self.build_index(self.chunks)

    def load_documents(self):
        docs = []
        pattern = os.path.join(self.docs_folder, "*.*")
        for path in glob.glob(pattern):
            if path.endswith(".md") or path.endswith(".txt"):
                with open(path, "r", encoding="utf8") as f:
                    text = f.read()
                docs.append((os.path.basename(path), text))
        return docs

    def chunk_documents(self, documents):
        chunks = []
        for filename, text in documents:
            for paragraph in text.split("\n\n"):
                stripped = paragraph.strip()
                if stripped:
                    chunks.append((filename, stripped))
        return chunks

    def build_index(self, chunks):
        # Inverted index: word → set of chunk indices
        index = {}
        for idx, (_, text) in enumerate(chunks):
            for token in text.lower().split():
                word = token.strip(".,!?;:\"'()")
                if word:
                    index.setdefault(word, set()).add(idx)
        return index

    def score_document(self, query, text):
        _punct = ".,!?;:\"'()"
        query_words = {w.strip(_punct) for w in query.lower().split() if w.strip(_punct)}
        text_words  = {w.strip(_punct) for w in text.lower().split()  if w.strip(_punct)}
        return sum(1 for word in query_words if word in text_words)

    def retrieve(self, query, top_k=3, min_score=1):
        # min_score=1 filters chunks that only matched on stop words
        _punct = ".,!?;:\"'()"
        query_words = {w.strip(_punct) for w in query.lower().split() if w.strip(_punct)}
        candidate_indices = set()
        for word in query_words:
            for idx in self.index.get(word, set()):
                candidate_indices.add(idx)

        scored = []
        for idx in candidate_indices:
            filename, text = self.chunks[idx]
            score = self.score_document(query, text)
            if score >= min_score:
                scored.append((score, filename, text))

        scored.sort(reverse=True)
        return [(fname, text) for _, fname, text in scored[:top_k]]

    def answer_retrieval_only(self, query, top_k=3):
        snippets = self.retrieve(query, top_k=top_k)
        if not snippets:
            return "I do not know based on these docs."
        return "\n---\n".join(f"[{fname}]\n{text}\n" for fname, text in snippets)

    def answer_rag(self, query, top_k=3):
        if self.llm_client is None:
            raise RuntimeError("RAG mode requires an LLM client.")
        snippets = self.retrieve(query, top_k=top_k)
        if not snippets:
            return "I do not know based on these docs."
        return self.llm_client.answer_from_snippets(query, snippets)

    def add_documents(self, new_docs: list):
        """Appends documents and incrementally updates the index without a full rebuild."""
        offset = len(self.chunks)
        self.documents.extend(new_docs)
        new_chunks = self.chunk_documents(new_docs)
        self.chunks.extend(new_chunks)
        for idx, (_, text) in enumerate(new_chunks, start=offset):
            for token in text.lower().split():
                word = token.strip(".,!?;:\"'()")
                if word:
                    self.index.setdefault(word, set()).add(idx)

    def reset_to_default_docs(self):
        self.documents = self.load_documents()
        self.chunks = self.chunk_documents(self.documents)
        self.index = self.build_index(self.chunks)

    @property
    def source_count(self) -> int:
        return len(self.documents)

    def full_corpus_text(self):
        return "\n\n".join(text for _, text in self.documents)
