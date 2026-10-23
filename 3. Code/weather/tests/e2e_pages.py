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
PAGES = {"Overview": 3, "Short": 6, "Medium": 6, "Seasonal": 6, "Map": 2}   # AI vs IFS removed 23 Oct (W-025); Overview W-026
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
        if name == "Overview":   # W-026: week-ahead grid – 4 states × up to 14 days, click opens a chart page
            cells = page.locator(".week td.cell")
            n_cells = cells.count()
            check(n_cells >= 4 * 12, f"Overview: {n_cells} week cells")
            check(page.locator(".week tr").count() == 5, "Overview: 4 state rows + head")
            check(not page.locator("#page-field-box").is_visible(), "Overview: no top-bar field picker")
            cells.first.click()
            page.wait_for_timeout(1500)
            check(page.locator("#tabs .tab.on").inner_text() == "Short", "Overview: day-1 click opens Short")
            page.click("#tabs .tab:text-is('Overview')")
            page.wait_for_timeout(1500)
            page.locator(".week tr").nth(1).locator("td.cell").last.click()
            page.wait_for_timeout(1500)
            check(page.locator("#tabs .tab.on").inner_text() == "Medium", "Overview: late-day click opens Medium")
        elif name != "Map":   # W-025: one picker in the top bar drives every region chart on the page
            check(page.locator("#page-field-box").is_visible(), f"{name}: top-bar field picker shown")
            check(page.locator(".grid-stack-item .panel select[data-key=field]").count() == 0, f"{name}: no per-chart field pickers")
            for f in ("wind", "solar", "rain", "temp"):
                page.select_option("#page-field", f)
                page.wait_for_timeout(500)
                fields = page.evaluate("[...window.__weather.panels.values()].filter(p => p.item.opts.region && p.item.kind !== 'map').map(p => p.item.opts.field)")
                check(fields and all(x == f for x in fields), f"{name}: all charts on {f} ({fields})")
                if f == "rain":
                    page.screenshot(path=str(out / f"page_{name.replace(' ', '_')}_rain_{theme}.png"))
            check(not page.locator(".err").count(), f"{name}: error after field changes")
        if name == "Map":
            check(not page.locator("#page-field-box").is_visible(), "Map: no top-bar field picker")
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
