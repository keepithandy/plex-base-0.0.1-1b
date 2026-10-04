import unittest

from plex_training.config import DEFAULT_CONFIG, ModelConfig, tiny_test_config


class ModelConfigTests(unittest.TestCase):
    def test_default_parameter_count_matches_p1_12(self) -> None:
        self.assertEqual(DEFAULT_CONFIG.parameter_count(), 27_566_080)

    def test_config_round_trips_through_plain_data(self) -> None:
        self.assertEqual(ModelConfig.from_dict(DEFAULT_CONFIG.to_dict()), DEFAULT_CONFIG)

    def test_invalid_head_divisibility_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "divisible"):
            ModelConfig(width=31, heads=4)

    def test_tiny_test_model_is_separate_from_default(self) -> None:
        self.assertLess(tiny_test_config().parameter_count(), DEFAULT_CONFIG.parameter_count())


if __name__ == "__main__":
    unittest.main()
