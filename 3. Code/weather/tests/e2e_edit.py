"""Edit mode, like a user would: add a page, add / pick / move / resize / text size / minimise / remove a panel,
copy, rename, delete a page, reset a built-in page. Checks what was saved (/api/layout). Cleans up after itself.

  python tests\\e2e_edit.py http://127.0.0.1:8892 "..\\..\\2. Output\\screenshots"
"""
import json
from pathlib import Path
import sys

from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8892"
out = Path(sys.argv[2] if len(sys.argv) > 2 else "screenshots")
out.mkdir(parents=True, exist_ok=True)
problems, checks = [], 0
T1, T2, T3 = "Test page", "Test page renamed", "Test page copy"


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
    api = lambda name: page.request.get(f"{url}/api/layout/{name}").json()
    for n in (T1, T2, T3):   # leftovers from an earlier failed run
        page.request.delete(f"{url}/api/layout/{n}")
    page.goto(url)
    page.wait_for_timeout(2500)

    # edit mode on
    page.keyboard.press("Control+e")
    page.wait_for_timeout(300)
    check(page.locator("body.editing").count() == 1, "Ctrl+E turns edit mode on")

    # new page
    page.click("#tabs .tab.add")
    page.fill(".modal .field", T1)
    page.click(".modal .ok")
    page.wait_for_timeout(1200)
    check(page.locator(f"#tabs .tab.on:text-is('{T1}')").count() == 1, "new page added and opened")
    check(page.locator("body.empty-page").count() == 1, "new page is empty")

    # add a panel, pick region + field
    page.select_option("#add-panel", "short")
    page.wait_for_timeout(2000)
    panel = page.locator(".grid-stack-item").first
    check(page.locator(".grid-stack-item").count() == 1, "panel added")
    panel.locator("select[data-key=region]").select_option("VIC")
    page.select_option("#page-field", "wind")   # W-025: top-bar picker
    page.wait_for_timeout(1200)
    saved = api(T1)
    it = saved["panels"][0]
    check(it["kind"] == "short" and it["opts"] == {"region": "VIC", "field": "wind"}, f"region + field saved {it.get('opts')}")

    # move it (drag the title bar) and resize it (drag the right edge)
    box = panel.locator(".panel-head").bounding_box()
    x0 = it["x"]
    page.mouse.move(box["x"] + 30, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(box["x"] + 30 + 480, box["y"] + box["height"] / 2 + 160, steps=12)
    page.mouse.up()
    page.wait_for_timeout(1200)
    it = api(T1)["panels"][0]
    check(it["x"] > x0 and it["y"] > 0, f"panel moved to x={it['x']} y={it['y']}")
    w0 = it["w"]
    pb = panel.bounding_box()
    page.mouse.move(pb["x"] + pb["width"] - 2, pb["y"] + pb["height"] / 2)
    page.mouse.down()
    page.mouse.move(pb["x"] + pb["width"] + 240, pb["y"] + pb["height"] / 2, steps=12)
    page.mouse.up()
    page.wait_for_timeout(1200)
    it = api(T1)["panels"][0]
    check(it["w"] > w0, f"panel resized: w {w0} -> {it['w']}")

    # text size, add a map + about
    panel.locator("button:text-is('A+')").click()
    page.wait_for_timeout(900)
    check(api(T1)["panels"][0]["font"] > 1, "A+ bigger text saved")
    page.select_option("#add-panel", "about")
    page.wait_for_timeout(1500)
    check(page.locator(".grid-stack-item").count() == 2, "second panel (A1) added in free space")
    page.screenshot(path=str(out / "edit_mode.png"))

    # minimise, then remove a panel
    page.locator(".grid-stack-item").nth(1).locator("button:text-is('▁')").click()
    page.wait_for_timeout(900)
    check(any(x.get("min") for x in api(T1)["panels"]), "minimise saved")
    page.locator(".grid-stack-item").nth(1).locator("button.remove").click()
    page.wait_for_timeout(900)
    check(len(api(T1)["panels"]) == 1, "panel removed")

    # copy, rename, delete
    page.click("#copy-page")
    page.fill(".modal .field", T3)
    page.click(".modal .ok")
    page.wait_for_timeout(1200)
    check(page.locator(f"#tabs .tab.on:text-is('{T3}')").count() == 1 and len(api(T3)["panels"]) == 1, "page copied")
    page.click("#rename-page")
    page.fill(".modal .field", T2)
    page.click(".modal .ok")
    page.wait_for_timeout(1200)
    names = page.request.get(f"{url}/api/layouts").json()
    check(T2 in names and T3 not in names, "page renamed")
    page.click("#delete-page")
    page.click(".modal .ok")
    page.wait_for_timeout(1200)
    names = page.request.get(f"{url}/api/layouts").json()
    check(T2 not in names and page.locator("#tabs .tab.on:text-is('Short')").count() == 1, "page deleted, back on Short")

    # built-in page: change it, then Reset brings the built-in layout back
    page.locator(".grid-stack-item").first.locator("button.remove").click()
    page.wait_for_timeout(900)
    check(len(api("Short")["panels"]) == 5, "built-in page changed (one panel removed)")
    page.click("#reset-page")
    page.click(".modal .ok")
    page.wait_for_timeout(1500)
    check(len(api("Short")["panels"]) == 6 and page.locator(".grid-stack-item").count() == 6, "Reset puts the built-in layout back")
    page.click("#delete-page")
    page.wait_for_timeout(300)
    check("built-in" in page.locator(".modal p").inner_text(), "built-in page can't be deleted")
    page.keyboard.press("Escape")

    # cleanup: edit mode off, test page gone
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    check(page.locator("body.editing").count() == 0, "Escape leaves edit mode")
    page.request.delete(f"{url}/api/layout/{T1}")
    page.request.delete(f"{url}/api/layout/Short")   # back to the untouched built-in page
    b.close()

print(f"\n{checks} checks")
print("\n".join(problems) if problems else "All OK")
