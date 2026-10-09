"""Verified answer-token weights for a packed, approved Plex BPE corpus."""
from __future__ import annotations

import hashlib
import json
import random
from itertools import zip_longest
from pathlib import Path

import torch
from torch import Tensor

from .data import TokenCorpus
from .tokenizer import PlexTokenizer, sha256_file

PROMPT_END = "Return code only. Do not include Markdown fences or explanations."
MAX_INDEX_BYTES = 16 * 1024 * 1024
MAX_JSONL_BYTES = 64 * 1024 * 1024


class AnswerWeightedTokenCorpus(TokenCorpus):
    """Use the same sampled windows as TokenCorpus, weighting target positions."""

    def __init__(
        self, token_path: Path, *, dataset_jsonl: Path, index_path: Path,
        tokenizer: PlexTokenizer, expected_jsonl_sha256: str, answer_weight: int = 4,
    ) -> None:
        if type(answer_weight) is not int or answer_weight != 4:
            raise ValueError("The controlled comparison uses answer weight 4 only")
        for path, limit in ((dataset_jsonl, MAX_JSONL_BYTES), (index_path, MAX_INDEX_BYTES)):
            if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
                raise ValueError("Answer weighting needs bounded, regular dataset and index files")
        if sha256_file(dataset_jsonl) != expected_jsonl_sha256:
            raise ValueError("Answer-weighted text differs from the verified tokenizer dataset")
        super().__init__(token_path)
        try:
            entries = json.loads(index_path.read_text(encoding="utf-8"))
            if not isinstance(entries, list) or not entries:
                raise ValueError("Answer-weighted token index is empty or malformed")
            weights = bytearray([1]) * self.token_count
            offset = prompt_count = answer_count = record_count = 0
            sentinel = object()
            with dataset_jsonl.open("r", encoding="utf-8") as stream:
                for line, entry in zip_longest(stream, entries, fillvalue=sentinel):
                    if line is sentinel:
                        raise ValueError("Training dataset has fewer rows than its token index")
                    if entry is sentinel:
                        raise ValueError("Training dataset has more rows than its token index")
                    row = json.loads(line)
                    if not isinstance(row, dict) or not isinstance(entry, dict):
                        raise ValueError("Answer-weighted record or index is malformed")
                    text = row.get("text")
                    if not isinstance(text, str) or text.count(PROMPT_END) != 1:
                        raise ValueError("Training text has no unique answer boundary")
                    boundary = text.index(PROMPT_END) + len(PROMPT_END)
                    if (not text.startswith("Write a small ") or "\nRequest: " not in text
                            or "\nOutput contract: " not in text or text[boundary:boundary + 1] != "\n"
                            or not text[boundary + 1:]):
                        raise ValueError("Training text does not follow the approved prompt/answer format")
                    prompt_ids = tokenizer.encode(text[:boundary])
                    whole_ids = tokenizer.encode(text)
                    expected = whole_ids + [3]
                    if (whole_ids[:len(prompt_ids)] != prompt_ids
                            or entry.get("recordId") != row.get("recordId")
                            or entry.get("startToken") != offset
                            or entry.get("tokenCount") != len(expected)
                            or offset + len(expected) > self.token_count
                            or self._window(offset, len(expected)).tolist() != expected):
                        raise ValueError("Answer-weighted spans differ from packed verified tokens")
                    first_answer = offset + len(prompt_ids)
                    end = offset + len(expected)
                    weights[first_answer:end] = bytes([answer_weight]) * (end - first_answer)
                    prompt_count += len(prompt_ids)
                    answer_count += end - first_answer
                    offset = end
                    record_count += 1
            if record_count != len(entries) or offset != self.token_count or not prompt_count or not answer_count:
                raise ValueError("Answer-weighted records do not cover the packed corpus")
            self._weights = weights
            self.objective_record = {
                "kind": "answer-weighted-next-token-v1",
                "promptWeight": 1,
                "answerAndEosWeight": answer_weight,
                "trainJsonlSha256": expected_jsonl_sha256,
                "weightMapSha256": hashlib.sha256(weights).hexdigest(),
                "promptTokens": prompt_count,
                "answerAndEosTokens": answer_count,
                "records": record_count,
            }
        except Exception:
            self.close()
            raise

    def sample_weighted_batch(
        self, rng: random.Random, batch_size: int, sequence_length: int,
    ) -> tuple[Tensor, Tensor, Tensor]:
        maximum_start = self.token_count - sequence_length - 1
        if maximum_start < 0:
            raise ValueError("Answer-weighted corpus is shorter than a complete training window")
        starts = [rng.randint(0, maximum_start) for _ in range(batch_size)]
        inputs = torch.stack([self._window(start, sequence_length) for start in starts])
        targets = torch.stack([self._window(start + 1, sequence_length) for start in starts])
        weights = torch.tensor(
            [list(self._weights[start + 1:start + sequence_length + 1]) for start in starts],
            dtype=torch.float32,
        )
        return inputs, targets, weights
