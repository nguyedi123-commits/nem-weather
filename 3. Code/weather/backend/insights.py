"""I1 Insights (W-021): plain-words bullets from the numbers each page already shows, by fixed rules (card I1).

insights(page, run, vs) -> {headlines, regions{NSW: [...]}, changes, run_text, vs_text, note}
Each bullet: {"text", "kind" (heat | cold | wind | solar | rain | change | info), "score" (bigger = more important),
              "price" (up | down, W-025 – the direction this weather usually pushes power prices), "why"}.
"""
from datetime import datetime

from . import views

REGIONS = ["NSW", "QLD", "VIC", "SA"]          # TAS left out on purpose (user, 20 Oct)
HEAT = {"Sydney": 32, "Brisbane": 32, "Melbourne": 35, "Adelaide": 36, "Hobart": 30}
COLD = {"Sydney": 8, "Brisbane": 8, "Melbourne": 5, "Adelaide": 5, "Hobart": 3}
LULL, STRONG, DULL, WET, HEAVY, LIKELY = 12, 40, 3.0, 10, 25, 70
UNCERTAIN = 8                                   # °C, width of the 10–90 % range of the high
DISAGREE = {"high": 3, "low": 3, "rain": 5, "wind": 10, "solar": 1.5}
CHANGE = {"high": 2, "low": 2, "rain": 5, "rain_chance": 30, "wind": 10, "solar": 1.5}
LEAN, LEAN_MOVE = 70, 20
NAME = {"high": ("high", "°C", 1), "low": ("low", "°C", 1), "rain": ("rain", "mm", 0), "rain_chance": ("rain chance", "%", 0),
        "wind": ("wind", "km/h", 0), "solar": ("sun", "kWh/m²", 1)}
WORD = {"temp": ("warmer", "cooler"), "rain": ("wetter", "drier"), "wind": ("windier", "calmer"), "solar": ("sunnier", "duller")}


# W-025 price tags (card I1): direction only, with the reason
UP, DOWN = "up", "down"
AIRCON, HEATING = (UP, "more aircon demand"), (UP, "more heating demand")
LESS_WIND, MORE_WIND = (UP, "less wind generation"), (DOWN, "more wind generation")
LESS_SUN = (UP, "less solar by day")
SUMMER, WINTER = {11, 12, 1, 2, 3}, {6, 7, 8}


def _b(text, kind, score, price=None, tag=None):
    b = {"text": text, "kind": kind, "score": round(score, 2)}
    if price:
        b["price"], b["why"] = price
    if tag:   # short word for the W1 week-ahead cells
        b["tag"] = tag
    return b


def _seas_price(field, warmer_etc, months):
    """Price direction for a seasonal lean over `months` ("Oct 2026", ...); None = no clear effect."""
    if field == "wind":
        return MORE_WIND if warmer_etc else LESS_WIND
    if field == "solar":
        return (DOWN, "more solar, mostly midday") if warmer_etc else (UP, "less solar")
    if field == "temp":
        nums = {datetime.strptime(m, "%b %Y").month for m in months}
        if nums & SUMMER:
            return AIRCON if warmer_etc else (DOWN, "less aircon demand")
        if nums & WINTER:
            return (DOWN, "less heating demand") if warmer_etc else HEATING
    return None


def _day(label):   # "Thu 22 Oct" -> "Thu 22"
    return " ".join(label.split()[:2])


def _f(v, d=0):
    return f"{v:.{d}f}"


def _pct_range(vals):
    lo, hi = min(vals), max(vals)
    return f"{lo:.0f} %" if round(lo) == round(hi) else f"{lo:.0f}–{hi:.0f} %"


