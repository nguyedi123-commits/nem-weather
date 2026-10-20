"""Open every built-in page, try the pickers and the ⓘ help, save screenshots, report page errors.

  python tests\\e2e_pages.py http://127.0.0.1:8892 "..\\..\\2. Output\\screenshots" [light|dark]
"""
from pathlib import Path
import sys

from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8892"
out = Path(sys.argv[2] if len(sys.argv) > 2 else "screenshots")
theme = sys.argv[3] if len(sys.argv) > 3 else "light"
out.mkdir(parents=True, exist_ok=True)
PAGES = {"Short": 6, "Medium": 6, "AI vs IFS": 6, "Seasonal": 6, "Map": 2}
problems, checks = [], 0


def check(ok, what):
    global checks
    checks += 1
    if not ok:
        problems.append(f"FAILED: {what}")


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge")
    page = b.new_page(viewport={"width": 1920, "height": 1080})
    page.on("pageerror", lambda e: problems.append(f"page error: {e}"))
    page.on("console", lambda m: problems.append(f"console {m.type}: {m.text}") if m.type == "error" else None)
    page.request.post(f"{url}/api/settings", data='{"theme": "%s"}' % theme)
    page.goto(url)
    page.wait_for_timeout(2500)
    for name, n in PAGES.items():
        page.click(f"#tabs .tab:text-is('{name}')")
        page.wait_for_timeout(1800)
        panels = page.locator(".grid-stack-item .panel").count()
        check(panels == n, f"{name}: {panels} panels, expected {n}")
        check(not page.locator(".err").count(), f"{name}: error box {page.locator('.err').all_inner_texts()}")
        page.screenshot(path=str(out / f"page_{name.replace(' ', '_')}_{theme}.png"))
        if name != "Map":   # try every field on the first panel (its own picker)
            sel = page.locator(".grid-stack-item .panel").first.locator("select[data-key=field]")
            for f in ("wind", "solar", "rain", "temp"):
                sel.select_option(f)
                page.wait_for_timeout(400)
                if f == "rain":
                    page.screenshot(path=str(out / f"page_{name.replace(' ', '_')}_rain_{theme}.png"))
            check(not page.locator(".err").count(), f"{name}: error after field changes")
        else:
            src = page.locator(".grid-stack-item .panel").first.locator("select[data-key=src]")
            for s in ("ens", "seasonal", "aifs", "ifs"):
                src.select_option(s)
                page.wait_for_timeout(900)
                if s == "seasonal":
                    page.screenshot(path=str(out / f"page_Map_seasonal_{theme}.png"))
            page.locator(".m-next").click()
            page.wait_for_timeout(600)
    # ⓘ help on the Short page
    page.click("#tabs .tab:text-is('Short')")
    page.wait_for_timeout(1500)
    page.locator(".grid-stack-item .panel").first.locator(".help-btn").click()
    page.wait_for_timeout(500)
    check(page.locator(".help-pop h3").inner_text().startswith("S1"), "ⓘ help shows the S1 card")
    page.screenshot(path=str(out / f"help_S1_{theme}.png"))
    page.keyboard.press("Escape")
    b.close()

print(f"{checks} checks, screenshots in {out}")
print("\n".join(problems) if problems else "All OK – no page errors")
