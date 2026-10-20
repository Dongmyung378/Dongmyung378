# Coding statistics

The profile cards use official public data from [AtCoder ParkDM](https://atcoder.jp/users/ParkDM) and [LeetCode Dongmyung](https://leetcode.com/u/Dongmyung/). They do not require account credentials or third-party statistics widgets.

Each card links directly to its official profile. The cards wrap onto separate rows on smaller screens. Following a link shows the latest information available on that platform; it does not trigger a GitHub workflow. Values displayed in the README are snapshots fetched by the workflow, not browser-side live requests.

- AtCoder values refer to **Algorithm** contests. The graph uses `NewRating` from rated contests, not performance scores or contest placement. A provisional rating stays labelled provisional.
- LeetCode solved counts are distinct accepted problems, not accepted submission counts. Active days are scoped to the calendar year shown. The profile rank and the contest rating are different metrics. Profile ranks above five million are displayed as `5M+`; absent contest ratings are `Unrated`, not zero.
- Each card displays its last successful UTC refresh time. Failed sources retain their previous values and original timestamp. The initial update requires both sources to succeed, and a total fetch failure leaves published files unchanged. Image URLs include the successful refresh version so an earlier cached card is not reused for a new snapshot.
- The [profile statistics workflow](../.github/workflows/profile-statistics.yml) is scheduled daily at **00:00 UTC (09:00 KST)**, when the UTC date changes. GitHub may delay or drop scheduled jobs, or disable them for inactive public repositories. The displayed timestamp, rather than a live-status claim, indicates freshness.
- To refresh immediately, open the repository's **Actions** tab, select **Update profile statistics**, choose **Run workflow** on `main`, and wait for a successful run. A successful manual or push-triggered run verifies the refresh code; only a run labelled `schedule` verifies the automatic trigger.

Run `python scripts/update_coding_stats.py` to fetch and render, or add `--render-only` to regenerate SVGs from `data/coding-stats.json`. Run `python -m unittest discover -s tests -v` to verify parsing and failure handling. Python 3.12 or newer is sufficient; no additional packages are required.

The README block between `coding-stats:start` and `coding-stats:end` is generated, including its accessible text. Other profile sections are maintained manually.
