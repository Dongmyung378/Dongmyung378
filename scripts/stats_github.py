"""Collect public GitHub activity and language statistics without a card service."""
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
import json
import os
import re
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

USERNAME = "Dongmyung378"
QUERY = """
query ProfileStatistics($login:String!, $from:DateTime!, $to:DateTime!, $cursor:String) {
  user(login:$login) {
    login createdAt
    contributionsCollection(from:$from, to:$to) {
      totalRepositoriesWithContributedCommits
      commitContributionsByRepository(maxRepositories:100) {
        repository { isPrivate }
        contributions { totalCount }
      }
    }
    repositories(first:100, after:$cursor, privacy:PUBLIC, isFork:false, ownerAffiliations:OWNER) {
      totalCount pageInfo { hasNextPage endCursor }
      nodes {
        name isPrivate isFork stargazerCount
        languages(first:100, orderBy:{field:SIZE,direction:DESC}) {
          totalSize pageInfo { hasNextPage }
          edges { size node { name color } }
        }
      }
    }
  }
  pullRequests: search(type:ISSUE, query:"is:public is:pr author:Dongmyung378", first:1) { issueCount }
  issues: search(type:ISSUE, query:"is:public is:issue author:Dongmyung378", first:1) { issueCount }
}
"""


def token():
    value = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not value:
        result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError("GitHub authentication is unavailable")
        value = result.stdout.strip()
    if not value:
        raise RuntimeError("GitHub authentication is unavailable")
    return value


def request(url, payload=None, authorization=None):
    headers = {"User-Agent": "Dongmyung378-profile-statistics", "Accept": "application/json,text/html"}
    if authorization:
        headers["Authorization"] = f"Bearer {authorization}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
    body = None if payload is None else json.dumps(payload).encode()
    for attempt in range(3):
        try:
            with urlopen(Request(url, data=body, headers=headers), timeout=25) as response:
                return response.read().decode("utf-8")
        except HTTPError as exc:
            if attempt == 2 or exc.code not in (429, 500, 502, 503, 504):
                raise RuntimeError(f"GitHub request failed: HTTP {exc.code}") from None
        except (URLError, TimeoutError):
            if attempt == 2:
                raise RuntimeError("GitHub request failed: network unavailable") from None
        time.sleep(2**attempt)
    raise RuntimeError("GitHub retry limit reached")


class CalendarParser(HTMLParser):
    """Match contribution cells to their official count tooltips."""
    def __init__(self):
        super().__init__()
        self.cells = {}
        self.counts = {}
        self.tooltip = None
        self.text = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if attrs.get("data-date") and attrs.get("id"):
            self.cells[attrs["id"]] = attrs["data-date"]
        if tag == "tool-tip":
            self.tooltip = attrs.get("for")
            self.text = []

    def handle_data(self, value):
        if self.tooltip:
            self.text.append(value)

    def handle_endtag(self, tag):
        if tag == "tool-tip" and self.tooltip:
            text = "".join(self.text).strip()
            match = re.match(r"(No|[\d,]+) contributions?\b", text)
            if match:
                self.counts[self.tooltip] = 0 if match[1] == "No" else int(match[1].replace(",", ""))
            self.tooltip = None


def parse_calendar(html, start, end):
    parser = CalendarParser()
    parser.feed(html)
    days = {}
    for cell, day in parser.cells.items():
        current = date.fromisoformat(day)
        if start <= current <= end:
            if cell not in parser.counts:
                raise ValueError("GitHub calendar count is missing")
            if day in days:
                raise ValueError("Duplicate GitHub calendar day")
            days[day] = parser.counts[cell]
    required = (end-start).days+1
    if len(days) != required:
        raise ValueError(f"Incomplete public GitHub calendar: {len(days)}/{required} days")
    return days


