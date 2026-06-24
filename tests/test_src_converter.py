import unittest
import tempfile
import os
import json
from json import JSONDecodeError

try:
    import ijson

    IJSON_ERRORS = (ijson.common.JSONError,)
except ImportError:
    IJSON_ERRORS = ()
from src.converter import flatten_dict, serialize_primitive_array, process_json_to_csv


class TestConverter(unittest.TestCase):
    def test_flatten_dict_acceptance_and_success(self):
        cases = [
            ("basic_nesting", {"a": 1, "b": {"c": 2}}, "", ".", {"a": 1, "b.c": 2}),
            ("deep_nesting", {"a": {"b": {"c": 3}}}, "", ".", {"a.b.c": 3}),
            ("custom_sep", {"a": {"b": 4}}, "", "_", {"a_b": 4}),
            ("custom_prefix", {"a": {"b": 4}}, "prefix", "_", {"prefix_a_b": 4}),
            ("empty_dict", {}, "", ".", {}),
            ("none_values", {"a": None}, "", ".", {"a": None}),
            ("boolean_and_numbers", {"a": True, "b": 1}, "", ".", {"a": True, "b": 1}),
        ]
        for name, data, parent_key, sep, expected in cases:
            with self.subTest(case=name):
                self.assertEqual(flatten_dict(data, parent_key, sep), expected)

    def test_flatten_dict_exceptions(self):
        cases = [
            (
                "acceptance_collision",
                {"a": 1, "b.c": 2, "b": {"c": 3}},
                "",
                ".",
                ValueError,
            ),
            ("collision_nested_first", {"b": {"c": 3}, "b.c": 2}, "", ".", ValueError),
            ("non_dict_int", 123, "", ".", TypeError),
            ("non_dict_list", [1, 2], "", ".", TypeError),
            ("non_dict_bool", True, "", ".", TypeError),
            ("non_dict_str", "string", "", ".", TypeError),
            ("non_dict_none", None, "", ".", TypeError),
            ("invalid_parent_key_type", {"a": 1}, 123, ".", TypeError),
            ("invalid_sep_type", {"a": 1}, "", 1.5, TypeError),
        ]
        for name, data, parent_key, sep, expected_exc in cases:
            with self.subTest(case=name):
                with self.assertRaises(expected_exc):
                    flatten_dict(data, parent_key, sep)

    def test_serialize_primitive_array_acceptance_and_success(self):
        cases = [
            (
                "acceptance_example",
                [1, "hello", True, None],
                "[1, 'hello', True, None]",
            ),
            ("integers_and_booleans", [1, True, False, 0], "[1, True, False, 0]"),
            ("empty_list", [], "[]"),
            ("floats", [1.5, -2.5], "[1.5, -2.5]"),
        ]
        for name, array_data, expected in cases:
            with self.subTest(case=name):
                res = serialize_primitive_array(array_data)
                self.assertEqual(res, expected)

    def test_serialize_primitive_array_distinguish_bool_from_int(self):
        res_bool = serialize_primitive_array([True, False])
        res_int = serialize_primitive_array([1, 0])
        self.assertNotEqual(res_bool, res_int)
        self.assertTrue("True" in res_bool or "true" in res_bool)
        self.assertIn("1", res_int)

    def test_serialize_primitive_array_exceptions(self):
        cases = [
            ("nested_list_acceptance", [1, [2, 3]], TypeError),
            ("nested_dict", [1, {"a": 2}], TypeError),
            ("non_list_dict", {"a": 1}, TypeError),
            ("non_list_str", "not_a_list", TypeError),
            ("non_list_int", 42, TypeError),
            ("non_list_bool", True, TypeError),
            ("non_list_none", None, TypeError),
            ("list_with_complex_object", [object()], TypeError),
        ]
        for name, array, expected_exc in cases:
            with self.subTest(case=name):
                with self.assertRaises(expected_exc):
                    serialize_primitive_array(array)

    def test_process_json_to_csv_success(self):
        cases = [
            (
                "flat_records",
                [{"a": 1, "b": 2}, {"a": 3, "b": 4}],
                ",",
                "a,b\r\n1,2\r\n3,4\r\n",
            ),
            ("custom_delimiter", [{"a": 1, "b": 2}], ";", "a;b\r\n1;2\r\n"),
            ("nested_records", [{"a": 1, "b": {"c": 2}}], ",", "a,b.c\r\n1,2\r\n"),
            ("heterogeneous_fields", [{"a": 1}, {"b": 2}], ",", "a,b\r\n1,\r\n,2\r\n"),
            (
                "primitive_arrays_serialization",
                [{"a": [1, True, None]}],
                ",",
                'a\r\n"[1, True, None]"\r\n',
            ),
        ]
        for name, json_data, delimiter, expected_csv in cases:
            with self.subTest(case=name):
                with tempfile.TemporaryDirectory() as tmpdir:
                    in_path = os.path.join(tmpdir, "in.json")
                    out_path = os.path.join(tmpdir, "out.csv")
                    with open(in_path, "w", encoding="utf-8") as f:
                        json.dump(json_data, f)

                    process_json_to_csv(in_path, out_path, delimiter=delimiter)

                    self.assertTrue(os.path.exists(out_path))
                    with open(out_path, "r", newline="", encoding="utf-8") as f:
                        content = f.read()

                    content_lines = content.replace("\r\n", "\n").strip().splitlines()
                    expected_lines = (
                        expected_csv.replace("\r\n", "\n").strip().splitlines()
                    )
                    self.assertEqual(content_lines, expected_lines)

    def test_process_json_to_csv_exceptions(self):
        allowed_syntax_errors = (JSONDecodeError,) + IJSON_ERRORS
        cases = [
            ("non_existent_file", "non_existent.json", (FileNotFoundError,), None),
            ("non_array_root_object", "dummy.json", (ValueError,), '{"a": 1}'),
            ("non_array_root_string", "dummy.json", (ValueError,), '"hello"'),
            ("non_array_root_int", "dummy.json", (ValueError,), "42"),
            (
                "malformed_json_syntax_error",
                "dummy.json",
                allowed_syntax_errors,
                '{"a": ',
            ),
            ("empty_file_syntax_error", "dummy.json", allowed_syntax_errors, ""),
        ]
        for name, filename, expected_excs, raw_content in cases:
            with self.subTest(case=name):
                with tempfile.TemporaryDirectory() as tmpdir:
                    in_path = (
                        os.path.join(tmpdir, filename)
                        if raw_content is not None
                        else filename
                    )
                    out_path = os.path.join(tmpdir, "out.csv")

                    if raw_content is not None:
                        with open(in_path, "w", encoding="utf-8") as f:
                            f.write(raw_content)

                    with self.assertRaises(expected_excs):
                        process_json_to_csv(in_path, out_path)