def _flags(city, day, high=None, low=None, wind=None, solar=None, rain=None, chance=None):
    """The weather rules for one day, one city."""
    out = []
    if high is not None and high >= HEAT[city]:
        very = high >= HEAT[city] + 4
        out.append(_b(f"{'Very hot' if very else 'Hot'} {day}: {_f(high)} °C", "heat", 9 if very else 7, AIRCON))
    if low is not None and low <= COLD[city]:
        out.append(_b(f"Cold night {day}: {_f(low)} °C", "cold", 6, HEATING, "Cold"))
    if wind is not None and wind <= LULL:
        out.append(_b(f"Wind lull {day}: {_f(wind)} km/h at 100 m", "wind", 6, LESS_WIND, "Lull"))
    if wind is not None and wind >= STRONG:
        out.append(_b(f"Strong wind {day}: {_f(wind)} km/h at 100 m", "wind", 6, MORE_WIND, "Windy"))
    if solar is not None and solar <= DULL:
        out.append(_b(f"Dull day {day}: {_f(solar, 1)} kWh/m² of sun", "solar", 4, LESS_SUN, "Dull"))
    if rain is not None and rain >= WET:
        heavy = rain >= HEAVY
        out.append(_b(f"{'Heavy rain' if heavy else 'Wet'} {day}: {_f(rain)} mm", "rain", 8 if heavy else 5, None, "Heavy" if heavy else "Wet"))
    elif chance is not None and chance >= LIKELY:
        out.append(_b(f"Rain likely {day}: {chance:.0f} % chance", "rain", 4, None, "Rain"))
    return out


def _change(region, day, key, old, new):
    if old is None or new is None or abs(new - old) < CHANGE[key]:
        return None
    name, unit, dp = NAME[key]
    c = new - old
    return _b(f"{region} {day} {name} {_f(old, dp)} → {_f(new, dp)}{' ' + unit if unit != '%' else ' %'} ({'+' if c > 0 else ''}{_f(c, dp)})",
              "change", 5 + abs(c) / CHANGE[key])


def _hottest(city, rows, key=lambda r: r["high"]):
    rows = [r for r in rows if key(r) is not None]
    if not rows:
        return []
    r = max(rows, key=key)
    return [_b(f"Hottest {_day(r['day'])}: {_f(key(r))} °C", "info", 1)]


# ---------- per page ----------

def _short(run, vs):
    d = views.short(run, vs)
    if d.get("error"):
        return d
    regions, changes = {}, []
    for r in REGIONS:
        reg = d["regions"][r]
        city = reg["city"]
        rows = [x for x in reg["daily"] if not x["part"]]
        items = _hottest(city, rows)
        for x in rows:
            items += _flags(city, _day(x["day"]), x["high"], x["low"], x["wind"], x["solar"], x["rain"], x.get("rain_chance"))
        regions[r] = items
        old = (reg.get("vs") or {}).get("daily", {})
        for x in rows:
            o = old.get(x["date"])
            if o and o.get("hours", 0) >= 20:
                for k in ("high", "low", "rain"):
                    c = _change(r, _day(x["day"]), k, o.get(k), x.get(k))
                    if c:
                        changes.append(c)
    return {"run_text": f"IFS {d['run_text']}", "vs_text": d.get("vs_text"), "regions": regions, "changes": changes}


def _medium(run, vs):
    d = views.medium(run, vs)
    if d.get("error"):
        return d
    regions, changes = {}, []
    for r in REGIONS:
        reg = d["regions"][r]
        city = reg["city"]
        rows = reg["daily"]
        items = _hottest(city, rows, key=lambda x: x["high"][1])
        for x in rows:
            day = _day(x["day"])
            items += _flags(city, day, x["high"][1], x["low"][1], x["wind"][1], x["solar"][1], x["rain"][1], x["rain_chance"])
            lo, mid, hi = x["high"]
            if hi >= HEAT[city] > mid:
                items.append(_b(f"Heat risk {day}: 1 in 10 runs ≥ {_f(hi)} °C (middle {_f(mid)} °C)", "heat", 5, AIRCON))
            if hi - lo >= UNCERTAIN:
                items.append(_b(f"Uncertain {day}: high anywhere {_f(lo)}–{_f(hi)} °C", "info", 3))
        regions[r] = items
        old = (reg.get("vs") or {}).get("daily", {})
        for x in rows:
            o = old.get(x["date"])
            if not o:
                continue
            for k in ("high", "low", "rain", "wind", "solar"):
                c = _change(r, _day(x["day"]), k, o[k][1], x[k][1])
                if c:
                    changes.append(c)
            c = _change(r, _day(x["day"]), "rain_chance", o["rain_chance"], x["rain_chance"])
            if c:
                changes.append(c)
    return {"run_text": f"Ensemble {d['run_text']}", "vs_text": d.get("vs_text"), "regions": regions, "changes": changes}


