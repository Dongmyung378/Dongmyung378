"""Render GitHub activity cards in the profile's existing visual style."""
from html import escape
from stats_render import text

BG = "#101B2B"
LINE = "#34465E"
MUTED = "#B6C5D6"
MINT = "#79D4B3"
LAVENDER = "#C6B3FF"


def svg(width, height, title, description, content, vertical_gap=0):
    canvas_height = height + 2*vertical_gap
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{canvas_height}" viewBox="0 {-vertical_gap} {width} {canvas_height}" '
            'role="img" aria-labelledby="title desc" font-family="Arial, Helvetica, sans-serif">\n'
            f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>\n'
            f'<rect x=".5" y=".5" width="{width-1}" height="{height-1}" rx="14" fill="{BG}" stroke="{LINE}"/>\n'
            + "\n".join(content)+"\n</svg>\n")


def overview(record, mobile=False):
    width, height = (354, 466) if mobile else (760, 300)
    center_x, center_y, radius = (177, 122, 61) if mobile else (606, 150, 78)
    # Circle shows an actual proportion of active days, not an invented rank.
    circumference = 2*3.141592653589793*radius
    fraction = min(record["active_days"]/365, 1)
    lines = [text(22, 35, "GitHub activity", 24, MINT, 600)]
    lines += [
        f'<circle cx="{center_x}" cy="{center_y}" r="{radius}" fill="none" stroke="{LINE}" stroke-width="8"/>',
        f'<circle cx="{center_x}" cy="{center_y}" r="{radius}" fill="none" stroke="{MINT}" stroke-width="8" '
        f'stroke-dasharray="{circumference*fraction:.2f} {circumference:.2f}" stroke-linecap="round" transform="rotate(-90 {center_x} {center_y})"/>',
        text(center_x, center_y+8, f'{record["active_days"]:,}', 43, weight=600, anchor="middle"),
        text(center_x, center_y+32, "active days", 14, MUTED, anchor="middle"),
        text(center_x, center_y+radius+26, "Last 365 days", 14, MUTED, anchor="middle"),
    ]
    entries = [
        ("Stars earned", record["stars"]),
        ("Commits / last 365 days", record["commits"]),
        ("Pull requests", record["pull_requests"]),
        ("Issues opened", record["issues"]),
        ("Repos committed to / 365d", record["repositories_committed_to"]),
    ]
    top = 250 if mobile else 86
    right = 329 if mobile else 413
    for i, (label, value) in enumerate(entries):
        y = top+i*36
        lines += [text(22, y, label, 17 if mobile else 18, MUTED),
                  text(right, y, f"{value:,}", 22, "#E6EEF8", 600, "end")]
    lines.append(text(22, height-18, f'Public activity / {record["updated_at"][:16].replace("T"," ")} UTC', 12, MUTED))
    return svg(width, height, "GitHub activity", description(record), lines)


def streak_card(record, width=354):
    height=356
    s=record["streaks"]
    center=width/2
    lines=[text(22,35,"Contribution streak",23,LAVENDER,600),
           text(22,67,"Public GitHub calendar / UTC",14,MUTED)]
    for x, value, label in [(width*.27,s["current"],"Current streak"),(width*.75,s["longest"],"Longest streak")]:
        lines += [text(x,137,value,48,weight=600,anchor="middle"),text(x,166,label,16,MUTED,anchor="middle")]
    lines.append(f'<path d="M {center} 95 V 177" stroke="{LINE}"/>')
    lines += [text(22,218,"Total contributions",16,MUTED),
              text(width-22,218,f'{record["total_contributions"]:,}',24,MINT,600,"end")]
    lines += [text(22,252,"Since "+record["created_at"],14,MUTED)]
    longest = f'{s["longest_start"]} to {s["longest_end"]}' if s["longest"] else "No contribution streak yet"
    lines += [text(22,283,"Longest: "+longest,12,MUTED)]
    lines += [text(22,321,"Streak lengths are measured in days.",13,MUTED),
              text(22,340,"An unfinished UTC day does not break a streak.",12,MUTED)]
    return svg(width,height,"GitHub contribution streak",description(record),lines,vertical_gap=6)


