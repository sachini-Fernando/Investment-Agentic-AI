"""
Financial NLP utilities for FinBERT sentiment analysis and spaCy NER.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


def _fallback_entities(text: str) -> List[Dict[str, Any]]:
    candidates = re.findall(r"\b[A-Z][A-Za-z0-9.&-]{2,}\b", text or "")
    stop_words = {"The", "This", "That", "With", "From", "Will", "Today", "Market"}
    seen = set()
    entities = []
    for candidate in candidates:
        if candidate in stop_words or candidate in seen:
            continue
        seen.add(candidate)
        entities.append({"text": candidate, "label": "PROPN", "start": None, "end": None, "confidence": None})
    return entities


@dataclass
class FinancialNLPAnalyzer:
    """
    Uses FinBERT when available, spaCy NER for entity extraction,
    and sentence-transformers for embeddings.
    """

    sentiment_model_name: str = "ProsusAI/finbert"
    embedding_model_name: str = "all-MiniLM-L6-v2"

    def __post_init__(self) -> None:
        self.sentiment_model_name = os.getenv("FINBERT_MODEL", self.sentiment_model_name)
        self.embedding_model_name = os.getenv("EMBEDDING_MODEL", self.embedding_model_name)
        self._sentiment_pipeline = None
        self._nlp = None
        self._embedder = None

    @property
    def sentiment_pipeline(self):
        if self._sentiment_pipeline is None and TRANSFORMERS_AVAILABLE:
            try:
                self._sentiment_pipeline = pipeline("sentiment-analysis", model=self.sentiment_model_name)
            except Exception as exc:
                logger.warning(f"Failed to load FinBERT model '{self.sentiment_model_name}': {exc}")
                self._sentiment_pipeline = False
        return self._sentiment_pipeline if self._sentiment_pipeline not in (None, False) else None

    @property
    def nlp(self):
        if self._nlp is None and SPACY_AVAILABLE:
            try:
                self._nlp = spacy.load("en_core_web_sm")
            except Exception:
                logger.warning("spaCy model en_core_web_sm is unavailable. Falling back to regex entities.")
                self._nlp = False
        return self._nlp if self._nlp not in (None, False) else None

    @property
    def embedder(self):
        if self._embedder is None and SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self._embedder = SentenceTransformer(self.embedding_model_name)
            except Exception as exc:
                logger.warning(f"Failed to load embedding model '{self.embedding_model_name}': {exc}")
                self._embedder = False
        return self._embedder if self._embedder not in (None, False) else None

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        text = text or ""
        if not text.strip():
            return {"label": "NEUTRAL", "score": 0.0, "confidence": 0.0, "source": "empty"}

        sentiment_pipeline = self.sentiment_pipeline
        if sentiment_pipeline is not None:
            try:
                result = sentiment_pipeline(text[:4000])[0]
                label = result.get("label", "neutral").upper()
                score = float(result.get("score", 0.0))
                mapped_score = score if label.startswith("POS") else -score if label.startswith("NEG") else 0.0
                return {
                    "label": "POSITIVE" if label.startswith("POS") else "NEGATIVE" if label.startswith("NEG") else "NEUTRAL",
                    "score": mapped_score,
                    "confidence": score,
                    "source": "finbert",
                }
            except Exception as exc:
                logger.warning(f"FinBERT sentiment analysis failed: {exc}")

        positive_words = {"beat", "growth", "profit", "upgrade", "strong", "bullish", "record", "gain"}
        negative_words = {"miss", "loss", "downgrade", "weak", "bearish", "decline", "risk", "lawsuit"}
        tokens = re.findall(r"\w+", text.lower())
        pos = sum(token in positive_words for token in tokens)
        neg = sum(token in negative_words for token in tokens)
        total = pos + neg
        if total == 0:
            return {"label": "NEUTRAL", "score": 0.0, "confidence": 0.5, "source": "fallback"}
        score = (pos - neg) / total
        return {
            "label": "POSITIVE" if score > 0 else "NEGATIVE" if score < 0 else "NEUTRAL",
            "score": score,
            "confidence": min(1.0, total / 8.0),
            "source": "fallback",
        }

    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        text = text or ""
        if not text.strip():
            return []

        nlp = self.nlp
        if nlp is not None:
            try:
                doc = nlp(text[:10000])
                return [
                    {
                        "text": ent.text,
                        "label": ent.label_,
                        "start": ent.start_char,
                        "end": ent.end_char,
                        "confidence": None,
                    }
                    for ent in doc.ents
                ]
            except Exception as exc:
                logger.warning(f"spaCy NER failed: {exc}")

        return _fallback_entities(text)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        texts = [text or "" for text in texts]
        embedder = self.embedder
        if embedder is not None:
            try:
                vectors = embedder.encode(texts, normalize_embeddings=True)
                return [vector.tolist() for vector in vectors]
            except Exception as exc:
                logger.warning(f"Embedding generation failed: {exc}")

        # Stable deterministic fallback for local/offline use.
        vectors: List[List[float]] = []
        for text in texts:
            vector = [0.0] * 8
            for index, token in enumerate(re.findall(r"\w+", text.lower())):
                vector[index % 8] += (sum(ord(char) for char in token) % 97) / 97.0
            vectors.append(vector)
        return vectors

    def annotate_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        text = " ".join(filter(None, [article.get("title"), article.get("content"), article.get("summary")]))
        sentiment = self.analyze_sentiment(text)
        entities = self.extract_entities(text)
        annotated = dict(article)
        annotated["sentiment"] = sentiment
        annotated["entities"] = entities
        annotated["embedding_text"] = text.strip()
        return annotated

    def annotate_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.annotate_article(article) for article in articles or []]

