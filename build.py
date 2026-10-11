#!/usr/bin/env python3
"""Fetch Open-Meteo + NOAA, plan 3 outings, inline into dist/weekend-gameplan.html."""
import json
import os
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
ET = ZoneInfo("America/New_York")
STATION = "8575512"
# Millersville, MD 21108
LAT, LON = 39.0596, -76.6477


def rd(rel):
    with open(os.path.join(HERE, rel), encoding="utf-8") as f:
        return f.read()


def upcoming_weekend(now):
    """Return Fri/Sat/Sun dates for the upcoming weekend (this week if before Fri end, else next)."""
    # weekday: Mon=0 … Sun=6
    wd = now.weekday()
    # days until Friday
    days_to_fri = (4 - wd) % 7
    if wd == 4:
        days_to_fri = 0
    elif wd > 4:
        # Sat/Sun → next Friday
        days_to_fri = (4 - wd) % 7
        if days_to_fri == 0:
            days_to_fri = 7
    fri = (now + timedelta(days=days_to_fri)).date()
    return [fri, fri + timedelta(days=1), fri + timedelta(days=2)]


def wmo_label(code):
    code = int(code)
    table = {
        0: ("Clear", "☀️"),
        1: ("Mostly clear", "🌤️"),
        2: ("Partly cloudy", "⛅"),
        3: ("Overcast", "☁️"),
        45: ("Fog", "🌫️"),
        48: ("Rime fog", "🌫️"),
        51: ("Light drizzle", "🌦️"),
        53: ("Drizzle", "🌦️"),
        55: ("Heavy drizzle", "🌧️"),
        61: ("Light rain", "🌧️"),
        63: ("Rain", "🌧️"),
        65: ("Heavy rain", "🌧️"),
        66: ("Freezing rain", "🧊"),
        67: ("Heavy freezing rain", "🧊"),
        71: ("Light snow", "🌨️"),
        73: ("Snow", "🌨️"),
        75: ("Heavy snow", "❄️"),
        77: ("Snow grains", "🌨️"),
        80: ("Rain showers", "🌦️"),
        81: ("Showers", "🌧️"),
        82: ("Heavy showers", "🌧️"),
        85: ("Snow showers", "🌨️"),
        86: ("Heavy snow showers", "❄️"),
        95: ("Thunderstorm", "⛈️"),
        96: ("Thunder + hail", "⛈️"),
        99: ("Severe storm", "⛈️"),
    }
    return table.get(code, (f"Code {code}", "🌡️"))


def c_to_f(c):
    return round(c * 9 / 5 + 32, 1)


def kmh_to_mph(k):
    return round(k * 0.621371, 1)


def mm_to_in(mm):
    return round(mm / 25.4, 2)

def fmt_hm_12(iso_or_hm):
    """Format 'HH:MM' or '...THH:MM' as 12-hour clock."""
    s = str(iso_or_hm)
    if "T" in s:
        s = s.split("T", 1)[1]
    s = s[:5]
    h, m = map(int, s.split(":"))
    ap = "PM" if h >= 12 else "AM"
    h = h % 12 or 12
    return f"{h}:{m:02d} {ap}"




def noaa_url(product, begin, end, interval):
    return (
        "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
        f"?product={product}&application=WeekendGameplan"
        f"&begin_date={begin}&end_date={end}&datum=MLLW&station={STATION}"
        f"&time_zone=lst_ldt&units=english&interval={interval}&format=json"
    )


def fetch_weather(days):
    # Need enough forecast days to cover the weekend
    now = datetime.now(ET)
    last = days[-1]
    span = (last - now.date()).days + 2
    forecast_days = max(3, min(16, span + 1))
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,"
        "precipitation_sum,precipitation_probability_max,sunrise,sunset,wind_speed_10m_max"
        "&hourly=temperature_2m,precipitation_probability,weather_code"
        f"&timezone=America%2FNew_York&forecast_days={forecast_days}"
    )
    with urllib.request.urlopen(url, timeout=18) as r:
        raw = json.loads(r.read().decode())
    daily = raw["daily"]
    by_date = {}
    for i, t in enumerate(daily["time"]):
        d = t[:10]
        code = daily["weather_code"][i]
        label, icon = wmo_label(code)
        by_date[d] = {
            "date": d,
            "weather_code": code,
            "label": label,
            "icon": icon,
            "temp_max_f": c_to_f(daily["temperature_2m_max"][i]),
            "temp_min_f": c_to_f(daily["temperature_2m_min"][i]),
            "precip_in": mm_to_in(daily["precipitation_sum"][i]),
            "precip_prob": daily["precipitation_probability_max"][i],
            "sunrise": daily["sunrise"][i],
            "sunset": daily["sunset"][i],
            "wind_mph": kmh_to_mph(daily["wind_speed_10m_max"][i]),
        }
    return {
        "source": "Open-Meteo",
        "live": True,
        "location": {
            "name": "Millersville, MD 21108",
            "lat": LAT,
            "lon": LON,
            "near": "Annapolis / Chesapeake Bay",
        },
        "units": {"temp": "°F", "precip": "in", "wind": "mph"},
        "by_date": by_date,
        "raw_timezone": raw.get("timezone", "America/New_York"),
    }


