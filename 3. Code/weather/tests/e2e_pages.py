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
PAGES = {"Overview": 3, "Short": 6, "Medium": 6, "Seasonal": 6, "Map": 2, "Check": 4}   # AI vs IFS removed 23 Oct (W-025); Overview W-026
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
        elif name == "Check":   # W-014: forecast check – 4 models, every measure draws
            f1 = page.locator(".grid-stack-item .panel").first
            page.wait_for_selector(".grid-stack-item .panel .table table", timeout=20000)   # first calculation takes a few s
            check(f1.locator(".table tr").count() == 5, "Check: 4 model rows + head")
            for mv in ("low", "rain", "sun", "high"):
                f1.locator("select[data-key=measure]").select_option(mv)
                page.wait_for_timeout(500)
                if mv == "rain":
                    page.screenshot(path=str(out / f"page_Check_rain_{theme}.png"))
            check(not page.locator(".err").count(), "Check: no error after measure changes")
            check(not page.locator("#page-field-box").is_visible(), "Check: no top-bar field picker")
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

    # W-029 linked charts: hover one chart -> value boxes on all four; click a day -> highlighted on every page
    page.click("#tabs .tab:text-is('Short')")
    page.wait_for_timeout(1500)
    box = page.locator(".grid-stack-item .chart").first.bounding_box()
    page.mouse.move(box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.5)
    page.wait_for_timeout(800)
    tips = page.evaluate("""[...document.querySelectorAll('.grid-stack-item .chart > div')].filter(d => d.style.zIndex === '9999999' && d.style.display !== 'none' && d.style.opacity !== '0').length""")
    check(tips >= 4, f"hover: value boxes on all 4 charts ({tips})")
    row = page.locator(".grid-stack-item .table tr[data-date]").nth(1)
    date = row.get_attribute("data-date")
    row.click()
    page.wait_for_timeout(1200)
    check(page.locator("#day-chip").is_visible(), "click a day: Day chip shown")
    check(page.locator(f".table tr.dayon[data-date='{date}']").count() == 4, "click a day: row highlighted on all 4 panels")
    page.screenshot(path=str(out / f"linked_day_short_{theme}.png"))
    page.click("#tabs .tab:text-is('Overview')")
    page.wait_for_timeout(1500)
    check(page.locator(f".week td.cell.dayon[data-date='{date}']").count() == 4, "highlighted day outlined in the week grid")
    page.keyboard.press("Escape")
    page.wait_for_timeout(600)
    check(not page.locator("#day-chip").is_visible() and page.locator(".week td.cell.dayon").count() == 0, "Esc clears the day")
    page.locator(".week tr").nth(1).locator("td.cell").last.click()
    page.wait_for_timeout(1800)
    check(page.locator("#tabs .tab.on").inner_text() == "Medium" and page.locator(".table tr.dayon").count() == 4,
          "week-grid click opens Medium with that day highlighted")
    page.screenshot(path=str(out / f"linked_day_medium_{theme}.png"))
    page.locator("#day-chip button").click()
    page.wait_for_timeout(500)

    # W-030 keyboard: 1-5 pages, T/R/S/W field, arrows move the day, ? = key list
    page.keyboard.press("2")
    page.wait_for_timeout(1500)
    check(page.locator("#tabs .tab.on").inner_text() == "Short", "key 2 opens Short")
    page.keyboard.press("r")
    page.wait_for_timeout(600)
    check(page.locator("#page-field").input_value() == "rain", "key R shows rain")
    page.keyboard.press("t")
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(800)
    check(page.locator("#day-chip").is_visible() and page.locator(".table tr.dayon").count() == 4, "→ highlights a day")
    page.keyboard.press("Escape")
    page.keyboard.press("?")
    page.wait_for_timeout(500)
    check("Keyboard" in page.locator(".modal h3").inner_text(), "? shows the key list")
    page.keyboard.press("Escape")

    # W-030 map: click the Sydney dot -> Short or Medium with the map's day highlighted, NSW chart flashing
    page.keyboard.press("5")
    page.wait_for_timeout(2500)
    m = page.locator(".grid-stack-item .chart").first
    mb = m.bounding_box()
    xy = page.evaluate("""() => { const el = document.querySelector('.grid-stack-item .chart');
        const c = echarts.getInstanceByDom(el); const o = c.getOption(); const s = o.series[2].data.find(d => d.name === 'Sydney');
        return c.convertToPixel({ seriesIndex: 2 }, s.value); }""")
    page.mouse.click(mb["x"] + xy[0], mb["y"] + xy[1])
    page.wait_for_timeout(1800)
    on = page.locator("#tabs .tab.on").inner_text()
    check(on in ("Short", "Medium") and page.locator("#day-chip").is_visible(), f"map city click opens {on} with the day highlighted")
    check(page.locator(".panel.flash").count() == 1, "the NSW chart flashes")
    page.screenshot(path=str(out / f"map_click_{theme}.png"))
    page.keyboard.press("Escape")

    # W-028 alerts: button in the top bar, list opens, "Mark all seen" clears the dot
    page.wait_for_timeout(5500)   # one status poll
    check(page.locator("#alerts").is_visible(), "Alerts button shown")
    page.click("#alerts")
    page.wait_for_timeout(1200)
    check("Alerts" in page.locator(".modal h3").inner_text(), "alert list opens")
    page.screenshot(path=str(out / f"alerts_{theme}.png"))
    page.click(".modal .ok")
    page.wait_for_timeout(800)
    check(page.locator("#alerts .badge").is_hidden(), "Mark all seen clears the red dot")
    b.close()

print(f"{checks} checks, screenshots in {out}")
print("\n".join(problems) if problems else "All OK – no page errors")