def streaks(days, today):
    """Keep a streak through yesterday until the current UTC day is complete."""
    ordered = sorted((date.fromisoformat(day), count) for day, count in days.items())
    longest = run = 0
    previous = None
    run_start = longest_start = longest_end = None
    for day, count in ordered:
        if count:
            continuing = previous is not None and day == previous+timedelta(days=1) and run > 0
            run = run+1 if continuing else 1
            if not continuing:
                run_start = day
            if run > longest:
                longest, longest_start, longest_end = run, run_start, day
        else:
            run = 0
        previous = day
    end = today if days.get(today.isoformat(), 0) else today-timedelta(days=1)
    current = 0
    cursor = end
    while days.get(cursor.isoformat(), 0) > 0:
        current += 1
        cursor -= timedelta(days=1)
    return {
        "current": current,
        "current_start": (cursor+timedelta(days=1)).isoformat() if current else None,
        "current_end": end.isoformat() if current else None,
        "longest": longest,
        "longest_start": longest_start.isoformat() if longest_start else None,
        "longest_end": longest_end.isoformat() if longest_end else None,
    }


def aggregate_languages(repositories):
    counts, colors = Counter(), {}
    for repo in repositories:
        if repo["isPrivate"] or repo["isFork"]:
            raise ValueError("Language input must contain only public non-fork repositories")
        languages = repo["languages"]
        if languages["pageInfo"]["hasNextPage"]:
            raise ValueError("Repository language response is incomplete")
        if sum(edge["size"] for edge in languages["edges"]) != languages["totalSize"]:
            raise ValueError("Language byte totals do not match")
        for edge in languages["edges"]:
            name = edge["node"]["name"]
            counts[name] += edge["size"]
            colors[name] = edge["node"]["color"] or "#8DA2B8"
    total = sum(counts.values())
    return [{"name": name, "bytes": size, "percent": 100*size/total, "color": colors[name]}
            for name, size in sorted(counts.items(), key=lambda item: (-item[1], item[0]))] if total else []


def fetch_github(now=None):
    now = now or datetime.now(timezone.utc)
    today = now.date()
    period_start = today-timedelta(days=364)
    auth = token()
    variables = {"login": USERNAME, "from": period_start.isoformat()+"T00:00:00Z",
                 "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "cursor": None}
    repositories = []
    first = None
    cursors = set()
    while True:
        response = json.loads(request("https://api.github.com/graphql", {"query": QUERY, "variables": variables}, auth))
        if response.get("errors") or not response.get("data", {}).get("user"):
            raise ValueError("GitHub GraphQL response is incomplete")
        data = response["data"]
        first = first or data
        connection = data["user"]["repositories"]
        repositories.extend(connection["nodes"])
        if not connection["pageInfo"]["hasNextPage"]:
            break
        cursor = connection["pageInfo"]["endCursor"]
        if not cursor or cursor in cursors:
            raise ValueError("GitHub repository pagination did not advance")
        cursors.add(cursor)
        variables["cursor"] = cursor
    if len(repositories) != connection["totalCount"] or len({r["name"] for r in repositories}) != len(repositories):
        raise ValueError("GitHub repository inventory is incomplete")
    created = date.fromisoformat(first["user"]["createdAt"][:10])
    days = {}
    # These requests deliberately have no authorization: use the public calendar.
    for year in range(created.year, today.year+1):
        start, end = max(created, date(year, 1, 1)), min(today, date(year, 12, 31))
        html = request(f"https://github.com/users/{USERNAME}/contributions?from={year}-01-01&to={year}-12-31")
        days.update(parse_calendar(html, start, end))
    collection = first["user"]["contributionsCollection"]
    if collection["totalRepositoriesWithContributedCommits"] > 100:
        raise ValueError("Commit statistics exceed the supported repository limit")
    public_commits = [entry for entry in collection["commitContributionsByRepository"] if not entry["repository"]["isPrivate"]]
    return {
        "username": USERNAME,
        "updated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "created_at": created.isoformat(), "period_start": period_start.isoformat(), "period_end": today.isoformat(),
        "stars": sum(repo["stargazerCount"] for repo in repositories),
        "public_repositories": len(repositories),
        "commits": sum(entry["contributions"]["totalCount"] for entry in public_commits),
        "repositories_committed_to": len(public_commits),
        "pull_requests": first["pullRequests"]["issueCount"], "issues": first["issues"]["issueCount"],
        "total_contributions": sum(days.values()),
        "active_days": sum(count > 0 for day, count in days.items() if day >= period_start.isoformat()),
        "streaks": streaks(days, today), "languages": aggregate_languages(repositories),
        "calendar": dict(sorted(days.items())),
    }
