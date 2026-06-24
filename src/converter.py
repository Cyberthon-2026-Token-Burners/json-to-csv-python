import csv
import json

import ijson


def flatten_dict(data: dict, parent_key: str = "", sep: str = ".") -> dict:
    if not isinstance(data, dict):
        raise TypeError(f"Expected dict, got {type(data).__name__}")
    if not isinstance(parent_key, str):
        raise TypeError(f"parent_key must be str, got {type(parent_key).__name__}")
    if not isinstance(sep, str):
        raise TypeError(f"sep must be str, got {type(sep).__name__}")

    result: dict = {}
    for key, value in data.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, dict):
            nested = flatten_dict(value, new_key, sep)
            for k, v in nested.items():
                if k in result:
                    raise ValueError(f"Key collision detected: '{k}'")
                result[k] = v
        else:
            if new_key in result:
                raise ValueError(f"Key collision detected: '{new_key}'")
            result[new_key] = value
    return result


def serialize_primitive_array(array_data: list) -> str:
    if not isinstance(array_data, list):
        raise TypeError(f"Expected list, got {type(array_data).__name__}")

    for item in array_data:
        if isinstance(item, (list, dict)):
            raise TypeError(f"Nested collections not supported: {type(item).__name__}")
        if not isinstance(item, (bool, int, float, str, type(None))):
            raise TypeError(f"Unsupported type in array: {type(item).__name__}")

    return str(array_data)


def process_json_to_csv(
    input_path: str, output_path: str, delimiter: str = ","
) -> None:
    # Validate JSON syntax and root type before streaming.
    # Per contract: drain parser to surface syntax errors (mapped to JSONDecodeError)
    # before classifying structural errors (non-array root → TypeError).
    try:
        with open(input_path, "rb") as f:
            parser = ijson.parse(f, use_float=True)
            first = next(parser, None)
            if first is None:
                raise json.JSONDecodeError("Expecting value", input_path, 0)
            _, first_event, _ = first
            if first_event != "start_array":
                # Drain to confirm well-formedness; re-raise parse faults before type fault.
                try:
                    for _ in parser:
                        continue
                except ijson.JSONError as exc:
                    raise json.JSONDecodeError(str(exc), input_path, 0) from exc
                raise ValueError(
                    f"Root JSON element must be an array, got: {first_event}"
                )
    except FileNotFoundError:
        raise
    except ijson.JSONError as exc:
        raise json.JSONDecodeError(str(exc), input_path, 0) from exc

    # First pass: collect ordered unique headers without buffering records.
    headers: list = []
    seen_keys: set = set()
    try:
        with open(input_path, "rb") as f:
            for record in ijson.items(f, "item", use_float=True):
                flat = flatten_dict(record)
                for key in flat:
                    if key not in seen_keys:
                        seen_keys.add(key)
                        headers.append(key)
    except ijson.JSONError as exc:
        raise json.JSONDecodeError(str(exc), input_path, 0) from exc

    # Second pass: stream records and write CSV row-by-row (O(1) peak memory per record).
    try:
        with (
            open(input_path, "rb") as f,
            open(output_path, "w", newline="", encoding="utf-8") as out_f,
        ):
            writer = csv.DictWriter(
                out_f,
                fieldnames=headers,
                delimiter=delimiter,
                restval="",
                extrasaction="ignore",
            )
            writer.writeheader()
            for record in ijson.items(f, "item", use_float=True):
                flat = flatten_dict(record)
                row = {}
                for k, v in flat.items():
                    if v is None:
                        row[k] = ""
                    elif isinstance(v, list):
                        row[k] = serialize_primitive_array(v)
                    else:
                        row[k] = str(v)
                writer.writerow(row)
    except ijson.JSONError as exc:
        raise json.JSONDecodeError(str(exc), input_path, 0) from exc
