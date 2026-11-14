import copy
import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from update_coding_stats import refresh
import update_coding_stats
from stats_render import profile_rank, render_cards


class RefreshTests(unittest.TestCase):
    def test_partial_failure_preserves_previous_values_and_timestamp(self):
        old = {"atcoder": {"rating": 123, "updated_at": "2026-10-18T00:00:00Z"}, "leetcode": {"solved": 12, "updated_at": "2026-10-18T00:00:00Z"}}
        before = copy.deepcopy(old)
        def fail():
            raise ValueError("upstream schema changed")
        records, errors = refresh(old, {"atcoder": fail, "leetcode": lambda: {"solved": 16}}, "2026-10-19T00:00:00Z")
        self.assertEqual(records["atcoder"], old["atcoder"])
        self.assertEqual(records["leetcode"], {"solved": 16, "updated_at": "2026-10-19T00:00:00Z"})
        self.assertEqual(list(errors), ["atcoder"])
        self.assertEqual(old, before)

    def test_total_failure_does_not_publish_a_new_date(self):
        def fail():
            raise ConnectionError("unavailable")
        with self.assertRaisesRegex(RuntimeError, "left unchanged"):
            refresh({"atcoder": {}, "leetcode": {}}, {"atcoder": fail, "leetcode": fail}, "new date")

    def test_first_snapshot_requires_both_sources(self):
        def fail():
            raise ConnectionError("unavailable")
        with self.assertRaisesRegex(RuntimeError, "Initial"):
            refresh({}, {"atcoder": fail, "leetcode": lambda: {"solved": 0}}, "new date")

    def test_successful_zero_values_remain_real_zero_values(self):
        records, errors = refresh({}, {"atcoder": lambda: {"rating": 0}, "leetcode": lambda: {"solved": 0}}, "now")
        self.assertEqual(records["atcoder"]["rating"], 0)
        self.assertEqual(records["leetcode"]["solved"], 0)
        self.assertEqual(errors, {})

    def test_partial_refresh_is_published_but_returns_failure_status(self):
        old = {"atcoder": {"rating": 330, "updated_at": "2026-11-07T04:27:25Z"},
               "leetcode": {"solved": 25, "updated_at": "2026-11-07T04:27:25Z"}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "data" / "coding-stats.json").write_text(
                json.dumps({"profiles": old}), encoding="utf-8"
            )
            with patch.object(update_coding_stats, "ROOT", root), \
                 patch.object(update_coding_stats, "fetch_atcoder", side_effect=ValueError("changed profile")), \
                 patch.object(update_coding_stats, "fetch_leetcode", return_value={"solved": 26}), \
                 patch.object(update_coding_stats, "write_outputs") as publish, \
                 patch.object(sys, "argv", ["update_coding_stats.py"]), \
                 contextlib.redirect_stdout(io.StringIO()), \
                 contextlib.redirect_stderr(io.StringIO()) as errors:
                self.assertEqual(update_coding_stats.main(), 1)
            published = publish.call_args.args[1]
            self.assertEqual(published["atcoder"], old["atcoder"])
            self.assertEqual(published["leetcode"]["solved"], 26)
            self.assertNotEqual(published["leetcode"]["updated_at"], old["leetcode"]["updated_at"])
            self.assertIn("retained the last successful values and date", errors.getvalue())

    def test_complete_refresh_returns_success_status(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(update_coding_stats, "ROOT", Path(directory)), \
                 patch.object(update_coding_stats, "fetch_atcoder", return_value={"rating": 543}), \
                 patch.object(update_coding_stats, "fetch_leetcode", return_value={"solved": 26}), \
                 patch.object(update_coding_stats, "write_outputs") as publish, \
                 patch.object(sys, "argv", ["update_coding_stats.py"]), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(update_coding_stats.main(), 0)
            self.assertEqual(publish.call_args.args[1]["atcoder"]["rating"], 543)

    def test_large_profile_rank_is_a_lower_bound_not_a_contest_rank(self):
        self.assertEqual(profile_rank(5_000_001), "5M+")
        self.assertEqual(profile_rank(10), "#10")
        self.assertEqual(profile_rank(None), "Unavailable")


if __name__ == "__main__":
    unittest.main()
