import argparse
import json
import sys

import ijson.common

from src.converter import process_json_to_csv


def main(args: list[str] | None = None) -> None:
    """
    Parses CLI arguments, converts delimiter escape sequences, triggers process_json_to_csv, and exits with 0, 1, or 2 based on validation and execution outcomes.
    """
    if args is not None:
        if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
            raise TypeError("args must be list[str] or None")

    class _Parser(argparse.ArgumentParser):
        def error(self, message: str) -> None:
            self.print_usage(sys.stderr)
            print(f"CLI Error: {message}", file=sys.stderr)
            sys.exit(1)

    parser = _Parser(
        description="Convert a JSON file containing an array of objects to CSV format."
    )
    parser.add_argument(
        "-i", "--input", required=True, help="Path to the input JSON file"
    )
    parser.add_argument(
        "-o", "--output", required=True, help="Path to the output CSV file"
    )
    parser.add_argument(
        "-d",
        "--delimiter",
        default=",",
        help="Field delimiter character (default: ',')",
    )

    parsed = parser.parse_args(args)

    delimiter = parsed.delimiter
    if delimiter == "\\t":
        delimiter = "\t"

    if len(delimiter) != 1:
        print(
            f"CLI Error: delimiter must be exactly 1 character, got {len(delimiter)!r}",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        process_json_to_csv(parsed.input, parsed.output, delimiter)
    except (FileNotFoundError, PermissionError) as exc:
        print(f"CLI Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except (ValueError, json.JSONDecodeError, ijson.common.JSONError) as exc:
        print(f"Processing Error: {exc}", file=sys.stderr)
        sys.exit(2)

    print("Successfully converted JSON to CSV.")
    sys.exit(0)
