"""Compare runs (W-017): run / vs pickers on S1, M1, L1, G1 and the D1 "What changed" panel. Uses the runs on disk.

  python tests\\e2e_runs.py http://127.0.0.1:8892 "..\\..\\2. Output\\screenshots"
"""
from pathlib import Path
import sys

from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8892"
out = Path(sys.argv[2] if len(sys.argv) > 2 else "screenshots")
out.mkdir(parents=True, exist_ok=True)
problems, checks = [], 0
TEST = "Test runs"


def check(ok, what):
    global checks
    checks += 1
    print(("ok   " if ok else "FAIL ") + what)
    if not ok:
        problems.append(what)


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge")
    page = b.new_page(viewport={"width": 1920, "height": 1080})
    page.on("pageerror", lambda e: problems.append(f"page error: {e}"))
    runs = page.request.get(f"{url}/api/runs").json()
    print("IFS runs on disk:", [r["text"] for r in runs["ifs"]])
    page.request.delete(f"{url}/api/layout/{TEST}")
    page.goto(url)
    page.wait_for_timeout(2500)

    # S1 on the Short page: vs auto -> dashed line + Change column
    page.click("#tabs .tab:text-is('Short')")
    page.wait_for_timeout(2000)
    s1 = page.locator(".grid-stack-item").first
    check(s1.locator("select.run-pick.run").count() == 1 and s1.locator("select.run-pick.vs").count() == 1, "S1 has run + vs pickers")
    check("Change vs" in s1.locator(".table").inner_text(), "S1 table has a Change column (vs auto)")
    page.screenshot(path=str(out / "runs_S1_vs_auto.png"))
    s1.locator("select.run-pick.vs").select_option("none")
    page.wait_for_timeout(1200)
    check("Change vs" not in s1.locator(".table").inner_text(), "vs none: no Change column")
    oldest = runs["ifs"][-1]["id"]
    s1.locator("select.run-pick.vs").select_option(oldest)
    page.wait_for_timeout(1500)
    check("Change vs" in s1.locator(".table").inner_text(), f"vs picked run {oldest}: Change column back")
    s1.locator("select.run-pick.run").select_option(runs["ifs"][1]["id"])
    page.wait_for_timeout(1500)
    check(s1.locator("select.run-pick.run").input_value() == runs["ifs"][1]["id"], "older run picked for S1")
    page.screenshot(path=str(out / "runs_S1_older_run.png"))

    # M1 / L1: only one run on disk -> pickers say so, no error
    for name in ("Medium", "Seasonal"):
        page.click(f"#tabs .tab:text-is('{name}')")
        page.wait_for_timeout(1800)
        check(not page.locator(".err").count(), f"{name}: no error with a single run on disk")

    # new page with D1 + map (change map)
    page.keyboard.press("Control+e")
    page.click("#tabs .tab.add")
    page.fill(".modal .field", TEST)
    page.click(".modal .ok")
    page.wait_for_timeout(1200)
    page.select_option("#add-panel", "changes")
    page.wait_for_timeout(1500)
    d1 = page.locator(".grid-stack-item").first
    d1.locator("select[data-key=model]").select_option("ifs")
    page.wait_for_timeout(1800)
    txt = d1.locator(".changes").inner_text()
    check("Region" in txt or "No big changes" in txt, "D1 shows changes (IFS)")
    d1.locator("select[data-key=model]").select_option("ens")
    page.wait_for_timeout(1500)
    t = d1.locator(".changes").inner_text()
    check("No earlier run" in t or "Region" in t or "No big changes" in t, "D1 ensemble: changes, or 'no earlier run yet'")
    d1.locator("select[data-key=model]").select_option("ifs")
    page.wait_for_timeout(1200)
    page.select_option("#add-panel", "map")
    page.wait_for_timeout(2500)
    mp = page.locator(".grid-stack-item").nth(1)
    mp.locator("select.run-pick.vs").select_option("auto")
    page.wait_for_timeout(2500)
    note = mp.locator(".m-note").inner_text()
    check("Change map" in note or "doesn't cover" in note, f"map: change map on ({note[:60]})")
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)
    page.screenshot(path=str(out / "runs_D1_and_change_map.png"))
    page.request.delete(f"{url}/api/layout/{TEST}")
    page.request.delete(f"{url}/api/layout/Short")
    b.close()

print(f"\n{checks} checks")
print("\n".join(problems) if problems else "All OK")
