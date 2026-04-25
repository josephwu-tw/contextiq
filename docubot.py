"""
Core DocuBot class responsible for:
- Loading documents from the docs/ folder
- Building a simple retrieval index (Phase 1)
- Retrieving relevant snippets (Phase 1)
- Supporting retrieval only answers
- Supporting RAG answers when paired with Gemini (Phase 2)
"""

import os
import glob

class DocuBot:
    def __init__(self, docs_folder="docs", llm_client=None):
        """
        docs_folder: directory containing project documentation files
        llm_client: optional Gemini client for LLM based answers
        """
        self.docs_folder = docs_folder
        self.llm_client = llm_client

        # Load documents into memory
        self.documents = self.load_documents()  # List of (filename, full_text)

        # Split documents into paragraph-level chunks for finer retrieval
        self.chunks = self.chunk_documents(self.documents)  # List of (filename, chunk_text)

        # Build a retrieval index over chunks
        self.index = self.build_index(self.chunks)

    # -----------------------------------------------------------
    # Document Loading
    # -----------------------------------------------------------

    def load_documents(self):
        """
        Loads all .md and .txt files inside docs_folder.
        Returns a list of tuples: (filename, text)
        """
        docs = []
        pattern = os.path.join(self.docs_folder, "*.*")
        for path in glob.glob(pattern):
            if path.endswith(".md") or path.endswith(".txt"):
                with open(path, "r", encoding="utf8") as f:
                    text = f.read()
                filename = os.path.basename(path)
                docs.append((filename, text))
        return docs

    # -----------------------------------------------------------
    # Chunking (Phase 1 refactor)
    # -----------------------------------------------------------

    def chunk_documents(self, documents):
        """
        Splits each document into paragraph-level chunks by splitting on blank lines.
        Returns a flat list of (filename, chunk_text) tuples, skipping empty chunks.
        Paragraph splitting aligns naturally with Markdown sections and headers.
        """
        chunks = []
        for filename, text in documents:
            for paragraph in text.split("\n\n"):
                stripped = paragraph.strip()
                if stripped:
                    chunks.append((filename, stripped))
        return chunks

    # -----------------------------------------------------------
    # Index Construction (Phase 1)
    # -----------------------------------------------------------

    def build_index(self, chunks):
        """
        Builds an inverted index mapping lowercase words to the set of chunk
        indices (positions in self.chunks) where they appear.

        Example structure:
        {
            "token": {0, 3, 7},
            "database": {12}
        }
        """
        index = {}
        for idx, (_, text) in enumerate(chunks):
            for token in text.lower().split():
                word = token.strip(".,!?;:\"'()")
                if word:
                    index.setdefault(word, set())
                    index[word].add(idx)
        return index

    # -----------------------------------------------------------
    # Scoring and Retrieval (Phase 1)
    # -----------------------------------------------------------

    def score_document(self, query, text):
        """
        TODO (Phase 1):
        Return a simple relevance score for how well the text matches the query.

        Suggested baseline:
        - Convert query into lowercase words
        - Count how many appear in the text
        - Return the count as the score
        """
        query_words = query.lower().split()
        text_lower = text.lower()
        return sum(1 for word in query_words if word in text_lower)

    def retrieve(self, query, top_k=3, min_score=1):
        """
        Use the index to find candidate chunks, score them, and return the
        top_k results sorted by score descending.

        min_score guardrail: chunks where none of the query words matched are
        excluded. This prevents returning irrelevant content when the index
        happens to match on stop words.
        """
        query_words = set(query.lower().split())
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

    # -----------------------------------------------------------
    # Answering Modes
    # -----------------------------------------------------------

    def answer_retrieval_only(self, query, top_k=3):
        """
        Phase 1 retrieval only mode.
        Returns raw snippets and filenames with no LLM involved.
        """
        snippets = self.retrieve(query, top_k=top_k)

        if not snippets:
            return "I do not know based on these docs."

        formatted = []
        for filename, text in snippets:
            formatted.append(f"[{filename}]\n{text}\n")

        return "\n---\n".join(formatted)

    def answer_rag(self, query, top_k=3):
        """
        Phase 2 RAG mode.
        Uses student retrieval to select snippets, then asks Gemini
        to generate an answer using only those snippets.
        """
        if self.llm_client is None:
            raise RuntimeError(
                "RAG mode requires an LLM client. Provide a GeminiClient instance."
            )

        snippets = self.retrieve(query, top_k=top_k)

        if not snippets:
            return "I do not know based on these docs."

        return self.llm_client.answer_from_snippets(query, snippets)

    # -----------------------------------------------------------
    # Dynamic document management (RAG Enhancement)
    # -----------------------------------------------------------

    def add_documents(self, new_docs: list):
        """
        Adds (filename, text) tuples to the corpus and incrementally
        updates the index without rebuilding it from scratch.
        """
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
        """Discards any added documents and reloads only the original docs folder."""
        self.documents = self.load_documents()
        self.chunks = self.chunk_documents(self.documents)
        self.index = self.build_index(self.chunks)

    @property
    def source_count(self) -> int:
        return len(self.documents)

    # -----------------------------------------------------------
    # Bonus Helper: concatenated docs for naive generation mode
    # -----------------------------------------------------------

    def full_corpus_text(self):
        """
        Returns all documents concatenated into a single string.
        This is used in Phase 0 for naive 'generation only' baselines.
        """
        return "\n\n".join(text for _, text in self.documents)
