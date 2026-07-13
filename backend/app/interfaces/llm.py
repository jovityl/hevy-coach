from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Port for chat/completion. Used for the one-time abstract condensation
    (ingestion) and the coaching synthesis — never for counting numbers."""

    @abstractmethod
    async def complete(self, prompt: str) -> str:
        """Return the model's completion for a single prompt."""
        ...
