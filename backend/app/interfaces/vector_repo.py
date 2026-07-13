from abc import ABC, abstractmethod

from app.domain.rag import Finding


class VectorRepository(ABC):
    """Port for storing and similarity-searching research findings. The default
    binding is CorpusRepository (pgvector); a Pinecone adapter can implement the
    same interface (§3.2) without touching services."""

    @abstractmethod
    async def add(self, finding: Finding, abstract_text: str, embedding: list[float]) -> None:
        """Persist a finding with its embedding."""
        ...

    @abstractmethod
    async def search(self, embedding: list[float], k: int) -> list[Finding]:
        """Return the k findings most similar to the query embedding (cosine)."""
        ...
