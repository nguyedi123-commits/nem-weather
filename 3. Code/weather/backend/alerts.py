"""AL Alerts (W-028, card AL): when a new IFS or ensemble run arrives, what changed for days 1–7 against the run before.

IFS -> days 1–3, ensemble (middle) -> days 4–7, as the week grid (W1). Warnings = the I1 rules; big changes = the I1
"Changed since" limits. Saved in data/alerts.json: {"alerts": [one entry per compared run], "done": [...], "seen": time}.
"""
from datetime import datetime, timedelta, timezone
import json
import threading

from . import config as C, insights as I, progress, views
from .ecmwf import parse_run

WARN = {"Hot", "Very hot", "Cold", "Lull", "Windy", "Dull", "Heavy"}   # Wet / Rain likely / Heat risk: too jumpy
NAMES = {"Cold": "Cold night", "Lull": "Wind lull", "Windy": "Strong wind", "Dull": "Dull day", "Heavy": "Heavy rain"}
DAYS = {"ifs": (1, 3), "ens": (4, 7)}
KEEP_DAYS = 7
FRESH_H = 30   # runs older than this are history (a PC catching up after being off), not news
_lock = threading.Lock()


def _file():
    return C.DATA / "alerts.json"


def _load():
    try:
        s = json.loads(_file().read_text())
    except (FileNotFoundError, ValueError):
        s = {}
    return {"alerts": s.get("alerts", []), "done": s.get("done", []), "seen": s.get("seen", "")}


def _save(s):
    tmp = _file().with_suffix(".tmp")
    tmp.write_text(json.dumps(s, indent=1))
    C.replace(tmp, _file())


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _dates(feed):
    today = (datetime.now(timezone.utc) + timedelta(hours=10)).date()   # NEM time
    a, b = DAYS[feed]
    return {(today + timedelta(days=k)).isoformat() for k in range(a, b + 1)}


def _values(feed, rid):
    """{region: {date: {high, low, rain, wind, solar[, rain_chance]}}} – ensemble: the middle of the 50 runs."""
    df = views._cities(feed, rid)
    out = {}
    for r in I.REGIONS:
        x = df[df.region == r]
        if feed == "ens":
            out[r] = {d: {**{k: v[k][1] for k in views.DAILY_KEYS}, "rain_chance": v["rain_chance"]}
                      for d, v in views._ens_daily(x).items()}
        else:
            out[r] = {d: {k: v[k] for k in views.DAILY_KEYS} for d, v in views._det_daily(x).items() if v["hours"] >= 20}
    return out


def _warnings(city, date, v):
    """The warnings that fire on one day: {"heat": bullet, "Lull": bullet, ...} (Hot / Very hot share one slot)."""
    day = I._day(views._day_label(date))
    out = {}
    for b in I._flags(city, day, v.get("high"), v.get("low"), v.get("wind"), v.get("solar"), v.get("rain")):
        name = b.get("tag") or (("Very hot" if b["text"].startswith("Very hot") else "Hot") if b["kind"] == "heat" else None)
        if name in WARN:
            out["heat" if name in ("Hot", "Very hot") else name] = {**b, "name": NAMES.get(name, name)}
    return out


def _detail(b):
    return b["text"].split(": ", 1)[1] if ": " in b["text"] else ""


WIND_SUN = {"Lull", "Windy", "Dull", "wind", "solar"}


def _compare(feed, rid, prev):
    new, old = _values(feed, rid), _values(feed, prev)
    # W-027 switch: one run with farm-area wind / sun, the other with the city -> don't compare wind and sun
    skip = WIND_SUN if views.has_farms(feed, rid) != views.has_farms(feed, prev) else set()
    items = []
    for r in I.REGIONS:
        city = views.CITY[r]
        for d in sorted(_dates(feed) & set(new.get(r, {})) & set(old.get(r, {}))):
            day = I._day(views._day_label(d))
            wn, wo = _warnings(city, d, new[r][d]), _warnings(city, d, old[r][d])
            for key in sorted((set(wn) | set(wo)) - skip):
                n, o = wn.get(key), wo.get(key)
                if n and not o:
                    items.append({"kind": "new", "text": f"{r} {day} – new: {n['name']} ({_detail(n)})",
                                  "price": n.get("price"), "why": n.get("why"), "region": r, "date": d})
                elif o and not n:
                    items.append({"kind": "gone", "text": f"{r} {day} – no longer: {o['name']} (was {_detail(o)})",
                                  "region": r, "date": d})
                elif n["name"] != o["name"]:   # Hot <-> Very hot
                    items.append({"kind": "new" if n["name"] == "Very hot" else "gone",
                                  "text": f"{r} {day} – now {n['name']} (was {o['name']}: {_detail(o)})",
                                  "price": n.get("price"), "why": n.get("why"), "region": r, "date": d})
            for k in [k for k in I.CHANGE if k not in skip]:
                c = I._change(r, day, k, old[r][d].get(k), new[r][d].get(k))
                if c:
                    items.append({"kind": "change", "text": c["text"], "region": r, "date": d})
    order = {"new": 0, "gone": 1, "change": 2}
    return sorted(items, key=lambda x: (x["date"], order[x["kind"]], I.REGIONS.index(x["region"])))


def update():
    """Compare each model's newest run with the one before, once per run. Returns the saved state."""
    with _lock:
        s = _load()
        p = progress.read()
        if p.get("active") and not p.get("stalled"):   # a download is bringing runs in: compare once it has finished
            return s
        changed = False
        for feed in DAYS:
            lst = views.runs(feed)
            if len(lst) < 2 or f"{feed}:{lst[0]}" in s["done"]:
                continue
            rid, prev = lst[0], lst[1]
            if datetime.now(timezone.utc) - parse_run(rid) > timedelta(hours=FRESH_H):
                s["done"] = (s["done"] + [f"{feed}:{rid}"])[-200:]   # old news: no alert
                changed = True
                continue
            try:
                items = _compare(feed, rid, prev)
            except Exception as e:   # never break the screen over alerts
                items = [{"kind": "change", "text": f"Could not compare this run ({str(e)[:80]})", "region": "", "date": ""}]
            mixed = views.has_farms(feed, rid) != views.has_farms(feed, prev)
            s["alerts"].append({"id": f"{feed}:{rid}", "feed": feed, "run": rid, "time": _now(),
                                "title": f"{'IFS' if feed == 'ifs' else 'Ensemble'} {views.run_text(feed, rid)} "
                                         f"vs {views.run_text(feed, prev)} – days {DAYS[feed][0]}–{DAYS[feed][1]}"
                                         + (" (wind / sun not compared: farm areas vs city)" if mixed else ""),
                                "items": items})
            s["done"] = (s["done"] + [f"{feed}:{rid}"])[-200:]
            changed = True
        cut = (datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).isoformat(timespec="seconds")
        if any(a["time"] < cut for a in s["alerts"]):
            s["alerts"] = [a for a in s["alerts"] if a["time"] >= cut]
            changed = True
        if changed:
            _save(s)
        return s


def unseen(s=None):
    s = s or update()
    return sum(len(a["items"]) for a in s["alerts"] if a["time"] > s["seen"])


def view():
    s = update()
    return {"unseen": unseen(s), "seen": s["seen"],
            "runs": [{**a, "new": a["time"] > s["seen"]} for a in sorted(s["alerts"], key=lambda a: a["time"], reverse=True)]}


def mark_seen():
    with _lock:
        s = _load()
        s["seen"] = _now()
        _save(s)
    return {"ok": True}
