"""Build web/help.json (the ⓘ pop-up of each panel) from the panel cards in 4. Docs/panels/.

Takes each card's title and its "What you see" and "How to read it" sections, so the screen and the cards never
drift apart. Run after changing a card:  python tools\\build_help.py
"""
import html
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT.parents[1] / "4. Docs" / "panels"
KIND = {"S1": "short", "M1": "medium", "C1": "compare", "L1": "seasonal", "G1": "map", "A1": "about", "D1": "changes", "I1": "insights"}
SECTIONS = ["How to read it", "What you see", "Limits"]


def md_inline(t):
    t = html.escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    t = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", t)   # links -> plain text (cards live outside the screen)
    return t


def md_block(lines):
    """Bullets (2 levels) and plain lines -> HTML."""
    out, level = [], 0
    for raw in lines:
        if not raw.strip():
            continue
        m = re.match(r"^(\s*)- (.*)$", raw)
        if m:
            want = 1 + len(m.group(1)) // 2
            while level < want:
                out.append("<ul>"); level += 1
            while level > want:
                out.append("</ul>"); level -= 1
            out.append(f"<li>{md_inline(m.group(2))}</li>")
        elif level and raw.startswith("  "):   # continuation of the previous bullet
            out[-1] = out[-1][:-5] + " " + md_inline(raw.strip()) + "</li>"
        else:
            while level:
                out.append("</ul>"); level -= 1
            out.append(f"<p>{md_inline(raw.strip())}</p>")
    while level:
        out.append("</ul>"); level -= 1
    return "".join(out)


def card(path):
    text = path.read_text(encoding="utf-8").splitlines()
    title = re.sub(r"^#\s*\w+\s*[–-]\s*", "", text[0]).strip()
    secs, cur = {}, None
    for line in text[1:]:
        if line.startswith("## "):
            cur = line[3:].strip()
            secs[cur] = []
        elif cur:
            secs[cur].append(line)
    body = "".join(f"<h4>{s}</h4>{md_block(secs[s])}" for s in SECTIONS if s in secs)
    return title, body


def main():
    out = {}
    for p in sorted(CARDS.glob("*.md")):
        code = p.name.split("_")[0]
        if code in KIND:
            title, body = card(p)
            out[KIND[code]] = {"code": code, "title": title, "html": body}
    f = ROOT / "web" / "help.json"
    f.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(out)} panel guides -> {f}")


if __name__ == "__main__":
    main()