def _compare(run, vs):
    d = views.compare()
    if d.get("error"):
        return d
    regions = {}
    for r in REGIONS:
        items = []
        for x in d["regions"][r]["daily"]:
            for k, lim in DISAGREE.items():
                a, b = x[k]
                if a is None or b is None or abs(a - b) < lim:
                    continue
                name, unit, dp = NAME[k]
                items.append(_b(f"Models disagree {_day(x['day'])} {name}: IFS {_f(a, dp)} vs AI {_f(b, dp)} {unit}",
                                "heat" if k == "high" and max(a, b) >= HEAT[d["regions"][r]["city"]] else "info",
                                3 + abs(a - b) / lim))
        if not items:
            items.append(_b("IFS and the AI model agree on every day", "info", 1))
        regions[r] = items
    changes, vs_text = [], None
    for model, label in (("ifs", "IFS"), ("aifs", "AI")):
        ch = views.changes(model, "latest", vs)
        vs_text = vs_text or ch.get("vs_text")
        for row in ch.get("rows", []):
            if row["region"] in REGIONS:
                for it in row["items"]:
                    key = next(k for k, v in NAME.items() if v[0] == it["what"].lower())
                    c = _change(f"{label} {row['region']}", _day(row["day"]), key, it["old"], it["new"])
                    if c:
                        changes.append(c)
    return {"run_text": f"IFS {d['runs']['ifs']} · AI {d['runs']['aifs']}", "vs_text": vs_text, "regions": regions, "changes": changes}


def _seasonal(run, vs):
    d = views.seasonal(run, vs)
    if d.get("error"):
        return d
    regions, changes = {}, []
    for r in REGIONS:
        reg = d["regions"][r]
        items = []
        for field, (up, down) in WORD.items():
            q = reg.get(field)
            if not q:
                continue
            others = [(name, (reg.get(key) or {}).get(field)) for key, name in (("bom", "BOM"), ("cfs", "CFS"))]
            others = [(name, b) for name, b in others if b]
            runs_ = []   # consecutive months leaning the same way
            for i, m in enumerate(reg["months"]):
                a = q["above"][i]
                lean = up if a >= LEAN else down if a <= 100 - LEAN else None
                if lean and runs_ and runs_[-1][0] == lean and runs_[-1][2] == i - 1:
                    runs_[-1][2] = i
                elif lean:
                    runs_.append([lean, i, i])
            for lean, i0, i1 in runs_:
                ms = reg["months"][i0][:3] + ("" if i0 == i1 else "–" + reg["months"][i1][:3])
                ch = [q["above"][i] for i in range(i0, i1 + 1)]
                txt = (f"{ms} {lean} than normal (ECMWF {_pct_range(ch)} of runs)" if lean == up
                       else f"{ms} {lean} than normal (ECMWF: only {_pct_range(ch)} of runs above normal)")
                agree = 0
                for name, b in others:
                    bc = [b["above"][i] for i in range(i0, i1 + 1)]
                    same = all((x >= LEAN) if lean == up else (x <= 100 - LEAN) for x in bc)
                    other = all((x <= 100 - LEAN) if lean == up else (x >= LEAN) for x in bc)
                    agree += same
                    txt += (f", {name} agrees" if same else f", {name} disagrees ({_pct_range(bc)})" if other
                            else f", {name} less sure ({_pct_range(bc)})")
                kind = {"temp": "heat" if lean == up else "cold", "rain": "rain", "wind": "wind", "solar": "solar"}[field]
                items.append(_b(txt, kind, 4 + (i1 - i0) + agree, _seas_price(field, lean == up, reg["months"][i0:i1 + 1])))
            old = (reg.get("vs") or {}).get(field)
            if old:
                for i, m in enumerate(reg["months"]):
                    if m in reg["vs"]["months"]:
                        o = old["above"][reg["vs"]["months"].index(m)]
                        n = q["above"][i]
                        if abs(n - o) >= LEAN_MOVE:
                            changes.append(_b(f"{r} {m[:3]} chance {up} {o:.0f} → {n:.0f} %", "change", 5 + abs(n - o) / LEAN_MOVE))
        regions[r] = items or [_b("No clear lean – close to normal", "info", 1)]
    return {"run_text": f"{d['issue_text']} forecast", "vs_text": d.get("vs_text"), "regions": regions, "changes": changes}


