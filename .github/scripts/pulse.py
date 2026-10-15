"""Build assets/pulse.svg — the contribution graph as a 'server scan' animation.

Runs in GitHub Actions. Needs env GITHUB_TOKEN and USERNAME.
`python3 pulse.py --demo` renders with random data for local testing.
"""
import json
import os
import random
import sys
import urllib.request
from datetime import date, timedelta

OUT = "assets/pulse.svg"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount contributionLevel weekday date } }
      }
    }
  }
}"""

LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
          "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [[(d["weekday"], LEVELS[d["contributionLevel"]], d["contributionCount"])
              for d in w["contributionDays"]] for w in cal["weeks"]]
    return weeks, cal["totalContributions"]


def demo():
    weeks, total = [], 0
    for _ in range(53):
        days = []
        for wd in range(7):
            n = random.choice([0] * 6 + [1, 2, 3, 5, 8])
            total += n
            lvl = 0 if n == 0 else min(4, 1 + n // 3)
            days.append((wd, lvl, n))
        weeks.append(days)
    return weeks, total


def build(weeks, total):
    CELL, GAP = 14, 4
    STEP = CELL + GAP
    LEFT, TOP = 24, 62
    cols = len(weeks)
    W = LEFT * 2 + cols * STEP - GAP
    H = TOP + 7 * STEP - GAP + 58
    CYCLE = 9.0     # seconds per full loop
    SWEEP = 5.5     # seconds for the beam to cross the grid

    active_days = sum(1 for w in weeks for (_, lvl, _) in w if lvl > 0)

    fills = {0: "#111a24", 1: "#0c4a6e", 2: "#0369a1", 3: "#0ea5e9", 4: "#7dd3fc"}

    flash_rules = "\n".join(
        f"    @keyframes f{l} {{ 0% {{ fill: #f0f9ff; transform: scale(1.35); }} "
        f"12%, 100% {{ fill: {fills[l]}; transform: scale(1); }} }}"
        for l in range(1, 5)
    )

    col_rules = "\n".join(
        f".c{c}{{animation-delay:{c / cols * SWEEP:.3f}s}}" for c in range(cols)
    )

    cells = []
    for c, week in enumerate(weeks):
        for (wd, lvl, n) in week:
            x = LEFT + c * STEP
            y = TOP + wd * STEP
            cls = f"l{lvl} c{c}" if lvl else f"e c{c}"
            cells.append(
                f'<rect class="{cls}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3.5" fill="{fills[lvl]}"/>'
            )

    grid_w = cols * STEP - GAP
    grid_h = 7 * STEP - GAP
    beam_from = LEFT - 40
    beam_to = LEFT + grid_w + 10
    base_y = TOP + grid_h + 34

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <linearGradient id="beam" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#38bdf8" stop-opacity="0"/>
      <stop offset="0.85" stop-color="#38bdf8" stop-opacity="0.35"/>
      <stop offset="1" stop-color="#e0f2fe" stop-opacity="0.9"/>
    </linearGradient>
    <linearGradient id="edge" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#38bdf8" stop-opacity="0.45"/>
      <stop offset="0.5" stop-color="#38bdf8" stop-opacity="0.06"/>
      <stop offset="1" stop-color="#a78bfa" stop-opacity="0.4"/>
    </linearGradient>
    <clipPath id="gridclip"><rect x="{LEFT - 6}" y="{TOP - 6}" width="{grid_w + 12}" height="{grid_h + 12}" rx="6"/></clipPath>
  </defs>
  <style>
    .m {{ font: 14px ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; }}
    rect.e, rect.l1, rect.l2, rect.l3, rect.l4 {{
      transform-box: fill-box; transform-origin: center;
      animation-duration: {CYCLE}s; animation-iteration-count: infinite; animation-timing-function: ease-out;
    }}
    .e {{ animation-name: dim; }}
    .l1 {{ animation-name: f1; }} .l2 {{ animation-name: f2; }} .l3 {{ animation-name: f3; }} .l4 {{ animation-name: f4; }}
    @keyframes dim {{
      0% {{ fill: #1e3a52; }}
      6%, 100% {{ fill: #111a24; }}
    }}
{flash_rules}
    .beam {{ animation: sweep {CYCLE}s linear infinite; }}
    @keyframes sweep {{
      0% {{ transform: translateX(0); opacity: 1; }}
      {SWEEP / CYCLE * 100:.1f}% {{ transform: translateX({beam_to - beam_from}px); opacity: 1; }}
      {SWEEP / CYCLE * 100 + 0.1:.1f}%, 100% {{ transform: translateX({beam_to - beam_from}px); opacity: 0; }}
    }}
    .led {{ animation: blink 1.6s ease-in-out infinite; }}
    @keyframes blink {{ 50% {{ opacity: 0.25; }} }}
{col_rules}
    @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} .beam {{ display: none; }} }}
  </style>

  <rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14" fill="#070b12" stroke="url(#edge)" stroke-width="1.5"/>

  <text x="{LEFT}" y="34" class="m"><tspan fill="#4ade80">ayubjon@server</tspan><tspan fill="#64748b">:</tspan><tspan fill="#38bdf8">~</tspan><tspan fill="#64748b">$ </tspan><tspan fill="#f8fafc">git log --since="1 year ago"</tspan></text>
  <circle class="led" cx="{W - LEFT - 6}" cy="29" r="5" fill="#4ade80"/>
  <text x="{W - LEFT - 20}" y="34" class="m" fill="#64748b" text-anchor="end">live</text>

  {"".join(cells)}

  <g clip-path="url(#gridclip)">
    <rect class="beam" x="{beam_from}" y="{TOP - 6}" width="40" height="{grid_h + 12}" fill="url(#beam)"/>
  </g>

  <text x="{LEFT}" y="{base_y}" class="m" fill="#7dd3fc">● {total} contributions</text>
  <text x="{LEFT + 230}" y="{base_y}" class="m" fill="#a78bfa">● {active_days} active days</text>
  <g transform="translate({W - LEFT - 5 * 18 - 70},{base_y - 12})">
    <text x="0" y="12" class="m" fill="#64748b">less</text>
    {"".join(f'<rect x="{42 + i * 18}" y="0" width="14" height="14" rx="3.5" fill="{fills[i]}"/>' for i in range(5))}
    <text x="{42 + 5 * 18 + 4}" y="12" class="m" fill="#64748b">more</text>
  </g>
</svg>
'''


def main():
    if "--demo" in sys.argv:
        weeks, total = demo()
    else:
        weeks, total = fetch(os.environ["USERNAME"], os.environ["GITHUB_TOKEN"])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(build(weeks, total))
    print(f"wrote {OUT}: {total} contributions")


if __name__ == "__main__":
    main()
