import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase2"))
from prepare_binding_experiment import ARTIFACT_ROOT, prepare, verify_prepared
from run_binding_experiment import validate_bounds, require_identical_initial_weights


class BindingExperimentTests(unittest.TestCase):
    def test_training_bounds_reject_extensions_and_invalid_values(self):
        validate_bounds(100, 10)
        for steps, minutes in ((101, 10), (0, 10), (True, 10), (100, 11),
                               (100, 0), (100, float("nan"))):
            with self.subTest(steps=steps, minutes=minutes), self.assertRaises(ValueError):
                validate_bounds(steps, minutes)

    def test_weight_check_rejects_trained_external_or_different_parameters(self):
        payload = {"step": 0, "seed": 1337, "modelFamily": "plex-from-scratch", "codec": "fixture",
                   "initializationRecord": {"pretrainedCheckpointLoaded": False, "pretrainedModelWeightsLoaded": False},
                   "modelConfig": {"fixture": True}, "optimizerStateDict": {"state": {}},
                   "modelStateDict": {"fixture": (1, 2)}}
        require_identical_initial_weights([payload, copy.deepcopy(payload)], lambda a, b: a == b)
        for change in ("step", "pretrained", "weights"):
            other = copy.deepcopy(payload)
            if change == "step":
                other["step"] = 1
            elif change == "pretrained":
                other["initializationRecord"]["pretrainedModelWeightsLoaded"] = True
            else:
                other["modelStateDict"]["fixture"] = (1, 3)
            with self.subTest(change=change), self.assertRaises(ValueError):
                require_identical_initial_weights([payload, other], lambda a, b: a == b)

    def test_prepared_inputs_have_distinct_training_and_identical_validation(self):
        with tempfile.TemporaryDirectory(dir=ARTIFACT_ROOT) as directory:
            root = Path(directory) / "prepared"
            plan = prepare(root)
            self.assertEqual(verify_prepared(root), {k: v for k, v in plan.items() if k != "preparedDirectory"})
            self.assertEqual(plan["arms"]["original-only"]["trainRecords"], 6)
            self.assertEqual(plan["arms"]["varied"]["trainRecords"], 24)
            self.assertFalse(plan["tokenizerRefitted"])
            self.assertEqual((root / "original-only/dataset/validation.jsonl").read_bytes(),
                             (root / "varied/dataset/validation.jsonl").read_bytes())
            self.assertNotEqual((root / "original-only/dataset/train.jsonl").read_bytes(),
                                (root / "varied/dataset/train.jsonl").read_bytes())
            tokens = root / "varied/tokenizer/train.tokens.u16le"
            raw = tokens.read_bytes()
            tokens.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
            with self.assertRaisesRegex(ValueError, "input changed"):
                verify_prepared(root)
            tokens.write_bytes(raw)
            with self.assertRaises(FileExistsError):
                prepare(root)


if __name__ == "__main__":
    unittest.main()
