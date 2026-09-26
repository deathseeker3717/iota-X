"""Abstract interface for model providers."""

from harness.model.interface import ModelInterface
from harness.model.schemas import ModelRequest, ModelResponse


class ModelProvider(ModelInterface):
    """Abstract interface that all model providers must implement."""

    pass