# ---------- W1 Week ahead (W-026, card W1): the same rules, one cell per state and day ----------

def _cell(city, date, src, high, low, wind, solar, rain, chance, risk=False):
    day = _day(views._day_label(date))
    flags = _flags(city, day, high, low, wind, solar, rain, chance)
    if risk:
        flags.append(_b(f"Heat risk {day}", "heat", 5, AIRCON, "Risk"))
    h = HEAT[city]
    level = ("vhot" if high is not None and high >= h + 4 else "hot" if high is not None and high >= h
             else "warm" if high is not None and high >= h - 4 else "cold" if low is not None and low <= COLD[city] else "mild")
    ups = sorted({b["why"] for b in flags if b.get("price") == UP})
    downs = sorted({b["why"] for b in flags if b.get("price") == DOWN})
    price = "both" if ups and downs else UP if ups else DOWN if downs else None
    return {"src": src, "high": high, "low": low, "wind": wind, "solar": solar, "rain": rain, "chance": chance,
            "level": level, "tags": [b["tag"] for b in flags if b.get("tag")], "price": price, "up": ups, "down": downs}


def week():
    s, m = views.short(), views.medium()
    if s.get("error") and m.get("error"):
        return {"error": s["error"]}
    days, regions = {}, {}
    for r in REGIONS:
        cells = {}
        reg = (s.get("regions") or {}).get(r)
        if reg:
            for x in [x for x in reg["daily"] if not x["part"]][:3]:   # days 1–3: IFS
                cells[x["date"]] = _cell(reg["city"], x["date"], "IFS", x["high"], x["low"], x["wind"], x["solar"],
                                         x["rain"], x.get("rain_chance"))
        mreg = (m.get("regions") or {}).get(r)
        if mreg:
            last = max(cells) if cells else ""
            for x in mreg["daily"]:   # after that: ensemble middle (+ heat risk from the top of the range)
                if x["date"] > last and len(cells) < 15:
                    lo, mid, hi = x["high"]
                    cells[x["date"]] = _cell(mreg["city"], x["date"], "Ens", mid, x["low"][1], x["wind"][1], x["solar"][1],
                                             x["rain"][1], x["rain_chance"], risk=hi >= HEAT[mreg["city"]] > mid)
        regions[r] = {"city": (reg or mreg or {}).get("city"), "cells": cells}
        for d, c in cells.items():
            days.setdefault(d, c["src"])
    run = " · ".join(t for t in (f"IFS {s['run_text']}" if s.get("run_text") else "",
                                 f"Ensemble {m['run_text']}" if m.get("run_text") else "") if t)
    return {"run_text": run, "regions": regions,
            "days": [{"date": d, "label": _day(views._day_label(d)), "src": src} for d, src in sorted(days.items())][:15]}


PAGES = {"short": _short, "medium": _medium, "compare": _compare, "seasonal": _seasonal}


def insights(page="short", run="latest", vs="auto"):
    out = PAGES.get(page, _short)(run, vs)
    if out.get("error"):
        return out
    pool = [{**b, "text": f"{r} · {b['text']}"} for r, items in out["regions"].items() for b in items if b["kind"] != "info"]
    pool += out["changes"]
    out["headlines"] = sorted(pool, key=lambda b: -b["score"])[:5]
    for r in out["regions"]:   # most important first, at most 6 per region
        out["regions"][r] = sorted(out["regions"][r], key=lambda b: -b["score"])[:6]
    out["changes"] = sorted(out["changes"], key=lambda b: -b["score"])[:10]
    out["page"] = page
    if not out.get("vs_text"):
        out["note"] = "No earlier run on disk to compare with yet – each refresh adds one."
    return out
