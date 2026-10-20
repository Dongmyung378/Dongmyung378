"""Refresh the GitHub cards; leave the last snapshot untouched on upstream failure."""
import argparse
import json
from pathlib import Path
import re
import sys
from stats_github import fetch_github
from stats_github_render import readme_block, render_cards

ROOT=Path(__file__).resolve().parents[1]


def write_outputs(root, record):
    path=root/"README.md"
    readme=path.read_text(encoding="utf-8")
    marker=r"<!-- github-stats:start -->.*?<!-- github-stats:end -->"
    matches=re.findall(marker,readme,flags=re.DOTALL)
    if len(matches)!=1:
        raise ValueError("README must contain exactly one github-stats block")
    updated=re.sub(marker,lambda _:readme_block(record),readme,flags=re.DOTALL)
    cards=render_cards(record)
    (root/"data").mkdir(exist_ok=True)
    (root/"assets/stats").mkdir(parents=True,exist_ok=True)
    for name,content in cards.items():
        (root/"assets/stats"/name).write_text(content,encoding="utf-8",newline="\n")
    (root/"data/github-stats.json").write_text(json.dumps({"schema_version":1,"profile":record},indent=2)+"\n",encoding="utf-8",newline="\n")
    path.write_text(updated,encoding="utf-8",newline="\n")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render-only",action="store_true")
    args=parser.parse_args()
    if args.render_only:
        record=json.loads((ROOT/"data/github-stats.json").read_text(encoding="utf-8"))["profile"]
    else:
        try:
            record=fetch_github()
        except Exception as exc:
            print(f"GitHub refresh failed ({type(exc).__name__}); existing snapshot and timestamp were left unchanged.",file=sys.stderr)
            return 1
    write_outputs(ROOT,record)
    print(json.dumps({"updated_at":record["updated_at"],"public_repositories":record["public_repositories"],
                      "total_contributions":record["total_contributions"],"streaks":record["streaks"]}))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
