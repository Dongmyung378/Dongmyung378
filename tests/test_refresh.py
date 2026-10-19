import copy
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from update_coding_stats import refresh
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

    def test_large_profile_rank_is_a_lower_bound_not_a_contest_rank(self):
        self.assertEqual(profile_rank(5_000_001), "5M+")
        self.assertEqual(profile_rank(10), "#10")
        self.assertEqual(profile_rank(None), "Unavailable")


if __name__ == "__main__":
    unittest.main()
