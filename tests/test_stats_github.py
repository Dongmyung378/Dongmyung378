import copy
from datetime import date
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from stats_github import aggregate_languages, parse_calendar, streaks
from stats_github_render import render_cards
import update_github_stats


class GitHubStatsTests(unittest.TestCase):
    def test_calendar_counts_zero_one_and_thousands(self):
        html=''.join(
            f'<td id="d{i}" data-date="2026-01-0{i}"></td><tool-tip for="d{i}">{label} on January {i}.</tool-tip>'
            for i,label in enumerate(["No contributions","1 contribution","1,024 contributions"],1))
        self.assertEqual(parse_calendar(html,date(2026,1,1),date(2026,1,3)),
                         {"2026-01-01":0,"2026-01-02":1,"2026-01-03":1024})

    def test_incomplete_calendar_is_not_silently_filled_with_zeros(self):
        with self.assertRaisesRegex(ValueError,"Incomplete"):
            parse_calendar("",date(2026,1,1),date(2026,1,3))

    def test_missing_count_tooltip_rejects_snapshot(self):
        with self.assertRaisesRegex(ValueError,"count is missing"):
            parse_calendar('<td data-date="2026-01-01" id="d1"></td>',date(2026,1,1),date(2026,1,1))

    def test_current_streak_survives_unfinished_utc_day(self):
        result=streaks({"2026-01-01":2,"2026-01-02":1,"2026-01-03":0},date(2026,1,3))
        self.assertEqual(result["current"],2)
        self.assertEqual(result["current_end"],"2026-01-02")

    def test_streak_break_and_longest_are_separate(self):
        result=streaks({"2026-01-01":1,"2026-01-02":1,"2026-01-03":0,"2026-01-04":0},date(2026,1,4))
        self.assertEqual(result["current"],0)
        self.assertEqual(result["longest"],2)
        self.assertEqual(result["longest_start"],"2026-01-01")

    def test_streak_crosses_year_and_includes_today(self):
        result=streaks({"2025-12-31":1,"2026-01-01":3},date(2026,1,1))
        self.assertEqual(result["current"],2)
        self.assertEqual(result["longest"],2)

    def test_missing_day_does_not_join_two_runs(self):
        result=streaks({"2026-01-01":1,"2026-01-03":1},date(2026,1,3))
        self.assertEqual(result["longest"],1)

    @staticmethod
    def repository():
        return {"isPrivate":False,"isFork":False,"languages":{"totalSize":100,"pageInfo":{"hasNextPage":False},
                "edges":[{"size":75,"node":{"name":"Python","color":"#3572A5"}},{"size":25,"node":{"name":"C++","color":"#f34b7d"}}]}}

    def test_language_percentages_use_bytes(self):
        values=aggregate_languages([self.repository()])
        self.assertEqual([(x["name"],x["percent"]) for x in values],[("Python",75),("C++",25)])

    def test_private_or_incomplete_language_input_is_rejected(self):
        for kind in ("private","truncated","mismatch"):
            repo=self.repository()
            if kind=="private":repo["isPrivate"]=True
            elif kind=="truncated":repo["languages"]["pageInfo"]["hasNextPage"]=True
            else:repo["languages"]["totalSize"]=101
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                aggregate_languages([repo])

    def test_fetch_failure_preserves_every_existing_byte(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/"README.md").write_text("existing profile")
            (root/"data").mkdir()
            (root/"data/github-stats.json").write_text('{"old":"snapshot"}')
            before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob("*") if p.is_file()}
            with patch.object(update_github_stats,"ROOT",root),patch.object(update_github_stats,"fetch_github",side_effect=ConnectionError),patch.object(sys,"argv",["update_github_stats.py"]):
                self.assertEqual(update_github_stats.main(),1)
            self.assertEqual(before,{str(p.relative_to(root)):p.read_bytes() for p in root.rglob("*") if p.is_file()})

    def test_generated_cards_are_valid_xml_for_empty_languages_and_zero_activity(self):
        record={"username":"Dongmyung378","updated_at":"2026-01-02T00:00:00Z","created_at":"2026-01-01",
                "active_days":0,"stars":0,"commits":0,"pull_requests":0,"issues":0,"repositories_committed_to":0,
                "total_contributions":0,"public_repositories":0,"languages":[],
                "streaks":streaks({"2026-01-01":0,"2026-01-02":0},date(2026,1,2))}
        for name,svg in render_cards(record).items():
            with self.subTest(name=name):
                ET.fromstring(svg)
                self.assertNotIn("nan",svg.lower())


if __name__=="__main__":
    unittest.main()
