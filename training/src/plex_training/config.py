"""Model configuration shared by training, evaluation, and checkpoints."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ModelConfig:
    vocab_size: int = 16_384
    context_length: int = 512
    width: int = 512
    layers: int = 6
    heads: int = 8
    feed_forward_width: int = 2_048
    dropout: float = 0.1

    def __post_init__(self) -> None:
        positive = {
            "vocab_size": self.vocab_size,
            "context_length": self.context_length,
            "width": self.width,
            "layers": self.layers,
            "heads": self.heads,
            "feed_forward_width": self.feed_forward_width,
        }
        nonintegers = [name for name, value in positive.items() if type(value) is not int]
        if nonintegers:
            raise ValueError(
                f"Configuration dimensions must be exact integers: {', '.join(nonintegers)}"
            )
        invalid = [name for name, value in positive.items() if value <= 0]
        if invalid:
            raise ValueError(f"Configuration values must be positive: {', '.join(invalid)}")
        if self.width % self.heads:
            raise ValueError("width must be divisible by heads")
        if not 0.0 <= self.dropout < 1.0:
            raise ValueError("dropout must be in the range [0, 1)")

    def parameter_count(self) -> int:
        """Count the proposed pre-norm GPT with tied token embeddings."""
        block_parameters = self.layers * (
            4 * self.width * self.width
            + 2 * self.width * self.feed_forward_width
            + self.feed_forward_width
            + 9 * self.width
        )
        token_embeddings = self.vocab_size * self.width
        position_embeddings = self.context_length * self.width
        final_layer_norm = 2 * self.width
        return block_parameters + token_embeddings + position_embeddings + final_layer_norm

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: object) -> "ModelConfig":
        if not isinstance(value, dict):
            raise ValueError("Checkpoint model_config must be an object")
        expected = set(cls.__dataclass_fields__)
        if set(value) != expected:
            raise ValueError("Checkpoint model_config fields do not match this runner")
        try:
            return cls(**value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Checkpoint model_config is invalid") from exc


DEFAULT_CONFIG = ModelConfig()


def tiny_test_config() -> ModelConfig:
    """Small shape used only by tests; never used by the experiment commands."""
    return ModelConfig(
        vocab_size=256,
        context_length=32,
        width=32,
        layers=2,
        heads=4,
        feed_forward_width=128,
        dropout=0.0,
    )
