"""
ChromaDB-backed semantic search for news articles.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False


@dataclass
class NewsVectorStore:
    """
    Persists news embeddings in ChromaDB for semantic retrieval.
    """

    persist_directory: Optional[str] = None
    collection_name: str = "news_articles"

    def __post_init__(self) -> None:
        self.persist_directory = self.persist_directory or os.getenv("CHROMA_PERSIST_DIR", "data/chroma_db")
        self._client = None
        self._collection = None

    @property
    def available(self) -> bool:
        return CHROMADB_AVAILABLE

    @property
    def collection(self):
        if not self.available:
            return None
        if self._collection is None:
            self._client = chromadb.PersistentClient(path=self.persist_directory)
            self._collection = self._client.get_or_create_collection(name=self.collection_name)
        return self._collection

    def upsert_articles(self, articles: List[Dict[str, Any]], embeddings: List[List[float]]) -> None:
        if not self.available or not self.collection:
            logger.info("ChromaDB is unavailable. Skipping vector persistence.")
            return

        documents = []
        ids = []
        metadatas = []
        aligned_embeddings = []
        for article, embedding in zip(articles, embeddings):
            article_id = article.get("article_id") or article.get("url") or article.get("title")
            if not article_id:
                continue
            ids.append(str(article_id))
            documents.append(" ".join(filter(None, [article.get("title"), article.get("content"), article.get("summary")])))
            metadatas.append({
                "ticker": article.get("ticker"),
                "source": article.get("source"),
                "published_at": article.get("published_at"),
                "label": article.get("sentiment", {}).get("label"),
                "article_id": article_id,
            })
            aligned_embeddings.append(embedding)

        if ids:
            self.collection.upsert(
                ids=ids,
                documents=documents,
                embeddings=aligned_embeddings,
                metadatas=metadatas,
            )

    def search(self, query: str, limit: int = 5, ticker: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.available or not self.collection:
            return []

        try:
            from .nlp import FinancialNLPAnalyzer

            analyzer = FinancialNLPAnalyzer()
            query_embedding = analyzer.embed_texts([query])[0]
            where = {"ticker": ticker} if ticker else None
            result = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where,
            )

            formatted = []
            for idx, doc_id in enumerate(result.get("ids", [[]])[0]):
                formatted.append({
                    "id": doc_id,
                    "document": result.get("documents", [[]])[0][idx] if result.get("documents") else None,
                    "metadata": result.get("metadatas", [[]])[0][idx] if result.get("metadatas") else None,
                    "distance": result.get("distances", [[]])[0][idx] if result.get("distances") else None,
                })
            return formatted
        except Exception as exc:
            logger.warning(f"ChromaDB semantic search failed: {exc}")
            return []
