"""Render weather.png and traffic.png (1920x1080) for the Lux waiting-room Roku channel."""
import io, json, math, os, datetime, urllib.request, urllib.parse
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont, ImageFilter

LAT, LON = 28.054733, -81.965713   # 705 W Memorial Blvd, Lakeland, FL 33815
UA = "lux-waiting-room-tv (luxautomotive22@gmail.com)"
OUT = os.environ.get("OUT", "maps")
TZ = ZoneInfo("America/New_York")
GOLD, PANEL, BG = (212, 175, 55), (21, 21, 28), (11, 11, 15)
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
def F(s, b=False): return ImageFont.truetype(FB if b else FR, s)

def get(url, ua="Mozilla/5.0 " + UA, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.read()
def getj(url): return json.loads(get(url))

def deg2px(lat, lon, z):
    n = 256 * 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return x, y

def tilemap(w, h, z, url_fn, lat=LAT, lon=LON, mode="RGBA"):
    cx, cy = deg2px(lat, lon, z)
    x0, y0 = cx - w / 2, cy - h / 2
    img = Image.new(mode, (w, h), (0, 0, 0, 0))
    for tx in range(int(x0 // 256), int((x0 + w) // 256) + 1):
        for ty in range(int(y0 // 256), int((y0 + h) // 256) + 1):
            try:
                t = Image.open(io.BytesIO(get(url_fn(z, tx, ty)))).convert("RGBA")
                img.paste(t, (int(tx * 256 - x0), int(ty * 256 - y0)), t)
            except Exception as e: print("tile fail", tx, ty, e)
    return img, (x0, y0)

def osm(z, x, y): return f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
def darken(im):
    from PIL import ImageOps, ImageEnhance
    a = im.getchannel("A"); g = ImageOps.invert(im.convert("L"))
    g = ImageEnhance.Brightness(ImageEnhance.Contrast(g).enhance(0.8)).enhance(0.55)
    out = Image.merge("RGBA", (g, g, g.point(lambda v: min(255, v + 12)), a)); return out

def header(d, title, sub):
    d.rectangle([0, 0, 1920, 90], fill=(0, 0, 0))
    d.text((60, 24), "LUX AUTOMOTIVE", font=F(36, True), fill=GOLD)
    d.text((1860, 30), sub, font=F(28), fill=(220, 220, 220), anchor="ra")
    d.text((960, 24), title, font=F(36, True), fill="white", anchor="ma")

def pin(d, x, y, label=None):
    d.ellipse([x - 16, y - 16, x + 16, y + 16], fill=GOLD, outline="white", width=4)
    if label:
        tw = d.textlength(label, font=F(26, True))
        d.rounded_rectangle([x + 24, y - 22, x + 44 + tw, y + 22], 8, fill=(0, 0, 0, 200))
        d.text((x + 34, y - 15), label, font=F(26, True), fill="white")

def wrap(d, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= width: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def now_str(): return datetime.datetime.now(TZ).strftime("Updated %-I:%M %p ET")

# ---------------- WEATHER ----------------
def weather():
    W, H, MAPW = 1920, 1080, 1180
    z = 7
    base, (x0, y0) = tilemap(MAPW, H - 90, z, osm); base = darken(base)
    rv = getj("https://api.rainviewer.com/public/weather-maps.json")
    fr = rv["radar"]["past"][-1]
    radar, _ = tilemap(MAPW, H - 90, z, lambda z, x, y: f"{rv['host']}{fr['path']}/256/{z}/{x}/{y}/2/1_1.png")
    m = Image.alpha_composite(base, radar)
    img = Image.new("RGBA", (W, H), BG + (255,))
    img.paste(m, (0, 90))
    d = ImageDraw.Draw(img)
    rt = datetime.datetime.fromtimestamp(fr["time"], TZ).strftime("%-I:%M %p")
    pin(d, MAPW // 2, 90 + (H - 90) // 2, "Lux Automotive")
    d.rounded_rectangle([30, 1000, 560, 1060], 10, fill=(0, 0, 0, 190))
    d.text((50, 1013), f"Live radar  {rt} ET  -  RainViewer  Map: OSM", font=F(26), fill="white")
    # NWS
    pts = getj(f"https://api.weather.gov/points/{LAT},{LON}")["properties"]
    hourly = getj(pts["forecastHourly"])["properties"]["periods"][0]
    fc = getj(pts["forecast"])["properties"]["periods"]
    d.rectangle([MAPW, 90, W, H], fill=PANEL); d.rectangle([MAPW, 90, MAPW + 8, H], fill=GOLD)
    x = MAPW + 60
    d.text((x, 130), "LAKELAND WEATHER", font=F(38, True), fill=GOLD)
    d.text((x, 185), f"{hourly['temperature']}°{hourly['temperatureUnit']}", font=F(150, True), fill="white")
    y = 370
    for line in wrap(d, hourly["shortForecast"], F(42), 600)[:2]:
        d.text((x, y), line, font=F(42), fill=(220, 220, 228)); y += 54
    rain = (hourly.get("probabilityOfPrecipitation") or {}).get("value")
    wind = f"Wind {hourly.get('windDirection','')} {hourly.get('windSpeed','')}"
    d.text((x, y + 10), wind + (f"   Rain {rain}%" if rain is not None else ""), font=F(32), fill=(160, 160, 172))
    y = 560
    d.line([x, y, W - 60, y], fill=(58, 58, 70), width=2); y += 25
    for p in fc[:4]:
        d.text((x, y), p["name"], font=F(32, True), fill=GOLD)
        d.text((W - 60, y), f"{p['temperature']}°", font=F(40, True), fill="white", anchor="ra")
        d.text((x, y + 42), wrap(d, p["shortForecast"], F(28), 560)[0], font=F(28), fill=(190, 190, 200))
        y += 110
    header(d, "WEATHER", now_str())
    img.convert("RGB").save(f"{OUT}/weather.png", optimize=True)

# ---------------- TRAFFIC ----------------
FL = "https://fl511.com"
def fl_list(kind, length=100):
    q = {"columns": [{"name": "county", "search": {"value": "Polk"}}], "start": 0, "length": length}
    return getj(f"{FL}/List/GetData/{kind}?query={urllib.parse.quote(json.dumps(q))}&lang=en")["data"]

def traffic():
    W, H, MAPW = 1920, 1080, 1180
    z = 12
    base, (x0, y0) = tilemap(MAPW, H - 90, z, osm)
    img = Image.new("RGBA", (W, H), BG + (255,))
    img.paste(base, (0, 90))
    d = ImageDraw.Draw(img, "RGBA")
    cams = []
    for c in fl_list("Cameras"):
        try:
            wkt = c["latLng"]["geography"]["wellKnownText"]
            lo, la = map(float, wkt[wkt.index("(") + 1:-1].split())
        except Exception: continue
        dist = math.hypot((la - LAT) * 69, (lo - LON) * 61)
        cams.append((dist, la, lo, c))
    cams.sort(key=lambda t: t[0])
    shown = []
    for dist, la, lo, c in cams:
        px, py = deg2px(la, lo, z); px -= x0; py -= y0 - 90
        if 0 < px < MAPW and 90 < py < H:
            d.ellipse([px - 9, py - 9, px + 9, py + 9], fill=(30, 120, 255), outline="white", width=3)
    pin(d, MAPW // 2, 90 + (H - 90) // 2, "Lux Automotive")
    # incidents
    try: inc = fl_list("traffic", 50)
    except Exception as e: print("incidents fail", e); inc = []
    d.rectangle([MAPW, 90, W, H], fill=PANEL); d.rectangle([MAPW, 90, MAPW + 8, H], fill=GOLD)
    x = MAPW + 50
    d.text((x, 115), "LIVE ROAD CAMERAS", font=F(34, True), fill=GOLD)
    # 2x2 camera grid
    cw, ch = 300, 169; gx, gy = x, 170; n = 0
    for dist, la, lo, c in cams:
        if n >= 4: break
        try:
            im = Image.open(io.BytesIO(get(FL + c["images"][0]["imageUrl"]))).convert("RGB")
            if im.width < 100: continue
            if sum(im.convert("L").resize((16, 9)).getdata()) / 144 > 200: continue  # "no feed" placeholder
        except Exception: continue
        im = im.resize((cw, ch))
        px, py = gx + (n % 2) * (cw + 20), gy + (n // 2) * (ch + 58)
        img.paste(im, (px, py))
        d.text((px, py + ch + 6), (c.get("location") if c.get("location") and "not provided" not in c.get("location") else c["images"][0].get("description", ""))[:26], font=F(20), fill=(200, 200, 210))
        n += 1
    y = 640
    d.text((x, y), "POLK COUNTY ALERTS", font=F(34, True), fill=GOLD); y += 55
    if not inc:
        d.text((x, y), "No reported incidents.", font=F(30), fill="white")
    pri = {"Incidents": 0, "Crashes": 0, "Congestion": 1}
    inc.sort(key=lambda i: pri.get(i.get("type"), 2))
    for i in inc:
        if y > 990: break
        t = f"{i.get('roadwayName','')} {i.get('direction','')}".strip()
        d.text((x, y), f"{t}  -  {i.get('type','')}", font=F(26, True), fill="white"); y += 34
        desc = i.get("description", "").split(". Last updated")[0]
        for line in wrap(d, desc, F(22), 640)[:2]:
            d.text((x, y), line, font=F(22), fill=(180, 180, 190)); y += 28
        y += 12
    d.rounded_rectangle([30, 1000, 720, 1060], 10, fill=(0, 0, 0, 190))
    d.text((50, 1013), "Cameras & alerts: FL511 / FDOT   Map: OpenStreetMap", font=F(24), fill="white")
    header(d, "LOCAL TRAFFIC", now_str())
    img.convert("RGB").save(f"{OUT}/traffic.png", optimize=True)

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for fn in (weather, traffic):
        try: fn(); print("ok", fn.__name__)
        except Exception as e: print("FAILED", fn.__name__, e)  # keep previous image