def fetch_tides(days):
    begin = days[0].strftime("%Y%m%d")
    end = days[-1].strftime("%Y%m%d")
    with urllib.request.urlopen(noaa_url("predictions", begin, end, "hilo"), timeout=18) as r:
        hilo = json.loads(r.read().decode())
    extremes = [
        {"t": p["t"], "v": round(float(p["v"]), 3), "type": p["type"]}
        for p in hilo.get("predictions", [])
    ]
    if not extremes:
        raise RuntimeError("empty NOAA predictions")
    by_date = {}
    for e in extremes:
        d = e["t"][:10]
        by_date.setdefault(d, []).append(e)
    return {
        "source": "NOAA CO-OPS",
        "live": True,
        "station": {
            "id": STATION,
            "name": "Annapolis, MD",
            "lat": 38.9833,
            "lon": -76.4800,
            "datum": "MLLW",
            "units": "feet",
        },
        "extremes": extremes,
        "by_date": by_date,
    }


SPOTS = {
    "fishing": [
        {
            "id": "jonas-green",
            "name": "Jonas Green Park",
            "area": "Annapolis",
            "drive_min": 18,
            "why": "Free fishing pier on the Severn with easy parking and restrooms.",
            "kids": True,
            "best": "incoming tide / dusk",
            "tip": "Cast for white perch and spot near the bridge abutments.",
        },
        {
            "id": "sandy-point",
            "name": "Sandy Point State Park",
            "area": "Skidmore",
            "drive_min": 22,
            "why": "Bay beach, jetties, and a classic Chesapeake horizon.",
            "kids": True,
            "best": "morning flood / late afternoon",
            "tip": "State park entry fee; check wind — whitecaps mean tough casting.",
        },
        {
            "id": "fort-smallwood",
            "name": "Fort Smallwood Park",
            "area": "Pasadena",
            "drive_min": 20,
            "why": "Rock walls + pier access with picnic tables for a family base camp.",
            "kids": True,
            "best": "two hours before high",
            "tip": "Bring sweatshirts for the evening breeze off the Patapsco.",
        },
    ],
    "trails": [
        {
            "id": "kinder-farm",
            "name": "Kinder Farm Park",
            "area": "Millersville",
            "drive_min": 8,
            "why": "Home-base trails, farm animals, playgrounds — Char & Vic territory.",
            "kids": True,
            "best": "morning / golden hour",
            "tip": "Loop the Farm Trail then hit the playground before sunset.",
        },
        {
            "id": "quiet-waters",
            "name": "Quiet Waters Park",
            "area": "Annapolis",
            "drive_min": 20,
            "why": "Wooded paths, South River overlooks, sculptures, and a big playground.",
            "kids": True,
            "best": "late afternoon",
            "tip": "Walk to the overlook for sunset colors on the river.",
        },
        {
            "id": "downs-park",
            "name": "Downs Park",
            "area": "Pasadena",
            "drive_min": 18,
            "why": "Bay cliffs, boardwalk, and open fields for a frisbee cooldown.",
            "kids": True,
            "best": "midday to dusk",
            "tip": "Cliff trail can be breezy — great for kite days.",
        },
    ],
    "wildlife": [
        {
            "id": "patuxent-north",
            "name": "Patuxent Research Refuge — North Tract",
            "area": "Laurel / Bowie edge",
            "drive_min": 28,
            "why": "Wildlife driving loop and quiet trails; deer, waterfowl, and big sky.",
            "kids": True,
            "best": "morning",
            "tip": "Visitor contact station hours vary — pack binoculars.",
        },
        {
            "id": "downs-wildlife",
            "name": "Downs Park · bay overlook",
            "area": "Pasadena",
            "drive_min": 18,
            "why": "Easy cliff-top birding and Bay views — short hop for Char & Vic.",
            "kids": True,
            "best": "morning / dusk",
            "tip": "Bring binoculars; watch for osprey over the water.",
        },
        {
            "id": "jug-bay",
            "name": "Jug Bay Wetlands Sanctuary",
            "area": "Lothian",
            "drive_min": 30,
            "why": "Marsh boardwalks and Patuxent River overlooks for birding.",
            "kids": False,
            "best": "morning / outgoing tide",
            "tip": "Closed Mondays; wear boots after rain.",
        },
        {
            "id": "cbec",
            "name": "Chesapeake Bay Environmental Center",
            "area": "Grasonville",
            "drive_min": 40,
            "why": "Marsh trails, raptors, and Eastern Shore vibes across the Bay Bridge.",
            "kids": True,
            "best": "late morning",
            "tip": "Combine with a Kent Narrows snack stop.",
        },
    ],
    "rain": [
        {
            "id": "annapolis-maritime",
            "name": "Annapolis Maritime Museum",
            "area": "Eastport",
            "drive_min": 22,
            "why": "Hands-on bay exhibits under a roof when the sky opens up.",
            "kids": True,
            "best": "any rainy window",
            "tip": "Check weekend hours; pair with hot cocoa in Eastport.",
        },
        {
            "id": "maryland-hall",
            "name": "Maryland Hall / West Street stroll",
            "area": "Annapolis",
            "drive_min": 20,
            "why": "Indoor arts + covered café hops without a long drive.",
            "kids": True,
            "best": "afternoon",
            "tip": "Look for family workshops on the weekend calendar.",
        },
        {
            "id": "home-base",
            "name": "Home base · Millersville",
            "area": "777 Springbloom vibes",
            "drive_min": 0,
            "why": "Board games, movie marathon, and a backyard porch rainwatch.",
            "kids": True,
            "best": "peak rain hours",
            "tip": "Stock popcorn; save parks for the next clear break.",
        },
    ],
}


