"""Generate a self-hosted coverage badge SVG from coverage.xml (no external service).

    python tools/make_coverage_badge.py [coverage.xml] [out.svg]

Used by CI to publish a coverage badge to the `badges` branch, so the README badge always shows the real
percentage without requiring a third-party account.
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def pct(coverage_xml: str) -> int:
    root = ET.parse(coverage_xml).getroot()
    return round(float(root.get("line-rate", "0")) * 100)


def colour(p: int) -> str:
    return ("#e05d44" if p < 50 else "#dfb317" if p < 70 else "#97ca00" if p < 90 else "#4c1")


def svg(p: int) -> str:
    c = colour(p)
    val = f"{p}%"
    lw, vw = 62, 36                       # label / value box widths
    w = lw + vw
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="20" role="img" aria-label="coverage: {val}">
<linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>
<clipPath id="r"><rect width="{w}" height="20" rx="3" fill="#fff"/></clipPath>
<g clip-path="url(#r)">
<rect width="{lw}" height="20" fill="#555"/>
<rect x="{lw}" width="{vw}" height="20" fill="{c}"/>
<rect width="{w}" height="20" fill="url(#s)"/>
</g>
<g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
<text x="{lw/2}" y="14">coverage</text>
<text x="{lw + vw/2}" y="14">{val}</text>
</g></svg>'''


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "coverage.xml"
    out = sys.argv[2] if len(sys.argv) > 2 else "coverage.svg"
    p = pct(src)
    Path(out).write_text(svg(p), encoding="utf-8")
    print(f"coverage {p}% -> {out}")
