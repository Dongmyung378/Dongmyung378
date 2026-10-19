"""Validate the public LeetCode response without inventing unavailable statistics."""

import calendar
import math


GRAPHQL_QUERY = """
query ProfileStatistics($username: String!, $year: Int!) {
  matchedUser(username: $username) {
    username
    profile { ranking }
    submitStatsGlobal { acSubmissionNum { difficulty count } }
    userCalendar(year: $year) { totalActiveDays }
  }
  userContestRanking(username: $username) {
    attendedContestsCount
    rating
    globalRanking
    topPercentage
  }
}
""".strip()


def _object(value, path: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be an object")
    return value


def _field(value: dict, key: str, path: str):
    if key not in value:
        raise ValueError(f"{path}.{key} is missing")
    return value[key]


def _integer(value, path: str, *, nullable: bool = False) -> int | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{path} must be a nonnegative integer")
    return value


def _number(value, path: str, *, maximum: float | None = None) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path} must be a finite nonnegative number or null")
    try:
        number = float(value)
    except (ValueError, OverflowError) as error:
        raise ValueError(f"{path} must be a finite number") from error
    if not math.isfinite(number) or number < 0 or (maximum is not None and number > maximum):
        raise ValueError(f"{path} is outside its valid numeric range")
    return number


def parse_leetcode(payload: dict, username: str, year: int) -> dict:
    """Return a normalized snapshot; missing or invalid source fields are errors.

    A null contest object means no contest rating/rank is available. It is
    distinct from an explicit numeric zero. The problem-solving profile rank is
    preserved separately from the contest rank, including any source sentinel.
    """
    if not isinstance(username, str) or not username or username != username.strip():
        raise ValueError("username must be a nonempty account name without surrounding whitespace")
    if isinstance(year, bool) or not isinstance(year, int) or not 1 <= year <= 9999:
        raise ValueError("year must be an integer from 1 to 9999")
    payload = _object(payload, "response")
    errors = payload.get("errors")
    if errors is not None and (not isinstance(errors, list) or errors):
        raise ValueError("LeetCode returned GraphQL errors")
    data = _object(_field(payload, "data", "response"), "data")
    user = _object(_field(data, "matchedUser", "data"), "matchedUser")
    if _field(user, "username", "matchedUser") != username:
        raise ValueError("LeetCode returned a different account")

    profile = _object(_field(user, "profile", "matchedUser"), "profile")
    profile_rank = _integer(_field(profile, "ranking", "profile"), "profile.ranking", nullable=True)
    stats = _object(_field(user, "submitStatsGlobal", "matchedUser"), "submitStatsGlobal")
    entries = _field(stats, "acSubmissionNum", "submitStatsGlobal")
    if not isinstance(entries, list):
        raise ValueError("acSubmissionNum must be a list")
    counts = {}
    labels = {"All", "Easy", "Medium", "Hard"}
    for item in entries:
        item = _object(item, "acSubmissionNum entry")
        label = _field(item, "difficulty", "acSubmissionNum entry")
        if not isinstance(label, str) or label not in labels or label in counts:
            raise ValueError("acSubmissionNum has an unknown or duplicate difficulty")
        counts[label] = _integer(_field(item, "count", "acSubmissionNum entry"), f"{label}.count")
    if set(counts) != labels:
        raise ValueError("acSubmissionNum must include All, Easy, Medium and Hard")
    difficulty = {label: counts[label] for label in ("Easy", "Medium", "Hard")}
    if counts["All"] != sum(difficulty.values()):
        raise ValueError("All accepted-problem count does not match the difficulty total")

    activity = _object(_field(user, "userCalendar", "matchedUser"), "userCalendar")
    active_days = _integer(_field(activity, "totalActiveDays", "userCalendar"), "totalActiveDays")
    if active_days > (366 if calendar.isleap(year) else 365):
        raise ValueError("totalActiveDays exceeds the number of days in the requested year")

    raw_contest = _field(data, "userContestRanking", "data")
    contest = {"rating": None, "rank": None, "attended": 0, "top_percent": None}
    if raw_contest is not None:
        raw_contest = _object(raw_contest, "userContestRanking")
        contest = {
            "rating": _number(_field(raw_contest, "rating", "userContestRanking"), "contest.rating"),
            "rank": _integer(
                _field(raw_contest, "globalRanking", "userContestRanking"), "contest.rank", nullable=True
            ),
            "attended": _integer(
                _field(raw_contest, "attendedContestsCount", "userContestRanking"), "contest.attended"
            ),
            "top_percent": _number(
                _field(raw_contest, "topPercentage", "userContestRanking"),
                "contest.top_percent", maximum=100,
            ),
        }
    return {
        "solved": counts["All"],
        "difficulty": difficulty,
        "profile_rank": profile_rank,
        "active_days": active_days,
        "activity_year": year,
        "contest": contest,
    }
