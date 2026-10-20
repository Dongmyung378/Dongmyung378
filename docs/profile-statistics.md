# Profile statistics

The profile combines GitHub activity with AtCoder and LeetCode coding practice. The scheduled workflow runs at **00:00 UTC** each day and can also be started manually. GitHub may queue scheduled jobs; this is a scheduled start, not an exact delivery-time guarantee. Each card displays its last successful refresh.

## GitHub activity

The cards use GitHub's own GraphQL API and public contribution calendar. They are rendered as SVG files in this repository, so viewing the profile does not depend on an external statistics-card service.

| Field | Meaning |
| --- | --- |
| Stars earned | Stars on public repositories owned by this account, excluding forks. |
| Commits | Commit contributions to public repositories during the last 365 UTC dates, including today. This follows GitHub's contribution-counting rules rather than counting every Git object. |
| Pull requests and issues | Public pull requests and issues authored by this account across its history. |
| Repos committed to | Public repositories with counted commit contributions during the same 365-day window. |
| Active days | Dates with at least one contribution on the public contribution calendar in the last 365 days. The ring shows active days divided by 365, not a grade or developer ranking. |
| Total contributions | Contributions shown on the public calendar since the account was created. The unauthenticated public calendar is used even when API access is authenticated. |
| Current streak | Consecutive UTC calendar dates with a contribution, ending today or yesterday. An unfinished day with no contribution does not immediately reset yesterday's streak. |
| Longest streak | Longest consecutive run on the available public calendar since account creation. |
| Most used languages | GitHub-reported language bytes across owned, public, non-fork repositories. The largest eight languages are shown separately and the remainder are grouped as Other. |

Languages describe code volume, not proficiency, personal authorship of every line, or time spent. The calendar can include any restricted-contribution counts that the account owner has chosen to display publicly; the collector does not request private calendar details. Public repository names and private API results are not written to the snapshot. Language and repository pages are checked for completeness before publishing.

## Refresh and failure handling

The workflow uses its automatically supplied `GITHUB_TOKEN`; no additional personal access token needs to be stored. For a local refresh, authenticate GitHub CLI or provide `GH_TOKEN` in the process environment.

```bash
python -m unittest discover -s tests -v
python scripts/update_github_stats.py
python scripts/update_coding_stats.py
```

To regenerate images from retained data without accessing the network:

```bash
python scripts/update_github_stats.py --render-only
python scripts/update_coding_stats.py --render-only
```

A failed GitHub fetch preserves its existing snapshot, images, and date. A coding-platform failure retains that platform's last successful values. If just one coding platform fails, the other platform updates and the script records a warning. If both coding platforms fail, or the GitHub fetch fails, the workflow reports a failure while still publishing any successful independent refresh. Missing values are not silently published as zeros.

Sources: [GitHub GraphQL user and contribution fields](https://docs.github.com/en/graphql/reference/users), [GitHub contribution-counting rules](https://docs.github.com/en/account-and-profile/how-tos/contribution-settings/troubleshooting-missing-contributions), [GitHub Actions token](https://docs.github.com/en/actions/concepts/security/github_token).
