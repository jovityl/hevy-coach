from abc import ABC, abstractmethod


class EmbeddingClient(ABC):
    """Port for turning text into embedding vectors. The OpenAI adapter is one
    implementation; tests use a deterministic fake."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed each input text; returns one vector per input, in order."""
        ...
