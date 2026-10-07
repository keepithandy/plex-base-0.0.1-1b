import random
import tempfile
import unittest
from pathlib import Path

import torch

from plex_training.config import DEFAULT_CONFIG
from plex_training.pilot import _initialization_seed
from plex_training.tokenizer import CODEC


class TaskFineTuneSafetyTests(unittest.TestCase):
    def test_generic_pilot_rejects_task_stage_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            checkpoint = Path(temporary) / "stage.pt"
            tokenizer_record = {
                "codec": CODEC,
                "actualVocabularySize": 16384,
                "modelVocabularyCapacity": 16384,
                "tokenizerSha256": "fixture",
                "bundleManifestSha256": "fixture-bundle",
                "modelConfigSha256": "fixture-config",
            }
            torch.save({
                "formatVersion": 1,
                "modelFamily": "plex-from-scratch",
                "modelConfig": DEFAULT_CONFIG.to_dict(),
                "step": 0,
                "seed": 1337,
                "codec": CODEC,
                "tokenizerRecord": tokenizer_record,
                "optimizerStateDict": {},
                "initializationRecord": {
                    "pretrainedCheckpointLoaded": False,
                    "pretrainedModelWeightsLoaded": False,
                },
                "stageTransitionRecord": {
                    "kind": "plex-task-finetune-stage-transition-v1",
                    "modelTrainingPerformed": False,
                },
                "samplingRngState": random.Random(1337).getstate(),
                "torchCpuRngState": torch.get_rng_state(),
                "torchCudaRngStates": [],
            }, checkpoint)
            with self.assertRaisesRegex(ValueError, "random initialization"):
                _initialization_seed(checkpoint, tokenizer_record)


if __name__ == "__main__":
    unittest.main()
