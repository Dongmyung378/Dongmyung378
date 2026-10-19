"""Small official-table fixtures and strict cross-source consistency checks."""

import copy
import unittest

from scripts.stats_atcoder import parse_atcoder

# Statistics-only excerpts from ParkDM's official English profile, 2026-10-19.
NAV = """<ul id="user-nav-tabs" class="nav nav-tabs">
<li class="active"><a href="/users/ParkDM?contestType=algo">Algorithm</a></li>
<li class=""><a href="/users/ParkDM?contestType=heuristic">Heuristic</a></li>
</ul>"""
TABLE = """<table class="dl-table mt-2">
<tr><th class="no-break">Rank</th><td>45059th <span class="gray">(Top 35.64%)</span></td></tr>
<tr><th class="no-break">Rating</th><td><span class="user-gray">266</span>
<span class="bold small">(Provisional<span class="glyphicon glyphicon-question-sign"></span>)</span></td></tr>
<tr><th class="no-break">Highest Rating</th><td><span class="user-gray">266</span>
<span class="gray">―</span><span class="bold">9 Kyu</span></td></tr>
<tr><th class="no-break">Rated Matches <span class="glyphicon glyphicon-question-sign"></span></th><td>4</td></tr>
<tr><th class="no-break">Last Competed</th><td>2026/10/17</td></tr>
</table>"""
PROFILE = NAV + TABLE
# The official unrated state uses this paragraph instead of a numeric table.
UNRATED = NAV + "<p>This user has not competed in a rated contest yet.</p>"
HISTORY = [
    {
        "IsRated": True,
        "OldRating": 0,
        "NewRating": 2,
        "Place": 10031,
        "ContestScreenName": "abc477.contest.atcoder.jp",
        "ContestName": "ABC 477",
        "ContestNameEn": "UNICORNProgramming Contest2026(AtCoder Beginner Contest 477)",
        "EndTime": "2026-09-26T22:40:00+09:00",
    },
    {
        "IsRated": True,
        "OldRating": 2,
        "NewRating": 102,
        "Place": 3382,
        "ContestScreenName": "abc478.contest.atcoder.jp",
        "ContestName": "AtCoder Beginner Contest 478",
        "ContestNameEn": "",
        "EndTime": "2026-10-03T22:40:00+09:00",
    },
    {
        "IsRated": True,
        "OldRating": 102,
        "NewRating": 93,
        "Place": 7341,
        "ContestScreenName": "abc479.contest.atcoder.jp",
        "ContestName": "ABC 479",
        "ContestNameEn": "AtCoder Beginner Contest 479",
        "EndTime": "2026-10-11T22:40:00+09:00",
    },
    {
        "IsRated": True,
        "OldRating": 93,
        "NewRating": 266,
        "Place": 2796,
        "ContestScreenName": "abc480.contest.atcoder.jp",
        "ContestName": "ABC 480",
        "ContestNameEn": "AtCoder Beginner Contest 480",
        "EndTime": "2026-10-17T22:40:00+09:00",
    },
]


