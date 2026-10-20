"""Render public coding statistics as self-contained, accessible SVG cards."""
from html import escape

COLORS = {"Easy": "#79D4B3", "Medium": "#EBC078", "Hard": "#E794A5"}


def text(x, y, value, size=14, color="#E6EEF8", weight=400, anchor="start"):
    return (f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{escape(str(value))}</text>')


def profile_rank(value):
    if value is None:
        return "Unavailable"
    return "5M+" if value > 5_000_000 else f"#{value:,}"


def panel(x, y, width, record, platform, compact=False, mobile=False):
    height = 312
    left, right = x + 20, x + width - 20
    center = x + width / 2
    heading, body, small = (17, 13, 13) if compact else (24, 18, 16) if mobile else (20, 16, 14)
    accent = "#C6B3FF" if platform == "AtCoder" else "#EBC078"
    lines = [f'<rect x="{x+.5}" y="{y+.5}" width="{width-1}" height="{height-1}" rx="14" fill="#101B2B" stroke="#34465E"/>']
    lines += [text(left, y+32, platform, heading, accent, 600), text(right, y+32, record["username"], small, "#B6C5D6", anchor="end")]
    if platform == "AtCoder":
        value = "Unrated" if record["rating"] is None else f'{record["rating"]:,}'
        lines.append(text(left, y+88, value, 36 if compact else 44, weight=600))
        suffix = " (provisional)" if record["provisional"] else ""
        lines.append(text(left, y+112, "Algorithm rating"+suffix, small, "#B6C5D6"))
        lines += [text(left, y+146, "Algorithm rank", small, "#B6C5D6"), text(center+6, y+146, "Rated contests", small, "#B6C5D6")]
        rank = "Unranked" if record["rank"] is None else f'#{record["rank"]:,}'
        lines += [text(left, y+171, rank, body+4, weight=600), text(center+6, y+171, record["rated_contests"], body+4, weight=600)]
        history = record["history"][-12:]
        if history:
            peak = record["highest_rating"]
            lines.append(text(left, y+200, f"Rating history / Peak {peak:,}", small, "#B6C5D6"))
            lo = min(0, min(item["rating"] for item in history))
            hi = max(1, max(item["rating"] for item in history))
            points = []
            for i, item in enumerate(history):
                px = left + (right-left) * i / max(len(history)-1, 1)
                py = y+250 - 36*(item["rating"]-lo)/(hi-lo)
                points.append((round(px, 2), round(py, 2)))
            path = " ".join(f"{px},{py}" for px, py in points)
            lines.append(f'<path d="M {left} {y+250} H {right}" stroke="#34465E"/>')
            lines.append(f'<polyline points="{path}" fill="none" stroke="{accent}" stroke-width="2.5" stroke-linejoin="round"/>')
            for px, py in points:
                lines.append(f'<circle cx="{px}" cy="{py}" r="3" fill="{accent}"/>')
            lines += [text(left, y+269, history[0]["date"][5:], small, "#B6C5D6"), text(right, y+269, history[-1]["date"][5:], small, "#B6C5D6", anchor="end")]
        else:
            lines.append(text(left, y+219, "No rated contests yet", body, "#B6C5D6"))
    else:
        lines += [text(left, y+88, f'{record["solved"]:,}', 36 if compact else 44, weight=600), text(left, y+112, "Problems solved", small, "#B6C5D6")]
        contest = record["contest"]
        rating = "Unrated" if contest["rating"] is None else f'{contest["rating"]:,.0f}'
        lines += [text(left, y+146, "Contest rating", small, "#B6C5D6"), text(center+6, y+146, f'Active days {record["activity_year"]}', small, "#B6C5D6"), text(left, y+171, rating, body+3, weight=600), text(center+6, y+171, record["active_days"], body+4, weight=600)]
        lines.append(f'<rect x="{left}" y="{y+197}" width="{right-left}" height="10" rx="5" fill="#293A50"/>')
        px = left
        for difficulty in ("Easy", "Medium", "Hard"):
            value = record["difficulty"][difficulty]
            segment = (right-left) * value / max(record["solved"], 1)
            if segment:
                lines.append(f'<rect x="{px}" y="{y+197}" width="{segment}" height="10" fill="{COLORS[difficulty]}"/>')
            px += segment
        for i, difficulty in enumerate(("Easy", "Medium", "Hard")):
            px = left + (right-left) * i / 2
            anchor = ("start", "middle", "end")[i]
            lines.append(text(px, y+233, f'{difficulty} {record["difficulty"][difficulty]}', small, COLORS[difficulty], anchor=anchor))
        lines.append(text(left, y+267, f'Profile rank: {profile_rank(record["profile_rank"])}', small, "#B6C5D6"))
    refreshed = record["updated_at"][:16].replace("T", " ")
    lines.append(text(left, y+294, f'{refreshed} UTC', small, "#A6B9D0"))
    return lines


def render_cards(records):
    """Keep wide, tablet and mobile SVG content synchronized from one snapshot."""
    output = {}
    for name, width, height, panel_width, coords, compact in [
        ("wide", 760, 312, 370, [(0, 0), (390, 0)], False),
        ("tablet", 500, 312, 240, [(0, 0), (260, 0)], True),
        ("mobile", 360, 640, 360, [(0, 0), (0, 328)], False),
    ]:
        content = []
        for (x, y), key, label in zip(coords, ("atcoder", "leetcode"), ("AtCoder", "LeetCode")):
            content.extend(panel(x, y, panel_width, records[key], label, compact, name == "mobile"))
        description = alt_text(records)
        output[f"coding-{name}.svg"] = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc" font-family="Arial, Helvetica, sans-serif">\n'
            '<title id="title">Coding practice</title>\n'
            f'<desc id="desc">{escape(description)}</desc>\n'+"\n".join(content)+'\n</svg>\n')
    for key, label in (("atcoder", "AtCoder"), ("leetcode", "LeetCode")):
        content = panel(8, 0, 354, records[key], label, mobile=True)
        output[f"{key}.svg"] = ('<svg xmlns="http://www.w3.org/2000/svg" width="370" height="328" viewBox="0 0 370 328" role="img" aria-labelledby="title desc" font-family="Arial, Helvetica, sans-serif">\n'
            f'<title id="title">{label} coding practice</title>\n'
            f'<desc id="desc">{escape(alt_text(records, key))}</desc>\n'+"\n".join(content)+'\n</svg>\n')
    return output


