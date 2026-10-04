"""Bounded local completion from a saved Plex BPE checkpoint and tokenizer."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import torch

from .checkpoint import read_checkpoint
from .initialization import _tokenizer_metadata
from .tokenizer import CODEC, PlexTokenizer, sha256_file
from .telemetry import select_device


def _completion_tokenizer(bundle_dir: Path) -> tuple[PlexTokenizer, dict[str, Any]]:
    if bundle_dir.is_symlink() or not bundle_dir.is_dir():
        raise ValueError("Completion tokenizer bundle must be a regular local directory")
    root = bundle_dir.resolve(strict=True)
    for name in ("tokenizer.json", "tokenizer-config.json", "model-config.json", "manifest.json"):
        path = root / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
            raise ValueError(f"Completion tokenizer file is missing, linked, or too large: {name}")
    _, record = _tokenizer_metadata(root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if (manifest.get("schemaVersion") != 1 or manifest.get("codec") != CODEC
            or manifest.get("actualVocabularySize") != record["actualVocabularySize"]
            or manifest.get("modelVocabularyCapacity") != record["modelVocabularyCapacity"]
            or manifest.get("tokenizerSha256") != record["tokenizerSha256"]
            or manifest.get("modelConfigSha256") != record["modelConfigSha256"]
            or sha256_file(root / "manifest.json") != record["bundleManifestSha256"]):
        raise ValueError("Completion tokenizer manifest does not match its files")
    return PlexTokenizer.load(root), record


def _generate_token_ids(
    model: Any, prompt_ids: list[int], *, actual_vocab: int,
    max_new_tokens: int, temperature: float, seed: int, device: torch.device,
) -> tuple[list[int], bool]:
    if not prompt_ids or any(token < 3 or token >= actual_vocab for token in prompt_ids):
        raise ValueError("Prompt must contain ordinary in-vocabulary tokens")
    if not 4 <= actual_vocab <= model.config.vocab_size:
        raise ValueError("Learned vocabulary is outside the model capacity")
    if type(max_new_tokens) is not int or not 1 <= max_new_tokens <= 256:
        raise ValueError("max-new-tokens must be in the range 1..256")
    if not math.isfinite(temperature) or not 0 <= temperature <= 10:
        raise ValueError("temperature must be from 0 through 10; 0 uses greedy decoding")
    if type(seed) is not int or not 0 <= seed <= 2**63 - 1:
        raise ValueError("seed must be an integer from 0 through 2^63-1")
    generator = torch.Generator(device=device)
    generator.manual_seed(seed)
    model.eval()
    context_ids = prompt_ids.copy()
    generated: list[int] = []
    stopped_at_eos = False
    with torch.no_grad():
        for _ in range(max_new_tokens):
            context = torch.tensor(
                context_ids[-model.config.context_length:], dtype=torch.long, device=device
            ).unsqueeze(0)
            logits, _ = model(context)
            scores = logits[0, -1, :actual_vocab].clone()
            if not torch.isfinite(scores[3:]).all():
                raise ValueError("Model produced non-finite completion logits")
            scores[:3] = -torch.inf  # PAD, UNK, and BOS are not plain text.
            if temperature == 0:
                next_id = int(scores.argmax().item())
            else:
                probabilities = torch.softmax(scores / temperature, dim=-1)
                next_id = int(torch.multinomial(probabilities, 1, generator=generator).item())
            if next_id == 3:  # EOS is a boundary, not emitted text.
                stopped_at_eos = True
                break
            generated.append(next_id)
            context_ids.append(next_id)
    return generated, stopped_at_eos


def complete_pilot(
    *, checkpoint_path: Path, prompt: str, bundle_dir: Path | None = None,
    device_name: str = "auto", max_new_tokens: int = 64,
    temperature: float = 0.0, seed: int = 1337,
) -> dict[str, Any]:
    if not prompt or len(prompt.encode("utf-8")) > 4096:
        raise ValueError("prompt must be nonempty and at most 4096 UTF-8 bytes")
    if checkpoint_path.is_symlink() or not checkpoint_path.is_file():
        raise ValueError("Completion checkpoint must be a regular file")
    selected_bundle = bundle_dir or checkpoint_path.parent / "tokenizer"
    tokenizer, tokenizer_record = _completion_tokenizer(selected_bundle)
    device = select_device(device_name)
    model, payload = read_checkpoint(checkpoint_path, device)
    if (payload.get("codec") != CODEC or payload.get("tokenizerRecord") != tokenizer_record
            or type(payload.get("step")) is not int or payload["step"] <= 0
            or not isinstance(payload.get("datasetRecord"), dict)
            or not isinstance(payload.get("initializationRecord"), dict)
            or payload["initializationRecord"].get("pretrainedCheckpointLoaded") is not False):
        raise ValueError("Checkpoint is not a trained Plex pilot with the matching tokenizer")
    prompt_ids = tokenizer.encode(prompt)
    generated, stopped_at_eos = _generate_token_ids(
        model, prompt_ids, actual_vocab=tokenizer.vocabulary_size,
        max_new_tokens=max_new_tokens, temperature=temperature, seed=seed,
        device=device,
    )
    text = tokenizer.decode(prompt_ids + generated)
    if not text.startswith(prompt):
        raise RuntimeError("Tokenizer did not preserve the completion prompt")
    return {
        "checkpoint": str(checkpoint_path.resolve()),
        "checkpointSha256": sha256_file(checkpoint_path),
        "checkpointStep": payload["step"],
        "tokenizerSha256": tokenizer_record["tokenizerSha256"],
        "device": str(device),
        "sampling": "greedy" if temperature == 0 else "seeded-temperature",
        "temperature": temperature,
        "seed": seed,
        "prompt": prompt,
        "completion": text[len(prompt):],
        "text": text,
        "generatedTokenCount": len(generated),
        "stoppedAtEos": stopped_at_eos,
        "pretrainedCheckpointLoaded": False,
    }
