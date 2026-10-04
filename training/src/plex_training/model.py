"""A small GPT-style causal language model initialized from random weights."""

from __future__ import annotations

import torch
from torch import Tensor, nn
from torch.nn import functional as F

from .config import ModelConfig


class TransformerBlock(nn.Module):
    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.attention_norm = nn.LayerNorm(config.width)
        self.attention = nn.MultiheadAttention(
            config.width,
            config.heads,
            dropout=config.dropout,
            batch_first=True,
        )
        nn.init.normal_(self.attention.in_proj_weight, mean=0.0, std=0.02)
        if self.attention.in_proj_bias is not None:
            nn.init.zeros_(self.attention.in_proj_bias)
        self.attention_residual_dropout = nn.Dropout(config.dropout)
        self.feed_forward_norm = nn.LayerNorm(config.width)
        self.feed_forward = nn.Sequential(
            nn.Linear(config.width, config.feed_forward_width),
            nn.GELU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.feed_forward_width, config.width),
            nn.Dropout(config.dropout),
        )

    def forward(self, hidden: Tensor, causal_mask: Tensor) -> Tensor:
        normalized = self.attention_norm(hidden)
        attended = self.attention(
            normalized,
            normalized,
            normalized,
            attn_mask=causal_mask,
            need_weights=False,
        )[0]
        hidden = hidden + self.attention_residual_dropout(attended)
        return hidden + self.feed_forward(self.feed_forward_norm(hidden))


class PlexLanguageModel(nn.Module):
    """Decoder-only pre-layer-norm Transformer with tied token embeddings."""

    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.config = config
        self.token_embeddings = nn.Embedding(config.vocab_size, config.width)
        self.position_embeddings = nn.Embedding(config.context_length, config.width)
        self.embedding_dropout = nn.Dropout(config.dropout)
        self.blocks = nn.ModuleList(TransformerBlock(config) for _ in range(config.layers))
        self.final_norm = nn.LayerNorm(config.width)
        self.apply(self._initialize)

    @staticmethod
    def _initialize(module: nn.Module) -> None:
        if isinstance(module, (nn.Linear, nn.Embedding)):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if isinstance(module, nn.Linear) and module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.LayerNorm):
            nn.init.ones_(module.weight)
            nn.init.zeros_(module.bias)

    def forward(self, input_ids: Tensor, targets: Tensor | None = None) -> tuple[Tensor, Tensor | None]:
        if input_ids.ndim != 2:
            raise ValueError("input_ids must have shape (batch, sequence)")
        batch, sequence = input_ids.shape
        if sequence == 0 or sequence > self.config.context_length:
            raise ValueError("sequence length is outside the configured context")
        if torch.any(input_ids < 0) or torch.any(input_ids >= self.config.vocab_size):
            raise ValueError("input token id is outside the configured vocabulary")
        positions = torch.arange(sequence, device=input_ids.device)
        hidden = self.embedding_dropout(
            self.token_embeddings(input_ids) + self.position_embeddings(positions)[None, :, :]
        )
        causal_mask = torch.ones(
            (sequence, sequence), dtype=torch.bool, device=input_ids.device
        ).triu(diagonal=1)
        for block in self.blocks:
            hidden = block(hidden, causal_mask)
        logits = F.linear(self.final_norm(hidden), self.token_embeddings.weight)
        loss = None
        if targets is not None:
            if targets.shape != (batch, sequence):
                raise ValueError("targets must have the same shape as input_ids")
            loss = F.cross_entropy(logits.reshape(-1, self.config.vocab_size), targets.reshape(-1))
        return logits, loss


def parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters())
