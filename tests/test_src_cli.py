import unittest
from unittest.mock import patch
from src.cli import main


class TestCli(unittest.TestCase):
    def test_main_callable(self):
        """Verify that the main entrypoint is a callable object."""
        self.assertTrue(callable(main))

    @patch("src.cli.process_json_to_csv")
    def test_cli_parsing_success(self, mock_process):
        """Verify that main correctly parses arguments and calls the processing function."""
        test_cases = [
            {
                "args": ["input.json", "output.csv"],
                "expected_call": ("input.json", "output.csv", ","),
            },
            {
                "args": ["in.json", "out.csv", "--delimiter", ";"],
                "expected_call": ("in.json", "out.csv", ";"),
            },
            {
                "args": ["in.json", "out.csv", "-d", "|"],
                "expected_call": ("in.json", "out.csv", "|"),
            },
        ]

        for case in test_cases:
            with self.subTest(args=case["args"]):
                mock_process.reset_mock()
                main(case["args"])
                mock_process.assert_called_once()

                args, kwargs = mock_process.call_args
                called_input = args[0] if len(args) > 0 else kwargs.get("input_path")
                called_output = args[1] if len(args) > 1 else kwargs.get("output_path")
                called_delimiter = (
                    args[2] if len(args) > 2 else kwargs.get("delimiter", ",")
                )

                self.assertEqual(called_input, case["expected_call"][0])
                self.assertEqual(called_output, case["expected_call"][1])
                self.assertEqual(called_delimiter, case["expected_call"][2])

    def test_cli_missing_arguments_raises_system_exit(self):
        """Verify that incorrect or missing required arguments cause SystemExit."""
        bad_args_list = [[], ["input.json"], ["--delimiter", ";"]]
        for bad_args in bad_args_list:
            with self.subTest(bad_args=bad_args):
                with patch("sys.stderr"), patch("sys.stdout"):
                    with self.assertRaises(SystemExit):
                        main(bad_args)

    @patch("src.cli.process_json_to_csv")
    @patch("sys.argv", ["cli_entry.py", "sys_in.json", "sys_out.csv"])
    def test_cli_default_args_fallback(self, mock_process):
        """Verify that calling main with None correctly falls back to sys.argv."""
        main(None)
        mock_process.assert_called_once()
        args, kwargs = mock_process.call_args
        called_input = args[0] if len(args) > 0 else kwargs.get("input_path")
        called_output = args[1] if len(args) > 1 else kwargs.get("output_path")
        self.assertEqual(called_input, "sys_in.json")
        self.assertEqual(called_output, "sys_out.csv")
