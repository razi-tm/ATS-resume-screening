from __future__ import annotations

import abc
import math
import os
import re
from collections import Counter
from functools import lru_cache

Vector = list[float]


class EmbeddingProvider(abc.ABC):
    @abc.abstractmethod
    def embed(self, texts: list[str]) -> list[Vector]:
        raise NotImplementedError


class SentenceTransformerProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> list[Vector]:
        return self.model.encode(texts, normalize_embeddings=True).tolist()


class TfidfEmbeddingProvider(EmbeddingProvider):
    """Deterministic dependency-light fallback used in CI and constrained environments."""

    def embed(self, texts: list[str]) -> list[Vector]:
        tokenized = [self._tokens(text) for text in texts]
        vocabulary = sorted({token for doc in tokenized for token in doc})[:2048]
        if not vocabulary:
            return [[] for _ in texts]
        index = {token: pos for pos, token in enumerate(vocabulary)}
        doc_freq = Counter(token for doc in tokenized for token in set(doc))
        vectors: list[Vector] = []
        for doc in tokenized:
            counts = Counter(doc)
            vector = [0.0] * len(vocabulary)
            for token, count in counts.items():
                if token in index:
                    idf = math.log((1 + len(texts)) / (1 + doc_freq[token])) + 1
                    vector[index[token]] = float(count) * idf
            norm = math.sqrt(sum(value * value for value in vector)) or 1.0
            vectors.append([value / norm for value in vector])
        return vectors

    def _tokens(self, text: str) -> list[str]:
        return [token.lower() for token in re.findall(r"[a-zA-Z][a-zA-Z+#.]{2,}", text)]


class LLMProvider(abc.ABC):
    @abc.abstractmethod
    def summarize_fit(self, resume_text: str, job_description: str) -> str:
        raise NotImplementedError


class DisabledLLMProvider(LLMProvider):
    def summarize_fit(self, resume_text: str, job_description: str) -> str:
        return "LLM enhancement is disabled; deterministic scoring explanation is shown."


class OpenAIProvider(LLMProvider):
    def __init__(self, model: str = "gpt-4.1-mini") -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    def summarize_fit(self, resume_text: str, job_description: str) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=f"Assess candidate fit briefly.\nJOB:\n{job_description[:4000]}\nRESUME:\n{resume_text[:6000]}",
        )
        return response.output_text


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    provider = os.getenv("EMBEDDING_PROVIDER", "tfidf").lower()
    if provider == "sentence-transformers":
        return SentenceTransformerProvider(os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
    return TfidfEmbeddingProvider()
