"""Abstract interface for model providers and clients."""

from abc import ABC, abstractmethod
from harness.model.schemas import ModelRequest, ModelResponse


class ModelInterface(ABC):
    """Abstract interface that all model providers/clients must implement."""

    @abstractmethod
    def generate(self, request: ModelRequest) -> ModelResponse:
        """Execute text/tool generation given a ModelRequest."""
        pass