def pick_spot(kind, prefer_kids, rainy, windy):
    pool = list(SPOTS[kind])
    if prefer_kids:
        kid_first = [s for s in pool if s.get("kids")]
        if kid_first:
            pool = kid_first
        # Kids mode: closer parks first (playground / short hops)
        pool = sorted(pool, key=lambda s: (s["drive_min"], s["name"]))
    elif rainy or windy:
        pool = sorted(pool, key=lambda s: s["drive_min"])
    return pool[0], pool


def score_day(wx, tides):
    """Higher = better outdoor day."""
    if not wx:
        return 0
    score = 50
    score -= min(40, (wx.get("precip_prob") or 0) * 0.4)
    score -= min(20, (wx.get("precip_in") or 0) * 25)
    code = wx.get("weather_code", 3)
    if code == 0:
        score += 18
    elif code in (1, 2):
        score += 12
    elif code == 3:
        score += 4
    elif code >= 61:
        score -= 25
    wind = wx.get("wind_mph") or 0
    if wind > 20:
        score -= 12
    elif wind > 14:
        score -= 5
    # Mild fall temps are a plus
    hi = wx.get("temp_max_f") or 70
    if 55 <= hi <= 78:
        score += 8
    elif hi < 45 or hi > 88:
        score -= 8
    # Tide range bonus for fishing days
    if tides:
        vals = [e["v"] for e in tides]
        if vals:
            rng = max(vals) - min(vals)
            if rng >= 1.2:
                score += 4
    return round(score, 1)


