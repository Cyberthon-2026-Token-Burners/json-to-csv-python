import io
import json
import unittest
from unittest.mock import patch
from src.cli import main


class TestCli(unittest.TestCase):
    def test_main_callable(self):
        """Verify that the main entrypoint is a callable object."""
        self.assertTrue(callable(main))

    def test_main_args_type_boundaries(self):
        """Verify that main raises TypeError when args is not a list or None."""
        invalid_types = [
            123,
            "not-a-list",
            {"key": "val"},
            True,
            False,
        ]
        for val in invalid_types:
            with self.subTest(val=val):
                with self.assertRaises(TypeError):
                    main(val)

    def test_main_args_list_with_invalid_element_types(self):
        """Verify that passing a list containing non-strings raises TypeError."""
        invalid_element_lists = [
            [1, 2, 3],
            ["-i", 123],
            ["-i", "valid.json", "-o", "out.csv", 456],
            [None],
            [True],
        ]
        for val in invalid_element_lists:
            with self.subTest(val=val):
                with self.assertRaises(TypeError):
                    main(val)

    @patch("src.cli.process_json_to_csv")
    def test_cli_valid_invocations(self, mock_process):
        """Test valid CLI arguments and verify correct arguments are passed to the core engine."""
        test_cases = [
            (
                ["-i", "valid.json", "-o", "out.csv", "-d", ";"],
                ("valid.json", "out.csv", ";"),
            ),
            (
                ["-i", "valid.json", "-o", "out.csv", "-d", "\\t"],
                ("valid.json", "out.csv", "\t"),
            ),
            (
                ["-i", "valid.json", "-o", "out.csv", "-d", "\t"],
                ("valid.json", "out.csv", "\t"),
            ),
            (
                ["-i", "valid.json", "-o", "out.csv"],
                ("valid.json", "out.csv", ","),
            ),
            (
                ["--input", "valid.json", "--output", "out.csv", "--delimiter", "|"],
                ("valid.json", "out.csv", "|"),
            ),
        ]

        for args, expected in test_cases:
            with self.subTest(args=args):
                mock_process.reset_mock()
                stdout_capture = io.StringIO()
                stderr_capture = io.StringIO()
                with (
                    patch("sys.stdout", stdout_capture),
                    patch("sys.stderr", stderr_capture),
                ):
                    with self.assertRaises(SystemExit) as cm:
                        main(args)
                    self.assertEqual(cm.exception.code, 0)

                mock_process.assert_called_once_with(*expected)
                self.assertIn(
                    "Successfully converted JSON to CSV.", stdout_capture.getvalue()
                )

    @patch("src.cli.process_json_to_csv")
    def test_cli_errors_exit_code_1(self, mock_process):
        """Verify that CLI validation or missing files lead to Exit Code 1 without global filesystem mocking."""

        def process_side_effect(input_path, output_path, delimiter=","):
            if "missing.json" in input_path:
                raise FileNotFoundError("File not found")
            return None

        mock_process.side_effect = process_side_effect

        non_calling_cases = [
            ["-i", "valid.json"],
            ["-o", "out.csv"],
            ["-i", "valid.json", "-o", "out.csv", "-d", "abc"],
            ["-i", "valid.json", "-o", "out.csv", "-d", ""],
        ]
        for args in non_calling_cases:
            with self.subTest(args=args):
                mock_process.reset_mock()
                stdout_capture = io.StringIO()
                stderr_capture = io.StringIO()
                with (
                    patch("sys.stdout", stdout_capture),
                    patch("sys.stderr", stderr_capture),
                ):
                    with self.assertRaises(SystemExit) as cm:
                        main(args)
                    self.assertEqual(cm.exception.code, 1)
                mock_process.assert_not_called()

        with self.subTest(args="missing.json"):
            mock_process.reset_mock()
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            with (
                patch("sys.stdout", stdout_capture),
                patch("sys.stderr", stderr_capture),
            ):
                with self.assertRaises(SystemExit) as cm:
                    main(["-i", "missing.json", "-o", "out.csv"])
                self.assertEqual(cm.exception.code, 1)
            mock_process.assert_called_once_with("missing.json", "out.csv", ",")

    @patch("src.cli.process_json_to_csv")
    def test_cli_processing_errors_exit_code_2(self, mock_process):
        """Test cases where process_json_to_csv raises exceptions, leading to Exit Code 2 and 'Processing Error: '."""
        exceptions_to_test = [
            json.JSONDecodeError("Expecting value", "{}", 0),
            ValueError("Key collision or root not an array"),
        ]

        for exc in exceptions_to_test:
            with self.subTest(exc=type(exc)):
                mock_process.side_effect = exc
                stdout_capture = io.StringIO()
                stderr_capture = io.StringIO()

                with (
                    patch("sys.stdout", stdout_capture),
                    patch("sys.stderr", stderr_capture),
                ):
                    with self.assertRaises(SystemExit) as cm:
                        main(["-i", "malformed.json", "-o", "out.csv"])
                    self.assertEqual(cm.exception.code, 2)

                err_msg = stderr_capture.getvalue()
                self.assertTrue(
                    err_msg.startswith("Processing Error:")
                    or "Processing Error:" in err_msg,
                    f"Expected 'Processing Error:' in stderr, got: {err_msg}",
                )

    @patch("src.cli.process_json_to_csv")
    def test_cli_default_args_fallback(self, mock_process):
        """Verify that calling main with None correctly falls back to sys.argv."""
        test_args = ["cli.py", "-i", "valid.json", "-o", "out.csv", "-d", ";"]
        with patch("sys.argv", test_args):
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            with (
                patch("sys.stdout", stdout_capture),
                patch("sys.stderr", stderr_capture),
            ):
                with self.assertRaises(SystemExit) as cm:
                    main(None)
                self.assertEqual(cm.exception.code, 0)
            mock_process.assert_called_once_with("valid.json", "out.csv", ";")

    @patch("src.cli.process_json_to_csv")
    def test_cli_main_no_args_provided(self, mock_process):
        """Verify that calling main() with no arguments defaults to None and works with sys.argv."""
        test_args = ["cli.py", "-i", "valid.json", "-o", "out.csv"]
        with patch("sys.argv", test_args):
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            with (
                patch("sys.stdout", stdout_capture),
                patch("sys.stderr", stderr_capture),
            ):
                with self.assertRaises(SystemExit) as cm:
                    main()
                self.assertEqual(cm.exception.code, 0)
            mock_process.assert_called_once_with("valid.json", "out.csv", ",")