class AtCoderStatisticsTests(unittest.TestCase):
    def test_official_rated_provisional_profile_matches_history(self):
        result = parse_atcoder(PROFILE, HISTORY)
        self.assertEqual(
            (result["rating"], result["highest_rating"], result["rank"]),
            (266, 266, 45059),
        )
        self.assertEqual(result["rated_contests"], 4)
        self.assertTrue(result["provisional"])
        self.assertEqual(result["top_percent"], 35.64)
        self.assertEqual(
            result["latest_contest_url"], "https://atcoder.jp/contests/abc480"
        )
        self.assertEqual(
            result["history"][-1],
            {
                "date": "2026-10-17",
                "rating": 266,
                "contest": "AtCoder Beginner Contest 480",
                "place": 2796,
            },
        )

    def test_history_is_chronological_and_unrated_entries_do_not_count(self):
        history = [HISTORY[3], {"IsRated": False}, HISTORY[1], HISTORY[0], HISTORY[2]]
        result = parse_atcoder(PROFILE, history)
        self.assertEqual(
            [row["rating"] for row in result["history"]], [2, 102, 93, 266]
        )
        self.assertEqual(
            [row["date"] for row in result["history"]],
            [
                "2026-09-26",
                "2026-10-03",
                "2026-10-11",
                "2026-10-17",
            ],
        )
        self.assertEqual(
            result["history"][1]["contest"], "AtCoder Beginner Contest 478"
        )

    def test_explicit_unrated_state_has_none_instead_of_zero(self):
        self.assertEqual(
            parse_atcoder(UNRATED, []),
            {
                "rating": None,
                "highest_rating": None,
                "rank": None,
                "rated_contests": 0,
                "provisional": False,
                "history": [],
                "latest_contest_url": None,
            },
        )

    def test_numeric_zero_remains_a_real_rated_value(self):
        table = TABLE.replace(">266<", ">0<").replace("<td>4</td>", "<td>1</td>")
        history = [dict(HISTORY[0], NewRating=0)]
        result = parse_atcoder(NAV + table, history)
        self.assertEqual(result["rating"], 0)
        self.assertEqual(result["highest_rating"], 0)
        self.assertEqual(result["rated_contests"], 1)

    def test_heuristic_tab_is_rejected_even_with_a_plausible_table(self):
        heuristic_nav = NAV.replace('class="active"', 'class=""', 1).replace(
            '<li class=""><a href="/users/ParkDM?contestType=heuristic">',
            '<li class="active"><a href="/users/ParkDM?contestType=heuristic">',
        )
        with self.assertRaises(ValueError):
            parse_atcoder(heuristic_nav + TABLE, HISTORY)

    def test_unrelated_earlier_table_cannot_override_algorithm_statistics(self):
        unrelated = TABLE.replace(">266<", ">1500<")
        self.assertEqual(parse_atcoder(unrelated + PROFILE, HISTORY)["rating"], 266)

    def test_incomplete_or_ambiguous_html_is_not_zero_statistics(self):
        invalid = [
            "",
            "<html>Service unavailable</html>",
            TABLE,
            PROFILE.replace("</table>", ""),
            PROFILE + TABLE,
            PROFILE.replace("</td></tr>", "</tr></td>", 1),
            PROFILE.replace("<td>4</td>", "<td></td>"),
            PROFILE.replace(">266<", ">-<", 1),
            PROFILE.replace("Highest Rating", "Missing Rating"),
        ]
        for profile in invalid:
            with self.subTest(profile=profile[:80]), self.assertRaises(ValueError):
                parse_atcoder(profile, HISTORY)

    def test_profile_history_mismatches_raise(self):
        invalid = [
            PROFILE.replace("<td>4</td>", "<td>5</td>"),
            PROFILE.replace(">266<", ">267<", 1),
            PROFILE.replace(
                '266</span>\n<span class="gray">―', '300</span>\n<span class="gray">―'
            ),
            UNRATED,
        ]
        for profile in invalid:
            with self.subTest(profile=profile[:80]), self.assertRaises(ValueError):
                parse_atcoder(profile, HISTORY)
        history = copy.deepcopy(HISTORY)
        history[2]["OldRating"] = 100
        with self.assertRaises(ValueError):
            parse_atcoder(PROFILE, history)

    def test_invalid_history_fields_and_duplicate_contests_raise(self):
        mutations = {
            "IsRated": 1,
            "NewRating": None,
            "OldRating": False,
            "Place": 0,
            "EndTime": "2026-10-17",
            "ContestNameEn": 42,
            "ContestScreenName": "https://example.org/untrusted",
        }
        for field, value in mutations.items():
            history = copy.deepcopy(HISTORY)
            history[-1][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                parse_atcoder(PROFILE, history)
        with self.assertRaises(ValueError):
            parse_atcoder(PROFILE, HISTORY + [HISTORY[0]])
        with self.assertRaises(ValueError):
            parse_atcoder(PROFILE, {})

    def test_missing_optional_place_and_percentage_are_explicit(self):
        history = copy.deepcopy(HISTORY)
        history[-1].pop("Place")
        profile = PROFILE.replace('<span class="gray">(Top 35.64%)</span>', "")
        result = parse_atcoder(profile, history)
        self.assertIsNone(result["history"][-1]["place"])
        self.assertNotIn("top_percent", result)


if __name__ == "__main__":
    unittest.main()