def plan_outings(weekend_days, weather, tides, prefer_kids=False):
    plans = []
    kinds_cycle = ["fishing", "trails", "wildlife"]
    day_meta = []
    for i, d in enumerate(weekend_days):
        key = d.isoformat()
        wx = weather["by_date"].get(key)
        td = tides["by_date"].get(key, [])
        rainy = bool(wx and ((wx.get("precip_prob") or 0) >= 55 or (wx.get("precip_in") or 0) >= 0.25))
        windy = bool(wx and (wx.get("wind_mph") or 0) >= 18)
        sc = score_day(wx, td)
        day_meta.append(
            {
                "date": key,
                "weekday": d.strftime("%A"),
                "short": f"{d.strftime('%a')} {d.day}",
                "weather": wx,
                "tides": td,
                "score": sc,
                "rainy": rainy,
                "windy": windy,
            }
        )

    # Assign best kinds to best days (fishing loves tide + lower wind)
    ranked = sorted(range(3), key=lambda i: day_meta[i]["score"], reverse=True)
    assigned = {}
    remaining = kinds_cycle[:]
    # Prefer fishing on the day with biggest tide swing and not too rainy
    best_fish = max(
        range(3),
        key=lambda i: (
            0
            if day_meta[i]["rainy"]
            else (
                (max((e["v"] for e in day_meta[i]["tides"]), default=0)
                 - min((e["v"] for e in day_meta[i]["tides"]), default=0))
                - (day_meta[i]["weather"] or {}).get("wind_mph", 0) * 0.05
                + day_meta[i]["score"] * 0.01
            )
        ),
    )
    assigned[best_fish] = "fishing"
    remaining.remove("fishing")
    for i in ranked:
        if i in assigned:
            continue
        # wildlife on clearer higher-score days; trails otherwise
        if day_meta[i]["score"] >= 55 and "wildlife" in remaining:
            assigned[i] = "wildlife"
            remaining.remove("wildlife")
        elif "trails" in remaining:
            assigned[i] = "trails"
            remaining.remove("trails")
        else:
            assigned[i] = remaining.pop(0)

    for i, d in enumerate(weekend_days):
        kind = assigned[i]
        meta = day_meta[i]
        spot, alts = pick_spot(kind, prefer_kids, meta["rainy"], meta["windy"])
        wx = meta["weather"]
        sunset = None
        if wx and wx.get("sunset"):
            sunset = wx["sunset"]  # ISO local
        window = spot["best"]
        if kind == "fishing" and meta["tides"]:
            highs = [e for e in meta["tides"] if e["type"] == "H"]
            if highs:
                # Prefer daytime/evening high (6am–8pm), else soonest high
                def tide_hour(e):
                    return int(e["t"][11:13])
                day_highs = [e for e in highs if 6 <= tide_hour(e) <= 20]
                pick = day_highs[0] if day_highs else highs[0]
                window = (
                    f"around high tide {fmt_hm_12(pick['t'][11:])} "
                    f"({pick['v']} ft MLLW)"
                )
        elif kind in ("trails", "wildlife") and sunset:
            window = f"aim for golden hour before sunset {fmt_hm_12(sunset)}"

        title = {
            "fishing": "Bay fishing run",
            "trails": "Trail + playground loop",
            "wildlife": "Wildlife / marsh morning",
        }[kind]

        plans.append(
            {
                "id": f"plan-{kind}-{meta['date']}",
                "day_index": i,
                "date": meta["date"],
                "weekday": meta["weekday"],
                "kind": kind,
                "title": title,
                "spot": spot,
                "alternates": [a for a in alts if a["id"] != spot["id"]][:2],
                "weather": wx,
                "tides": meta["tides"],
                "score": meta["score"],
                "window": window,
                "rainy": meta["rainy"],
                "kids_mode": prefer_kids,
                "blurb": _blurb(kind, spot, wx, meta),
            }
        )

    # Rainy-day backup: pick rain spot based on worst precip day
    worst = max(day_meta, key=lambda m: (m["weather"] or {}).get("precip_prob") or 0)
    rain_spot, rain_alts = pick_spot("rain", True, True, False)
    backup = {
        "id": "rain-backup",
        "title": "Rainy-day backup",
        "trigger_day": worst["date"],
        "trigger_weekday": worst["weekday"],
        "trigger_prob": (worst["weather"] or {}).get("precip_prob"),
        "spot": rain_spot,
        "alternates": [a for a in rain_alts if a["id"] != rain_spot["id"]][:2],
        "blurb": (
            f"If {worst['weekday']}'s precip odds hold "
            f"({(worst['weather'] or {}).get('precip_prob', '—')}%), "
            f"pivot to {rain_spot['name']} instead of forcing a soaked trail."
        ),
    }
    return plans, backup, day_meta


def _blurb(kind, spot, wx, meta):
    bits = [f"{spot['name']} ({spot['area']}, ~{spot['drive_min']} min)."]
    if wx:
        bits.append(
            f"{meta['weekday']}: {wx['icon']} {wx['label']}, "
            f"{wx['temp_min_f']:.0f}–{wx['temp_max_f']:.0f}°F, "
            f"{wx['precip_prob']}% precip."
        )
    if kind == "fishing":
        bits.append(spot["tip"])
    elif kind == "trails":
        bits.append("Pack water bottles and a light layer for Char & Vic.")
    else:
        bits.append("Binoculars optional; quiet voices near the marsh.")
    return " ".join(bits)


