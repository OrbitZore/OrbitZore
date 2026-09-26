#!/usr/bin/env python3
"""Generate a GitHub-style "Most used languages" SVG bar.

Aggregates language byte counts across all non-fork repositories owned by
the user via the GitHub REST API (gh CLI, authenticated with GITHUB_TOKEN),
then renders a stacked bar + legend into github-languages.svg.
"""

import json
import subprocess
import sys

USER = "OrbitZore"
OUT = "github-languages.svg"
TOP_N = 8

# GitHub Linguist language colors
COLORS = {
    "C++": "#f34b7d", "C": "#555555", "Python": "#3572A5",
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Shell": "#89e051",
    "CMake": "#DA3434", "HTML": "#e34c26", "CSS": "#563d7c",
    "Jupyter Notebook": "#DA5B0B", "Makefile": "#427819",
    "Dockerfile": "#384d54", "Go": "#00ADD8", "Rust": "#dea584",
    "Java": "#b07219", "Kotlin": "#A97BFF", "Vue": "#41b883",
    "Ruby": "#701516", "Lua": "#000080", "PowerShell": "#012456",
    "Vim Script": "#199f4b", "ZenScript": "#00BCD1", "SCSS": "#c6538c",
    "Vue": "#41b883", "Nix": "#7e7eff", "Cuda": "#3A4E3A",
}
FALLBACK = "#8b949e"


def gh(path: str) -> list | dict:
    out = subprocess.run(
        ["gh", "api", "--paginate", path],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def main() -> None:
    repos = gh(f"users/{USER}/repos?type=owner&per_page=100")
    names = [r["full_name"] for r in repos if not r.get("fork")]

    totals: dict[str, int] = {}
    for name in names:
        try:
            langs = gh(f"repos/{name}/languages")
        except subprocess.CalledProcessError as e:
            print(f"warn: skip {name}: {e}", file=sys.stderr)
            continue
        for lang, size in langs.items():
            totals[lang] = totals.get(lang, 0) + size

    if not totals:
        sys.exit("no language data collected")

    grand = sum(totals.values())
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    top = ranked[:TOP_N]
    other = grand - sum(v for _, v in top)
    sections = [(l, v, COLORS.get(l, FALLBACK)) for l, v in top]
    if other > 0:
        sections.append(("Other", other, "#ebedf0"))

    # ---- render SVG ----
    W = 780
    BAR_H = 14
    x = 0.0
    bar_parts, legend_parts = [], []
    for i, (lang, size, color) in enumerate(sections):
        pct = size / grand * 100
        w = max(size / grand * W, 2.0)  # keep slivers visible
        bar_parts.append(
            f'<rect x="{x:.2f}" y="0" width="{w:.2f}" height="{BAR_H}" '
            f'rx="4" fill="{color}"><title>{lang} {pct:.1f}%</title></rect>'
        )
        col, row = i % 4, i // 4
        lx, ly = col * 195 + 7, BAR_H + 26 + row * 24
        legend_parts.append(
            f'<circle cx="{lx}" cy="{ly - 4}" r="5" fill="{color}"/>'
            f'<text x="{lx + 12}" y="{ly}" class="lbl">{lang} '
            f'<tspan class="pct">{pct:.1f}%</tspan></text>'
        )
        x += w

    rows = (len(sections) + 3) // 4
    H = BAR_H + 26 + rows * 24 + 4

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Most used languages">
  <style>
    .lbl {{ font: 13px -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #24292f; }}
    .pct {{ fill: #57606a; }}
    @media (prefers-color-scheme: dark) {{
      .lbl {{ fill: #c9d1d9; }}
      .pct {{ fill: #8b949e; }}
    }}
  </style>
  {''.join(bar_parts)}
  {''.join(legend_parts)}
</svg>
'''

    with open(OUT, "w") as f:
        f.write(svg)

    print(f"wrote {OUT}: {len(sections)} sections, {grand / 1e6:.1f} MB bytes total across {len(names)} repos")
    for lang, size, _ in sections:
        print(f"  {lang:<16} {size / grand * 100:5.1f}%")


if __name__ == "__main__":
    main()
