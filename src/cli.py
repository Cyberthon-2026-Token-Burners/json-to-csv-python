import argparse

from src.converter import process_json_to_csv


def main(args: list | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Convert a JSON file containing an array of objects to CSV format."
    )
    parser.add_argument("input", help="Path to the input JSON file")
    parser.add_argument("output", help="Path to the output CSV file")
    parser.add_argument(
        "--delimiter",
        "-d",
        default=",",
        help="Field delimiter character (default: ',')",
    )

    parsed = parser.parse_args(args)
    process_json_to_csv(parsed.input, parsed.output, parsed.delimiter)
