"""Abstract interface for model providers."""

from abc import ABC, abstractmethod
from typing import Optional

from harness.model.schemas import ModelRequest, ModelResponse


class ModelProvider(ABC):
    """Abstract interface that all model providers must implement."""

    @abstractmethod
    def generate(self, request: ModelRequest) -> ModelResponse:
        """Execute text/tool generation given a ModelRequest."""
        pass
