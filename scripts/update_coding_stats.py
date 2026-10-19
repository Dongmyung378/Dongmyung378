"""Fetch public profile data; retain the last successful snapshot on partial failure."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from stats_atcoder import parse_atcoder
from stats_leetcode import GRAPHQL_QUERY, parse_leetcode
from stats_render import readme_block, render_cards

ROOT = Path(__file__).resolve().parents[1]
ATCODER = "ParkDM"
LEETCODE = "Dongmyung"


def request(url, payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"User-Agent": "Dongmyung378-profile-stats/1.0", "Accept": "application/json,text/html"}
    if body is not None:
        headers.update({"Content-Type": "application/json", "Referer": f"https://leetcode.com/u/{LEETCODE}/"})
    for attempt in range(3):
        try:
            with urlopen(Request(url, data=body, headers=headers), timeout=25) as response:
                return response.read().decode("utf-8")
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)
    raise RuntimeError("Request retry limit reached")


def fetch_atcoder():
    profile_url = f"https://atcoder.jp/users/{ATCODER}?lang=en&contestType=algo"
    profile = request(profile_url)
    history = json.loads(request(f"https://atcoder.jp/users/{ATCODER}/history/json?contestType=algo"))
    data = parse_atcoder(profile, history)
    return {"username": ATCODER, "profile_url": f"https://atcoder.jp/users/{ATCODER}", **data}


def fetch_leetcode(year):
    payload = json.loads(request("https://leetcode.com/graphql/", {"query": GRAPHQL_QUERY, "variables": {"username": LEETCODE, "year": year}}))
    data = parse_leetcode(payload, LEETCODE, year)
    return {"username": LEETCODE, "profile_url": f"https://leetcode.com/u/{LEETCODE}/", **data}


def refresh(previous, fetchers, timestamp):
    """Do not relabel old data as fresh, or replace unavailable values with zero."""
    records = dict(previous)
    errors = {}
    successes = 0
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {name: pool.submit(fetcher) for name, fetcher in fetchers.items()}
        for name, future in futures.items():
            try:
                records[name] = {**future.result(), "updated_at": timestamp}
                successes += 1
            except Exception as exc:
                errors[name] = f"{type(exc).__name__}: {exc}"
    if any(name not in records for name in fetchers):
        raise RuntimeError("Initial public-data fetch incomplete: "+", ".join(errors))
    if successes == 0:
        raise RuntimeError("Both public sources failed; existing files were left unchanged")
    return records, errors


def write_outputs(root, records):
    readme_path = root / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    pattern = r"<!-- coding-stats:start -->.*?<!-- coding-stats:end -->"
    if len(re.findall(pattern, readme, flags=re.DOTALL)) != 1:
        raise ValueError("README must contain exactly one coding-stats block")
    updated = re.sub(pattern, lambda _: readme_block(records), readme, flags=re.DOTALL)
    svgs = render_cards(records)
    (root / "data").mkdir(exist_ok=True)
    (root / "assets" / "stats").mkdir(exist_ok=True)
    (root / "data" / "coding-stats.json").write_text(json.dumps({"schema_version": 1, "profiles": records}, indent=2, ensure_ascii=False)+"\n", encoding="utf-8", newline="\n")
    for name, svg in svgs.items():
        (root / "assets" / "stats" / name).write_text(svg, encoding="utf-8", newline="\n")
    readme_path.write_text(updated, encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render-only", action="store_true", help="Render the retained snapshot without network requests")
    args = parser.parse_args()
    path = ROOT / "data" / "coding-stats.json"
    previous = json.loads(path.read_text(encoding="utf-8"))["profiles"] if path.exists() else {}
    if args.render_only:
        records, errors = previous, {}
        if not all(key in records for key in ("atcoder", "leetcode")):
            raise ValueError("No complete snapshot is available")
    else:
        now = datetime.now(timezone.utc)
        stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        records, errors = refresh(previous, {"atcoder": fetch_atcoder, "leetcode": lambda: fetch_leetcode(now.year)}, stamp)
    write_outputs(ROOT, records)
    for name, error in errors.items():
        print(f"WARNING: {name}: {error}; retained the last successful values and date", file=sys.stderr)
    print(json.dumps({"updated_at": {k: v["updated_at"] for k,v in records.items()}, "retained_sources": list(errors)}))


if __name__ == "__main__":
    main()
