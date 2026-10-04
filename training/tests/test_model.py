import unittest

import torch

from plex_training.config import tiny_test_config
from plex_training.model import PlexLanguageModel, parameter_count


class ModelTests(unittest.TestCase):
    def setUp(self) -> None:
        torch.manual_seed(7)
        self.config = tiny_test_config()
        self.model = PlexLanguageModel(self.config)

    def test_forward_loss_and_backward(self) -> None:
        tokens = torch.randint(0, 256, (2, 16))
        logits, loss = self.model(tokens, tokens)
        self.assertEqual(tuple(logits.shape), (2, 16, self.config.vocab_size))
        self.assertIsNotNone(loss)
        loss.backward()
        self.assertTrue(all(parameter.grad is not None for parameter in self.model.parameters()))

    def test_causal_mask_hides_future_tokens(self) -> None:
        self.model.eval()
        first = torch.tensor([[1, 2, 3, 4]])
        changed_future = torch.tensor([[1, 2, 99, 100]])
        with torch.no_grad():
            first_logits, _ = self.model(first)
            changed_logits, _ = self.model(changed_future)
        self.assertTrue(torch.allclose(first_logits[:, :2], changed_logits[:, :2], atol=1e-6))

    def test_output_projection_reuses_token_embedding(self) -> None:
        self.assertEqual(parameter_count(self.model), self.config.parameter_count())


if __name__ == "__main__":
    unittest.main()
