"""Answer/EOS-only supervision over verified complete Plex training records."""
from __future__ import annotations

import json
import random
from itertools import zip_longest
from pathlib import Path

import torch
from torch import Tensor

from .answer_weighting import PROMPT_END
from .record_sampling import CompleteRecordTokenCorpus
from .tokenizer import PlexTokenizer, sha256_file


class AnswerFocusedCompleteRecordTokenCorpus(CompleteRecordTokenCorpus):
    """Keep the full prompt as context while supervising only answer/EOS targets.

    The underlying record selection, record boundaries, right padding, and Python
    RNG draws are identical to ``CompleteRecordTokenCorpus``. Only the loss mask
    changes: prompt targets receive zero weight, answer/EOS targets receive one,
    and right padding remains zero.
    """

    def __init__(
        self,
        token_path: Path,
        *,
        dataset_jsonl: Path,
        index_path: Path,
        tokenizer: PlexTokenizer,
        expected_jsonl_sha256: str,
    ) -> None:
        super().__init__(
            token_path,
            dataset_jsonl=dataset_jsonl,
            index_path=index_path,
            tokenizer=tokenizer,
            expected_jsonl_sha256=expected_jsonl_sha256,
        )
        try:
            entries = json.loads(index_path.read_text(encoding="utf-8"))
            if not isinstance(entries, list) or len(entries) != len(self.starts):
                raise ValueError("Answer-focused token index is empty or mismatched")

            first_supervised_by_start: dict[int, int] = {}
            with dataset_jsonl.open("r", encoding="utf-8") as stream:
                for line, entry in zip_longest(stream, entries):
                    if line is None or not isinstance(entry, dict):
                        raise ValueError("Answer-focused text and index have different row counts")
                    row = json.loads(line)
                    if not isinstance(row, dict):
                        raise ValueError("Answer-focused record is malformed")
                    text = row.get("text")
                    record_id = row.get("recordId")
                    if (not isinstance(text, str) or text.count(PROMPT_END) != 1
                            or not isinstance(record_id, str) or not record_id):
                        raise ValueError("Answer-focused record has no unique prompt/answer identity")
                    boundary = text.index(PROMPT_END) + len(PROMPT_END)
                    if text[boundary:boundary + 1] != "\n" or not text[boundary + 1:]:
                        raise ValueError("Answer-focused record has no answer after the prompt boundary")

                    prompt_ids = tokenizer.encode(text[:boundary])
                    whole_ids = tokenizer.encode(text)
                    expected = whole_ids + [3]
                    start = entry.get("startToken")
                    if (not prompt_ids or whole_ids[:len(prompt_ids)] != prompt_ids
                            or entry.get("recordId") != record_id
                            or type(start) is not int
                            or self._length_by_start.get(start) != len(expected)
                            or self._window(start, len(expected)).tolist() != expected):
                        raise ValueError("Answer-focused spans differ from verified complete-record tokens")

                    # Targets are shifted one position from inputs. The first token
                    # after the prompt is therefore predicted at prompt_len - 1.
                    first_supervised = len(prompt_ids) - 1
                    if not 0 <= first_supervised < len(expected) - 1:
                        raise ValueError("Answer-focused record has no supervised answer/EOS targets")
                    first_supervised_by_start[start] = first_supervised

            if set(first_supervised_by_start) != set(self.starts):
                raise ValueError("Answer-focused spans do not cover every verified record")

            self._first_supervised_by_start = first_supervised_by_start
            real_per_epoch = sum(self._length_by_start[start] - 1 for start in self.starts)
            supervised_per_epoch = sum(
                (self._length_by_start[start] - 1) - first_supervised_by_start[start]
                for start in self.starts
            )
            excluded_per_epoch = real_per_epoch - supervised_per_epoch
            if supervised_per_epoch <= 0 or excluded_per_epoch <= 0:
                raise ValueError("Answer-focused objective needs both prompt and answer target positions")

            self._supervised_targets = 0
            self._excluded_prompt_targets = 0
            self.objective_record = {
                "kind": "answer-eos-only-complete-record-v1",
                "promptTargetWeight": 0,
                "answerAndEosTargetWeight": 1,
                "paddingTargetWeight": 0,
                "records": len(self.starts),
                "trainJsonlSha256": expected_jsonl_sha256,
                "indexSha256": sha256_file(index_path),
                "realTargetsPerEpoch": real_per_epoch,
                "supervisedTargetsPerEpoch": supervised_per_epoch,
                "excludedPromptTargetsPerEpoch": excluded_per_epoch,
            }
            # Preserve the exact complete-record sampler identity while recording
            # the one intended experimental variable inside the saved settings.
            self.sampler_record = {
                **self.sampler_record,
                "answerObjective": self.objective_record,
            }
        except Exception:
            self.close()
            raise

    def sample_masked_batch(
        self,
        rng: random.Random,
        batch_size: int,
        sequence_length: int,
    ) -> tuple[Tensor, Tensor, Tensor]:
        if (batch_size <= 0 or sequence_length <= 0
                or self.maximum_record_tokens > sequence_length + 1
                or min(self.lengths) < 2):
            raise ValueError("Complete records must fit the context without truncation")

        starts = [rng.choice(self.starts) for _ in range(batch_size)]
        lengths = [self._length_by_start[start] - 1 for start in starts]
        inputs = torch.zeros((batch_size, max(lengths)), dtype=torch.long)
        targets = torch.zeros_like(inputs)
        weights = torch.zeros_like(inputs, dtype=torch.float32)
        supervised_targets = excluded_prompt_targets = 0

        for row, (start, length) in enumerate(zip(starts, lengths)):
            tokens = self._window(start, length + 1)
            inputs[row, :length] = tokens[:-1]
            targets[row, :length] = tokens[1:]
            first_supervised = self._first_supervised_by_start[start]
            weights[row, first_supervised:length] = 1.0
            supervised_targets += length - first_supervised
            excluded_prompt_targets += first_supervised
            self._counts[start] += 1

        real_targets = sum(lengths)
        padding_targets = targets.numel() - real_targets
        if supervised_targets + excluded_prompt_targets != real_targets:
            raise RuntimeError("Answer-focused target accounting is inconsistent")
        self._real_targets += real_targets
        self._padding_targets += padding_targets
        self._supervised_targets += supervised_targets
        self._excluded_prompt_targets += excluded_prompt_targets
        return inputs, targets, weights

    def sampling_audit(self) -> dict:
        return {
            **super().sampling_audit(),
            "supervisedTargetPositions": self._supervised_targets,
            "excludedPromptTargetPositions": self._excluded_prompt_targets,
            "answerObjective": self.objective_record,
        }