def alt_text(records, platform=None):
    a, leet = records["atcoder"], records["leetcode"]
    rating = "unrated" if a["rating"] is None else str(a["rating"])
    status = " provisional" if a["provisional"] else ""
    rank = "unranked" if a["rank"] is None else f'#{a["rank"]:,}'
    contest = "unrated" if leet["contest"]["rating"] is None else f'{leet["contest"]["rating"]:.0f}'
    descriptions = {
        "atcoder": f'AtCoder {a["username"]}: algorithm rating {rating}{status}, algorithm rank {rank}, {a["rated_contests"]} rated contests; updated {a["updated_at"][:10]} UTC.',
        "leetcode": (f'LeetCode {leet["username"]}: {leet["solved"]} problems solved, '+', '.join(f'{k} {v}' for k,v in leet["difficulty"].items())+
            f', contest rating {contest}, {leet["active_days"]} active days in {leet["activity_year"]}, profile rank {profile_rank(leet["profile_rank"])}; updated {leet["updated_at"][:10]} UTC.')
    }
    return descriptions[platform] if platform else " ".join(descriptions.values())


def readme_block(records):
    version = max(record["updated_at"] for record in records.values()).replace("-", "").replace(":", "")
    return '''<!-- coding-stats:start -->
<h3>Coding Practice</h3>

<p>
<a href="https://atcoder.jp/users/ParkDM"><img src="https://raw.githubusercontent.com/Dongmyung378/Dongmyung378/main/assets/stats/atcoder.svg?v='''+version+'''" width="370" alt="'''+escape(alt_text(records, "atcoder"), quote=True)+'''" /></a>
<a href="https://leetcode.com/u/Dongmyung/"><img src="https://raw.githubusercontent.com/Dongmyung378/Dongmyung378/main/assets/stats/leetcode.svg?v='''+version+'''" width="370" alt="'''+escape(alt_text(records, "leetcode"), quote=True)+'''" /></a>
</p>

<p><sub>Open a card to view the latest official profile.<br />Scheduled daily at 00:00 UTC. Cards show the last successful refresh (UTC).</sub></p>
<!-- coding-stats:end -->'''