def build_payload(prefer_kids=False):
    now = datetime.now(ET)
    days = upcoming_weekend(now)
    try:
        weather = fetch_weather(days)
        tides = fetch_tides(days)
        live = True
        source_note = "Live Open-Meteo weather + NOAA Annapolis tides"
    except Exception as ex:
        print(f"Live fetch failed ({ex}); using demo fallback")
        return load_demo()

    plans, backup, day_meta = plan_outings(days, weather, tides, prefer_kids=False)
    plans_kids, backup_kids, _ = plan_outings(days, weather, tides, prefer_kids=True)

    payload = {
        "source": source_note,
        "live": live,
        "fetched_at": now.isoformat(timespec="seconds"),
        "timezone": "America/New_York",
        "home": {
            "label": "Boyd family · Millersville MD 21108",
            "lat": LAT,
            "lon": LON,
        },
        "weekend": {
            "friday": days[0].isoformat(),
            "saturday": days[1].isoformat(),
            "sunday": days[2].isoformat(),
            "label": f"{days[0].strftime('%a')} {days[0].day}–{days[2].strftime('%a')} {days[2].day} {days[2].strftime('%b %Y')}",
        },
        "weather": weather,
        "tides": tides,
        "days": day_meta,
        "plans": plans,
        "plans_kids": plans_kids,
        "backup": backup,
        "backup_kids": backup_kids,
        "spots_catalog": SPOTS,
        "note": (
            "Outing suggestions combine forecast + Annapolis tides with local public parks. "
            "Always verify park hours, fees, and conditions before you go."
        ),
    }
    return payload


def load_demo():
    demo_path = os.path.join(HERE, "data", "gameplan-demo.json")
    if os.path.isfile(demo_path):
        with open(demo_path, encoding="utf-8") as f:
            data = json.load(f)
        data["live"] = False
        if "EXAMPLE" not in data.get("source", ""):
            data["source"] = "EXAMPLE / demo (embedded)"
        return data
    # Minimal last-resort demo so build never invents weather numbers silently
    raise SystemExit("no demo data and live fetch failed")


def write_demo_from(payload):
    demo = json.loads(json.dumps(payload))
    demo["source"] = "EXAMPLE / demo (embedded)"
    demo["live"] = False
    demo["note"] = (
        "Demo fallback for Weekend Gameplan. Weather and tide figures are a snapshot "
        "labeled EXAMPLE — not live. Used only when network fetch fails."
    )
    if "weather" in demo:
        demo["weather"]["live"] = False
        demo["weather"]["source"] = "EXAMPLE / demo (embedded)"
    if "tides" in demo:
        demo["tides"]["live"] = False
        demo["tides"]["source"] = "EXAMPLE / demo (embedded)"
    path = os.path.join(HERE, "data", "gameplan-demo.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(demo, f, indent=2)
    return path


def load_or_fetch():
    live_path = os.path.join(HERE, "data", "gameplan.json")
    demo_path = os.path.join(HERE, "data", "gameplan-demo.json")
    try:
        data = build_payload()
        if not data.get("live"):
            raise RuntimeError("payload not live")
        with open(live_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        if not os.path.isfile(demo_path):
            write_demo_from(data)
        print(
            f"Live · weekend {data['weekend']['label']} · "
            f"plans={len(data['plans'])}"
        )
        return data
    except Exception as ex:
        print(f"Fetch/plan failed ({ex}); using demo fallback")
        if os.path.isfile(demo_path):
            with open(demo_path, encoding="utf-8") as f:
                data = json.load(f)
        elif os.path.isfile(live_path):
            with open(live_path, encoding="utf-8") as f:
                data = json.load(f)
        else:
            raise SystemExit("no gameplan data available")
        data["live"] = False
        data["source"] = "EXAMPLE / demo (embedded)"
        if "weather" in data:
            data["weather"]["live"] = False
        if "tides" in data:
            data["tides"]["live"] = False
        return data


def main():
    data = load_or_fetch()
    data_js = json.dumps(data, ensure_ascii=False)
    html = rd("web/index.html")
    html = html.replace("/*__CSS__*/", rd("web/app.css"))
    html = html.replace("/*__DATA__*/ null /*__/DATA__*/", data_js)
    app = rd("web/app.js").replace("</script", "<\\/script")
    html = html.replace("/*__APP__*/", app)
    os.makedirs(os.path.join(HERE, "dist"), exist_ok=True)
    out = os.path.join(HERE, "dist", "weekend-gameplan.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    mode = "live" if data.get("live") else "demo"
    print(f"built {out} ({os.path.getsize(out):,} bytes) · {mode}")


if __name__ == "__main__":
    main()
