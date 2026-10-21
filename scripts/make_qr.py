"""Generate qr/<stock>.png for every unsold, priced car; remove stale ones."""
import json, os, urllib.request, qrcode
SRC = "https://luxrepair2025-rgb.github.io/lux-tesla-battery/data.json"
OUT = os.environ.get("QR_OUT", "qr")
os.makedirs(OUT, exist_ok=True)
cars = json.loads(urllib.request.urlopen(urllib.request.Request(SRC, headers={"User-Agent": "lux-tv"}), timeout=30).read())
keep = set()
for c in cars:
    if c.get("sold") or not c.get("price") or not c.get("url") or not c.get("stock"): continue
    fn = f"{OUT}/{c['stock']}.png"; keep.add(os.path.basename(fn))
    if os.path.exists(fn) and open(fn + ".url").read() == c["url"] if os.path.exists(fn + ".url") else False: continue
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    q.add_data(c["url"]); q.make(fit=True)
    q.make_image(fill_color="black", back_color="white").get_image().convert("RGB").resize((360, 360), 0).save(fn)
    open(fn + ".url", "w").write(c["url"])
for f in os.listdir(OUT):
    base = f[:-4] if f.endswith(".url") else f
    if base not in keep: os.remove(os.path.join(OUT, f))
print("qr", len(keep))
