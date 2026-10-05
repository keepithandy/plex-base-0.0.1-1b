"""Verified record-start windows for the bounded P2-03 sampler comparison."""
from __future__ import annotations

import json
import random
from itertools import zip_longest
from pathlib import Path

import torch
from torch import Tensor

from .answer_weighting import MAX_INDEX_BYTES, MAX_JSONL_BYTES, PROMPT_END
from .data import TokenCorpus
from .tokenizer import PlexTokenizer, sha256_file


class RecordStartTokenCorpus(TokenCorpus):
    """Start at a uniformly chosen verified prompt; wrap through EOS at EOF.

    Windows retain the ordinary next-token objective and fixed token budget.
    Later records in each window still have preceding context and nonzero positions.
    """

    def __init__(self, token_path: Path, *, dataset_jsonl: Path, index_path: Path,
                 tokenizer: PlexTokenizer, expected_jsonl_sha256: str) -> None:
        for path, limit in ((dataset_jsonl, MAX_JSONL_BYTES), (index_path, MAX_INDEX_BYTES)):
            if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
                raise ValueError("Record sampling needs bounded, regular dataset and index files")
        if sha256_file(dataset_jsonl) != expected_jsonl_sha256:
            raise ValueError("Record-start text differs from the verified tokenizer dataset")
        super().__init__(token_path)
        try:
            entries = json.loads(index_path.read_text(encoding="utf-8"))
            if not isinstance(entries, list) or not entries:
                raise ValueError("Record-start token index is empty or malformed")
            starts, lengths, ids = [], [], set()
            offset = 0
            with dataset_jsonl.open(encoding="utf-8") as stream:
                for line, entry in zip_longest(stream, entries):
                    if line is None or not isinstance(entry, dict):
                        raise ValueError("Record-start text and index have different row counts")
                    row = json.loads(line)
                    if not isinstance(row, dict):
                        raise ValueError("Record-start record is malformed")
                    text, record_id = row.get("text"), row.get("recordId")
                    if (not isinstance(record_id, str) or not record_id or record_id in ids
                            or not isinstance(text, str) or text.count(PROMPT_END) != 1):
                        raise ValueError("Record-start training text has no unique prompt/answer identity")
                    boundary = text.index(PROMPT_END) + len(PROMPT_END)
                    if (not text.startswith("Write a small ") or "\nRequest: " not in text
                            or "\nOutput contract: " not in text
                            or text[boundary:boundary + 1] != "\n" or not text[boundary + 1:]):
                        raise ValueError("Record-start text does not follow the approved prompt/answer format")
                    expected = tokenizer.encode(text) + [3]
                    if (entry.get("recordId") != record_id
                            or type(entry.get("startToken")) is not int
                            or type(entry.get("tokenCount")) is not int
                            or entry["startToken"] != offset or entry["tokenCount"] != len(expected)
                            or offset + len(expected) > self.token_count
                            or self._window(offset, len(expected)).tolist() != expected):
                        raise ValueError("Record-start index differs from packed verified tokens")
                    starts.append(offset)
                    lengths.append(len(expected))
                    ids.add(record_id)
                    offset += len(expected)
            if offset != self.token_count:
                raise ValueError("Record-start index does not cover the packed corpus")
            self.starts = tuple(starts)
            self.lengths = tuple(lengths)
            self.maximum_record_tokens = max(lengths)
            self.sampler_record = {
                "kind": "record-start-v1", "selection": "uniform-record-with-replacement",
                "endPolicy": "circular-eos-to-first-prompt-v1",
                "records": len(starts), "trainJsonlSha256": expected_jsonl_sha256,
                "indexSha256": sha256_file(index_path),
            }
            self._counts = dict.fromkeys(starts, 0)
            self._wrapped = 0
        except Exception:
            self.close()
            raise

    def sample_batch(self, rng: random.Random, batch_size: int,
                     sequence_length: int) -> tuple[Tensor, Tensor]:
        if (batch_size <= 0 or sequence_length <= 0
                or self.token_count < sequence_length + 1
                or self.maximum_record_tokens > sequence_length + 1):
            raise ValueError("Record-start windows must fit complete first records and the token budget")
        windows = []
        for _ in range(batch_size):
            start = rng.choice(self.starts)
            length = sequence_length + 1
            first = min(length, self.token_count - start)
            window = self._window(start, first)
            if first < length:
                window = torch.cat((window, self._window(0, length - first)))
                self._wrapped += 1
            self._counts[start] += 1
            windows.append(window)
        packed = torch.stack(windows)
        return packed[:, :-1], packed[:, 1:]

    def sampling_audit(self) -> dict:
        return {
            "windows": sum(self._counts.values()), "wrappedWindows": self._wrapped,
            "recordsSelected": sum(count > 0 for count in self._counts.values()),
            "minimumFirstRecordSelections": min(self._counts.values()),
            "maximumFirstRecordSelections": max(self._counts.values()),
        }


