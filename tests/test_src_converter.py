import unittest
import tempfile
import os
import json
import csv
from src.converter import flatten_dict, serialize_primitive_array, process_json_to_csv


class TestConverter(unittest.TestCase):
    def test_flatten_dict_success(self):
        cases = [
            (
                "acceptance_example_1",
                {"a": 1, "b": {"c": 2}},
                "",
                ".",
                {"a": 1, "b.c": 2},
            ),
            (
                "multi_level_nesting",
                {"a": {"b": {"c": {"d": 4}}}},
                "",
                ".",
                {"a.b.c.d": 4},
            ),
            (
                "flat_dict_no_change",
                {"x": 100, "y": "hello", "z": True},
                "",
                ".",
                {"x": 100, "y": "hello", "z": True},
            ),
            ("custom_separator", {"a": {"b": 5}}, "", "_", {"a_b": 5}),
            (
                "custom_prefix_and_sep",
                {"a": {"b": 5}},
                "prefix",
                "_",
                {"prefix_a_b": 5},
            ),
            ("empty_dict", {}, "", ".", {}),
            ("empty_string_key", {"": 1}, "", ".", {"": 1}),
            ("none_values", {"a": None}, "", ".", {"a": None}),
        ]
        for name, data, parent_key, sep, expected in cases:
            with self.subTest(case=name):
                result = flatten_dict(data, parent_key=parent_key, sep=sep)
                self.assertEqual(result, expected)

    def test_flatten_dict_type_and_value_errors(self):
        cases = [
            (
                "acceptance_example_2_collision",
                {"a": {"b": 1}, "a.b": 2},
                "",
                ".",
                ValueError,
            ),
            ("reverse_collision", {"a.b": 1, "a": {"b": 2}}, "", ".", ValueError),
            ("input_not_dict_string", "not a dict", "", ".", TypeError),
            ("input_not_dict_integer", 123, "", ".", TypeError),
            ("input_not_dict_none", None, "", ".", TypeError),
            ("invalid_parent_key_type", {"a": 1}, 123, ".", TypeError),
            ("invalid_sep_type", {"a": 1}, "", 123, TypeError),
        ]
        for name, data, parent_key, sep, expected_exception in cases:
            with self.subTest(case=name):
                with self.assertRaises(expected_exception):
                    flatten_dict(data, parent_key=parent_key, sep=sep)

    def test_serialize_primitive_array_success(self):
        cases = [
            ("acceptance_example_3", [1, 2, 3], "[1, 2, 3]"),
            ("strings", ["a", "b"], '["a", "b"]'),
            ("booleans_and_null", [True, False, None], "[true, false, null]"),
            ("floats", [1.5, 2.25], "[1.5, 2.25]"),
            ("empty_list", [], "[]"),
        ]
        for name, array_data, expected in cases:
            with self.subTest(case=name):
                result = serialize_primitive_array(array_data)
                self.assertEqual(json.loads(result), json.loads(expected))

    def test_serialize_primitive_array_errors(self):
        cases = [
            ("acceptance_example_4_nested_dict", [1, {"nested": True}], TypeError),
            ("nested_list", [1, [2, 3]], TypeError),
            ("input_string", "not a list", TypeError),
            ("input_int", 123, TypeError),
            ("input_none", None, TypeError),
            ("list_with_unsupported_object", [1, object()], TypeError),
        ]
        for name, array_data, expected_exception in cases:
            with self.subTest(case=name):
                with self.assertRaises(expected_exception):
                    serialize_primitive_array(array_data)

    def test_process_json_to_csv_success(self):
        cases = [
            (
                "flat_records",
                [{"a": 1, "b": 2}, {"a": 3, "b": 4}],
                ",",
                "a,b\r\n1,2\r\n3,4\r\n",
            ),
            (
                "nested_records",
                [{"a": 1, "b": {"c": 2}}, {"a": 3, "b": {"c": 4}}],
                ",",
                "a,b.c\r\n1,2\r\n3,4\r\n",
            ),
            ("heterogeneous_records", [{"a": 1}, {"b": 2}], ",", None),
            ("custom_delimiter", [{"a": 1, "b": 2}], ";", "a;b\r\n1;2\r\n"),
            (
                "special_characters",
                [{"a": "hello, world", "b": "line\\nbreak"}],
                ",",
                None,
            ),
        ]
        for name, json_data, delimiter, expected_raw in cases:
            with self.subTest(case=name):
                with tempfile.TemporaryDirectory() as tmpdir:
                    input_path = os.path.join(tmpdir, "input.json")
                    output_path = os.path.join(tmpdir, "output.csv")
                    with open(input_path, "w", encoding="utf-8") as f:
                        json.dump(json_data, f)
                    process_json_to_csv(input_path, output_path, delimiter=delimiter)
                    self.assertTrue(os.path.exists(output_path))
                    with open(output_path, "r", newline="", encoding="utf-8") as f:
                        raw_content = f.read()
                    with open(output_path, "r", newline="", encoding="utf-8") as f:
                        reader = csv.DictReader(f, delimiter=delimiter)
                        rows = list(reader)
                    expected_flattened = []
                    for record in json_data:
                        expected_flattened.append(
                            {
                                k: str(v) if v is not None else ""
                                for k, v in flatten_dict(record).items()
                            }
                        )
                    all_keys = set()
                    for r in expected_flattened:
                        all_keys.update(r.keys())
                    for r in expected_flattened:
                        for k in all_keys:
                            if k not in r:
                                r[k] = ""
                    self.assertEqual(len(rows), len(expected_flattened))
                    for actual_row, exp_row in zip(rows, expected_flattened):
                        normalized_actual = {
                            k: str(v) if v is not None else ""
                            for k, v in actual_row.items()
                        }
                        self.assertEqual(normalized_actual, exp_row)
                    if expected_raw is not None:
                        normalized_actual_raw = raw_content.replace("\r\n", "\n")
                        normalized_expected_raw = expected_raw.replace("\r\n", "\n")
                        self.assertEqual(
                            normalized_actual_raw.splitlines(),
                            normalized_expected_raw.splitlines(),
                        )

    def test_process_json_to_csv_errors(self):
        cases = [
            ("file_not_found", "non_existent_file.json", FileNotFoundError, None),
            ("malformed_json", "invalid_json_content", json.JSONDecodeError, "{"),
            (
                "invalid_json_root_type_int",
                "invalid_root_int",
                (TypeError, ValueError),
                "123",
            ),
            (
                "invalid_json_root_type_string",
                "invalid_root_string",
                (TypeError, ValueError),
                '"string"',
            ),
        ]
        for name, identifier, expected_exception, raw_content in cases:
            with self.subTest(case=name):
                with tempfile.TemporaryDirectory() as tmpdir:
                    input_path = os.path.join(tmpdir, "input.json")
                    output_path = os.path.join(tmpdir, "output.csv")
                    if raw_content is not None:
                        with open(input_path, "w", encoding="utf-8") as f:
                            f.write(raw_content)
                    else:
                        input_path = identifier
                    with self.assertRaises(expected_exception):
                        process_json_to_csv(input_path, output_path)
