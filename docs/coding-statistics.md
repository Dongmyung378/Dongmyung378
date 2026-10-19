# Coding statistics

The profile cards use official public data from [AtCoder ParkDM](https://atcoder.jp/users/ParkDM) and [LeetCode Dongmyung](https://leetcode.com/u/Dongmyung/). They do not require account credentials or third-party statistics widgets.

- AtCoder values refer to **Algorithm** contests. The graph uses `NewRating` from rated contests, not performance scores or contest placement. A provisional rating stays labelled provisional.
- LeetCode solved counts are distinct accepted problems, not accepted submission counts. Active days are scoped to the calendar year shown. The profile rank and the contest rating are different metrics. Profile ranks above five million are displayed as `5M+`; absent contest ratings are `Unrated`, not zero.
- Each card displays its last successful UTC refresh date. Failed sources retain their previous values and original date. The initial update requires both sources to succeed, and a total fetch failure leaves published files unchanged.
- The scheduled workflow runs daily at 21:17 UTC (06:17 Korea time the next day) and can also be run manually. GitHub may delay scheduled jobs or disable them for inactive public repositories. The displayed date, rather than a live-status claim, indicates freshness.

Run `python scripts/update_coding_stats.py` to fetch and render, or add `--render-only` to regenerate SVGs from `data/coding-stats.json`. Run `python -m unittest discover -s tests -v` to verify parsing and failure handling. Python 3.12 or newer is sufficient; no additional packages are required.

The README block between `coding-stats:start` and `coding-stats:end` is generated, including its accessible text. Other profile sections are maintained manually.