class CompleteRecordTokenCorpus(RecordStartTokenCorpus):
    """One complete record per batch row; right padding has zero loss weight.

    Rows never contain a second record. Causal attention hides right padding
    from every real input position, and each row starts with position zero.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._length_by_start = dict(zip(self.starts, self.lengths))
        self.sampler_record = {
            **self.sampler_record, "kind": "complete-record-v1",
            "endPolicy": "stop-at-record-eos-v1",
            "paddingPolicy": "right-pad-to-batch-longest-zero-target-weight-v1",
            "tokenAccounting": "nonpadding-next-token-targets-v1",
            "lossReduction": "mean-real-targets-per-microbatch-then-mean-accumulation-v1",
        }
        self._real_targets = self._padding_targets = 0

    def sample_batch(self, rng: random.Random, batch_size: int,
                     sequence_length: int) -> tuple[Tensor, Tensor]:
        raise ValueError("Complete-record sampling requires the padding mask")

    def sample_masked_batch(self, rng: random.Random, batch_size: int,
                            sequence_length: int) -> tuple[Tensor, Tensor, Tensor]:
        if (batch_size <= 0 or sequence_length <= 0
                or self.maximum_record_tokens > sequence_length + 1
                or min(self.lengths) < 2):
            raise ValueError("Complete records must fit the context without truncation")
        starts = [rng.choice(self.starts) for _ in range(batch_size)]
        lengths = [self._length_by_start[start] - 1 for start in starts]
        inputs = torch.zeros((batch_size, max(lengths)), dtype=torch.long)
        targets = torch.zeros_like(inputs)
        weights = torch.zeros_like(inputs, dtype=torch.float32)
        for row, (start, length) in enumerate(zip(starts, lengths)):
            tokens = self._window(start, length + 1)
            inputs[row, :length] = tokens[:-1]
            targets[row, :length] = tokens[1:]
            weights[row, :length] = 1.0
            self._counts[start] += 1
        real_targets = sum(lengths)
        self._real_targets += real_targets
        self._padding_targets += targets.numel() - real_targets
        return inputs, targets, weights

    def replay_progress(self, seed: int, draws: int) -> tuple[int, tuple]:
        """Verify variable-length checkpoint progress from the pinned sampler."""
        if type(draws) is not int or not 0 <= draws <= 1_000_000:
            raise ValueError("Complete-record resume exceeds the bounded replay limit")
        rng = random.Random(seed)
        positions = sum(self._length_by_start[rng.choice(self.starts)] - 1 for _ in range(draws))
        return positions, rng.getstate()

    def sampling_audit(self) -> dict:
        return {
            "examples": sum(self._counts.values()),
            "recordsSelected": sum(count > 0 for count in self._counts.values()),
            "minimumRecordSelections": min(self._counts.values()),
            "maximumRecordSelections": max(self._counts.values()),
            "realTargetPositions": self._real_targets,
            "paddingTargetPositions": self._padding_targets,
        }