def language_card(record, width=354):
    height=356
    languages=record["languages"]
    shown=languages[:8]
    if len(languages)>8:
        shown=shown+[{"name":"Other","percent":sum(x["percent"] for x in languages[8:]),"color":"#8DA2B8"}]
    lines=[text(22,35,"Most used languages",23,MINT,600),
           text(22,65,"Public, non-fork repositories",14,MUTED)]
    lines.append(f'<defs><clipPath id="bar"><rect x="22" y="83" width="{width-44}" height="12" rx="6"/></clipPath></defs>')
    x=22
    for item in shown:
        segment=(width-44)*item["percent"]/100
        lines.append(f'<rect x="{x:.3f}" y="83" width="{segment:.3f}" height="12" fill="{escape(item["color"])}" clip-path="url(#bar)"/>')
        x+=segment
    for i,item in enumerate(shown):
        y=124+i*22
        lines += [f'<circle cx="28" cy="{y-5}" r="5" fill="{escape(item["color"])}"/>',
                  text(42,y,item["name"],15),
                  text(width-22,y,f'{item["percent"]:.2f}%',15,MUTED,anchor="end")]
    if not shown:
        lines.append(text(22,138,"No language data available",16,MUTED))
    lines += [text(22,326,f'{record["public_repositories"]} repositories / GitHub language bytes',12,MUTED),
              text(22,344,"Code volume, not proficiency or time spent.",12,MUTED)]
    return svg(width,height,"Most used languages",description(record),lines,vertical_gap=6)


def description(record):
    return (f'GitHub {record["username"]}: {record["stars"]} stars earned, {record["commits"]} public commit contributions '
            f'in the last 365 days, {record["pull_requests"]} public pull requests, {record["issues"]} public issues; '
            f'{record["total_contributions"]} contributions on the public calendar, current streak {record["streaks"]["current"]} days, '
            f'longest streak {record["streaks"]["longest"]} days. Updated {record["updated_at"]} UTC.')


def render_cards(record):
    return {
        "github-overview.svg":overview(record),
        "github-overview-mobile.svg":overview(record,True),
        "github-streak.svg":streak_card(record),
        "github-streak-tablet.svg":streak_card(record,600),
        "github-languages.svg":language_card(record),
        "github-languages-tablet.svg":language_card(record,600),
    }


def readme_block(record):
    version=record["updated_at"].replace("-","").replace(":","")
    base=f'https://raw.githubusercontent.com/{record["username"]}/{record["username"]}/main/assets/stats/'
    alt=escape(description(record),quote=True)
    profile=f'https://github.com/{record["username"]}'
    return f'''<!-- github-stats:start -->
<h1>GitHub Stats</h1>

<p>
<a href="{profile}?tab=overview"><picture><source media="(max-width: 480px)" srcset="{base}github-overview-mobile.svg?v={version}" /><img src="{base}github-overview.svg?v={version}" width="100%" alt="{alt}" /></picture></a>
</p>

<p>
<a href="{profile}?tab=overview"><picture><source media="(max-width: 480px)" srcset="{base}github-streak.svg?v={version}" width="100%" /><source media="(max-width: 1000px)" srcset="{base}github-streak-tablet.svg?v={version}" width="100%" /><img src="{base}github-streak.svg?v={version}" width="49%" alt="{alt}" /></picture></a>
<a href="{profile}?tab=repositories"><picture><source media="(max-width: 480px)" srcset="{base}github-languages.svg?v={version}" width="100%" /><source media="(max-width: 1000px)" srcset="{base}github-languages-tablet.svg?v={version}" width="100%" /><img src="{base}github-languages.svg?v={version}" width="49%" alt="Language distribution by code bytes in public non-fork repositories. This measures code volume, not skill." /></picture></a>
</p>

<p><sub>Official GitHub data. Scheduled daily at 00:00 UTC alongside Coding Practice.<br />Cards show the last successful refresh. <a href="docs/profile-statistics.md">How the statistics are counted</a></sub></p>
<!-- github-stats:end -->'''
