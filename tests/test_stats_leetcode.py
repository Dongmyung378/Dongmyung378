"""Contract tests using a minimal official public response observed 2026-10-19."""

from copy import deepcopy
from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from stats_leetcode import parse_leetcode


OFFICIAL_RESPONSE = {
    "data": {
        "matchedUser": {
            "username": "Dongmyung",
            "profile": {"ranking": 5000001},
            "submitStatsGlobal": {
                "acSubmissionNum": [
                    {"difficulty": "All", "count": 16},
                    {"difficulty": "Easy", "count": 0},
                    {"difficulty": "Medium", "count": 16},
                    {"difficulty": "Hard", "count": 0},
                ]
            },
            "userCalendar": {"totalActiveDays": 5},
        },
        "userContestRanking": None,
    }
}


class LeetCodeParserTests(unittest.TestCase):
    def test_official_snapshot_preserves_problem_rank_and_unrated_contest(self):
        payload = deepcopy(OFFICIAL_RESPONSE)
        self.assertEqual(parse_leetcode(payload, "Dongmyung", 2026), {
            "solved": 16, "difficulty": {"Easy": 0, "Medium": 16, "Hard": 0},
            "profile_rank": 5000001, "active_days": 5, "activity_year": 2026,
            "contest": {"rating": None, "rank": None, "attended": 0, "top_percent": None},
        })
        self.assertEqual(payload, OFFICIAL_RESPONSE)

    def test_rated_contest_is_separate_from_problem_rank(self):
        payload = deepcopy(OFFICIAL_RESPONSE)
        payload["data"]["userContestRanking"] = {
            "rating": 1500.25, "globalRanking": 24000,
            "attendedContestsCount": 3, "topPercentage": 21.5,
        }
        result = parse_leetcode(payload, "Dongmyung", 2026)
        self.assertEqual(result["contest"], {
            "rating": 1500.25, "rank": 24000, "attended": 3, "top_percent": 21.5,
        })
        self.assertEqual(result["profile_rank"], 5000001)

    def test_explicit_zero_and_nullable_values_remain_distinct(self):
        payload = deepcopy(OFFICIAL_RESPONSE)
        user = payload["data"]["matchedUser"]
        user["profile"]["ranking"] = 0
        user["userCalendar"]["totalActiveDays"] = 0
        for entry in user["submitStatsGlobal"]["acSubmissionNum"]:
            entry["count"] = 0
        contest = {"rating": 0, "globalRanking": 0, "attendedContestsCount": 0, "topPercentage": 0}
        payload["data"]["userContestRanking"] = contest
        result = parse_leetcode(payload, "Dongmyung", 2026)
        self.assertEqual(result["solved"], 0)
        self.assertEqual(result["active_days"], 0)
        self.assertEqual(result["profile_rank"], 0)
        self.assertEqual(result["contest"], {"rating": 0.0, "rank": 0, "attended": 0, "top_percent": 0.0})
        user["profile"]["ranking"] = None
        contest.update(rating=None, globalRanking=None, topPercentage=None)
        result = parse_leetcode(payload, "Dongmyung", 2026)
        self.assertIsNone(result["profile_rank"])
        self.assertEqual(result["contest"], {"rating": None, "rank": None, "attended": 0, "top_percent": None})

    def test_graphql_errors_and_wrong_account_are_rejected(self):
        for errors in ([{"message": "rate limited"}], "failure", {"message": "failure"}):
            with self.subTest(errors=errors):
                payload = deepcopy(OFFICIAL_RESPONSE)
                payload["errors"] = errors
                with self.assertRaises(ValueError):
                    parse_leetcode(payload, "Dongmyung", 2026)
        for username in ("OtherAccount", "", None, 5):
            with self.subTest(username=username):
                payload = deepcopy(OFFICIAL_RESPONSE)
                payload["data"]["matchedUser"]["username"] = username
                with self.assertRaises(ValueError):
                    parse_leetcode(payload, "Dongmyung", 2026)

    def test_missing_or_null_schema_objects_and_fields_are_rejected(self):
        paths = [
            ("data",), ("data", "matchedUser"), ("data", "userContestRanking"),
            ("data", "matchedUser", "username"), ("data", "matchedUser", "profile"),
            ("data", "matchedUser", "profile", "ranking"),
            ("data", "matchedUser", "submitStatsGlobal"),
            ("data", "matchedUser", "submitStatsGlobal", "acSubmissionNum"),
            ("data", "matchedUser", "userCalendar"),
            ("data", "matchedUser", "userCalendar", "totalActiveDays"),
        ]
        for path in paths:
            with self.subTest(missing=path):
                payload = deepcopy(OFFICIAL_RESPONSE)
                parent = payload
                for key in path[:-1]:
                    parent = parent[key]
                del parent[path[-1]]
                with self.assertRaises(ValueError):
                    parse_leetcode(payload, "Dongmyung", 2026)
        for payload in (None, [], {}, {"data": None}, {"data": {"matchedUser": None}}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                parse_leetcode(payload, "Dongmyung", 2026)

    def test_invalid_difficulty_counts_and_inconsistent_totals_are_rejected(self):
        valid = OFFICIAL_RESPONSE["data"]["matchedUser"]["submitStatsGlobal"]["acSubmissionNum"]
        invalid_entries = [None, {}, [], valid[:-1], valid + [valid[0]],
                           [{"difficulty": "Unexpected", "count": 0}]]
        for value in (-1, True, 1.5, "16", None):
            entries = deepcopy(valid)
            entries[0]["count"] = value
            invalid_entries.append(entries)
        entries = deepcopy(valid)
        entries[0]["count"] = 17
        invalid_entries.append(entries)
        for entries in invalid_entries:
            with self.subTest(entries=entries):
                payload = deepcopy(OFFICIAL_RESPONSE)
                payload["data"]["matchedUser"]["submitStatsGlobal"]["acSubmissionNum"] = entries
                with self.assertRaises(ValueError):
                    parse_leetcode(payload, "Dongmyung", 2026)

    def test_invalid_profile_activity_and_request_values_are_rejected(self):
        for path, values in [
            (("profile", "ranking"), [-1, True, 1.5, "1"]),
            (("userCalendar", "totalActiveDays"), [-1, True, 1.5, "5", None, 366]),
        ]:
            for value in values:
                with self.subTest(path=path, value=value):
                    payload = deepcopy(OFFICIAL_RESPONSE)
                    payload["data"]["matchedUser"][path[0]][path[1]] = value
                    with self.assertRaises(ValueError):
                        parse_leetcode(payload, "Dongmyung", 2026)
        for username, year in [("", 2026), (None, 2026), (" Dongmyung", 2026),
                               ("Dongmyung", True), ("Dongmyung", 2026.0),
                               ("Dongmyung", 0), ("Dongmyung", 10000)]:
            with self.subTest(username=username, year=year), self.assertRaises(ValueError):
                parse_leetcode(OFFICIAL_RESPONSE, username, year)

    def test_invalid_or_missing_contest_metrics_are_rejected(self):
        valid = {"rating": 1500, "globalRanking": 1000, "attendedContestsCount": 2, "topPercentage": 10}
        cases = []
        for key in valid:
            missing = dict(valid)
            del missing[key]
            cases.append(missing)
        for key, values in [
            ("rating", [-1, True, "1500", float("nan"), float("inf"), 10 ** 1000]),
            ("globalRanking", [-1, True, 1.5, "1"]),
            ("attendedContestsCount", [-1, True, 1.5, None]),
            ("topPercentage", [-1, 100.01, True, float("nan"), float("inf")]),
        ]:
            for value in values:
                item = dict(valid)
                item[key] = value
                cases.append(item)
        for item in [[], "unrated", *cases]:
            with self.subTest(contest=item):
                payload = deepcopy(OFFICIAL_RESPONSE)
                payload["data"]["userContestRanking"] = item
                with self.assertRaises(ValueError):
                    parse_leetcode(payload, "Dongmyung", 2026)


if __name__ == "__main__":
    unittest.main()
