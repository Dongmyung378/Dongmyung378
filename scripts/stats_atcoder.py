"""Parse official English AtCoder algorithm statistics without network access."""

from __future__ import annotations

import re
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

_FIELDS = {"Rank", "Rating", "Highest Rating", "Rated Matches"}
_UNRATED = "This user has not competed in a rated contest yet."
_NUMBER = r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)"


class _ProfileHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.active_types: list[str] = []
        self.tables: list[list[list[str]]] = []
        self.paragraphs: list[str] = []
        self._nav_seen = False
        self._in_nav = False
        self._active_li = False
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._paragraph: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "ul" and attributes.get("id") == "user-nav-tabs":
            self._nav_seen = self._in_nav = True
        elif self._in_nav and tag == "li":
            self._active_li = "active" in (attributes.get("class") or "").split()
        elif self._in_nav and self._active_li and tag == "a":
            query = parse_qs(urlsplit(attributes.get("href") or "").query)
            self.active_types.extend(query.get("contestType", []))
        elif self._nav_seen and not self._in_nav:
            if tag == "table":
                if self._table is not None:
                    raise ValueError("Nested AtCoder statistics tables")
                self._table = []
            elif tag == "tr" and self._table is not None:
                if self._row is not None or self._cell is not None:
                    raise ValueError("Unclosed AtCoder statistics row")
                self._row = []
            elif tag in {"th", "td"} and self._row is not None:
                if self._cell is not None:
                    raise ValueError("Unclosed AtCoder statistics cell")
                self._cell = []
            elif tag == "p":
                self._paragraph = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)
        if self._paragraph is not None:
            self._paragraph.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._in_nav:
            if tag == "li":
                self._active_li = False
            elif tag == "ul":
                self._in_nav = False
            return
        if tag in {"th", "td"} and self._cell is not None:
            if self._row is None:
                raise ValueError("AtCoder statistics cell outside a row")
            self._row.append(" ".join(" ".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._table is None or self._cell is not None:
                raise ValueError("Malformed AtCoder statistics row")
            self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            if self._row is not None or self._cell is not None:
                raise ValueError("Unclosed AtCoder statistics table content")
            self.tables.append(self._table)
            self._table = None
        elif tag == "p" and self._paragraph is not None:
            self.paragraphs.append(" ".join(" ".join(self._paragraph).split()))
            self._paragraph = None

    def statistics(self) -> dict[str, str] | None:
        if self.active_types != ["algo"]:
            raise ValueError("Expected exactly one active AtCoder Algorithm tab")
        if self._table is not None or self._row is not None or self._cell is not None:
            raise ValueError("Incomplete AtCoder statistics HTML")
        candidates = []
        for table in self.tables:
            if any(row and row[0] in _FIELDS for row in table):
                fields = {}
                for row in table:
                    if row and row[0] in _FIELDS:
                        if len(row) != 2 or row[0] in fields:
                            raise ValueError("Malformed or duplicate AtCoder field")
                        fields[row[0]] = row[1]
                if set(fields) != _FIELDS:
                    raise ValueError("Missing required AtCoder statistics field")
                candidates.append(fields)
        if len(candidates) > 1:
            raise ValueError("Ambiguous AtCoder statistics tables")
        if candidates:
            if _UNRATED in self.paragraphs:
                raise ValueError("Conflicting rated and unrated AtCoder profile")
            return candidates[0]
        if _UNRATED in self.paragraphs:
            return None
        raise ValueError("AtCoder statistics or explicit unrated state not found")


def _integer(value: object, field: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"Invalid AtCoder {field}")
    return value


def _number_text(value: str, field: str) -> int:
    if not re.fullmatch(_NUMBER, value):
        raise ValueError(f"Invalid AtCoder {field}")
    return int(value.replace(",", ""))


def _rated_history(history: list) -> list[tuple[datetime, dict, int, str]]:
    if not isinstance(history, list):
        raise ValueError("AtCoder history must be a JSON list")  # noqa: TRY004 - parser failure contract
    results = []
    contests = set()
    for record in history:
        if not isinstance(record, dict) or not isinstance(record.get("IsRated"), bool):
            raise ValueError("Invalid AtCoder history rated flag")  # noqa: TRY004 - parser failure contract
        if not record["IsRated"]:
            continue
        try:
            end_time = datetime.fromisoformat(record["EndTime"].replace("Z", "+00:00"))  # noqa: FURB162 - Python 3.10 compatibility
        except (KeyError, TypeError, AttributeError, ValueError) as error:
            raise ValueError("Invalid AtCoder contest time") from error
        if end_time.utcoffset() is None:
            raise ValueError("AtCoder contest time must include its timezone")
        rating = _integer(record.get("NewRating"), "new rating")
        old_rating = _integer(record.get("OldRating"), "old rating")
        place = record.get("Place")
        if place is not None:
            _integer(place, "contest place", 1)
        screen_name = record.get("ContestScreenName")
        if not isinstance(screen_name, str):
            raise ValueError("Missing AtCoder contest identifier")  # noqa: TRY004 - parser failure contract
        match = re.fullmatch(r"([a-z0-9_-]+)(?:\.contest\.atcoder\.jp)?", screen_name)
        if not match or match[1] in contests:
            raise ValueError("Invalid or duplicate AtCoder contest identifier")
        contest_id = match[1]
        contests.add(contest_id)
        name = record.get("ContestNameEn") or record.get("ContestName")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Missing AtCoder contest name")
        results.append(
            (
                end_time,
                {
                    "date": end_time.date().isoformat(),
                    "rating": rating,
                    "contest": name.strip(),
                    "place": place,
                },
                old_rating,
                contest_id,
            )
        )
    results.sort(key=lambda item: item[0])
    previous_rating = 0
    for _, record, old_rating, _ in results:
        if old_rating != previous_rating:
            raise ValueError("AtCoder history rating chain does not match")
        previous_rating = record["rating"]
    return results


def parse_atcoder(profile_html: str, history: list) -> dict:
    """Return checked algorithm statistics; reject missing or conflicting data.

    The HTML must be the official English profile with Algorithm selected.
    History must come from the matching algorithm history/json endpoint.
    Unrated is represented by None, while a genuinely rated zero remains 0.
    """
    if not isinstance(profile_html, str) or not profile_html.strip():
        raise ValueError("AtCoder profile HTML is empty")
    parser = _ProfileHTML()
    parser.feed(profile_html)
    parser.close()
    fields = parser.statistics()
    rated = _rated_history(history)
    empty = {
        "rating": None,
        "highest_rating": None,
        "rank": None,
        "rated_contests": 0,
        "provisional": False,
        "history": [],
        "latest_contest_url": None,
    }
    if fields is None:
        if rated:
            raise ValueError("Unrated AtCoder profile has rated history")
        return empty
    count = _number_text(fields["Rated Matches"], "rated match count")
    if count != len(rated):
        raise ValueError("AtCoder rated match count differs from history")
    if count == 0:
        if any(
            fields[key] not in {"-", "―", "—"} for key in _FIELDS - {"Rated Matches"}
        ):
            raise ValueError("Zero-match AtCoder profile contains numeric ratings")
        return empty
    current = re.fullmatch(
        r"(" + _NUMBER + r")(?:\s*\(Provisional\s*\))?", fields["Rating"]
    )
    peak = re.fullmatch(
        r"(" + _NUMBER + r")(?:\s*[―—−-]\s*[0-9]+\s+(?:Kyu|Dan))?(?:\s+New!!)?",
        fields["Highest Rating"],
    )
    rank = re.fullmatch(
        r"(" + _NUMBER + r")(?:st|nd|rd|th)?(?:\s*\(Top\s+([0-9]+(?:\.[0-9]+)?)%\))?",
        fields["Rank"],
    )
    if not current or not peak or not rank:
        raise ValueError("Missing or invalid numeric AtCoder profile statistic")
    rating = _number_text(current[1], "rating")
    highest = _number_text(peak[1], "highest rating")
    rank_number = _number_text(rank[1], "rank")
    if rank_number == 0:
        raise ValueError("AtCoder rank must be positive")
    if rating != rated[-1][1]["rating"] or highest != max(
        item[1]["rating"] for item in rated
    ):
        raise ValueError("AtCoder profile ratings differ from history")
    result = {
        "rating": rating,
        "highest_rating": highest,
        "rank": rank_number,
        "rated_contests": count,
        "provisional": "Provisional" in fields["Rating"],
        "history": [item[1] for item in rated],
        "latest_contest_url": "https://atcoder.jp/contests/" + rated[-1][3],
    }
    if rank[2] is not None:
        top_percent = float(rank[2])
        if not 0 <= top_percent <= 100:
            raise ValueError("AtCoder top percentage is out of range")
        result["top_percent"] = top_percent
    return result
