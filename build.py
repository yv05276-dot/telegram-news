# בונה את אתר החדשות מערוצי טלגרם ציבוריים. רץ אוטומטית דרך GitHub Actions.
import json, re, html, urllib.request, datetime, os

CHANNELS = [
    "danielamram3", "abualiexpress", "amitsegal", "TheBigBadShadow",
    "PikudHaOref_all", "ynetalerts", "N12chat", "michaelshemesh",
    "idfofficial", "parlamnt",
]
PER_CHANNEL = 20
MAX_TEXT = 500

def fetch(u):
    req = urllib.request.Request("https://t.me/s/" + u, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

def clean(s):
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s).strip()

def parse(u, page):
    m = re.search(r'tgme_channel_info_header_title[^>]*>\s*<span[^>]*>(.*?)</span>', page, re.S)
    title = clean(m.group(1)) if m else u
    m = re.search(r'counter_value">([^<]+)</span>\s*<span class="counter_type">subscribers', page)
    subs = m.group(1) if m else ""
    posts = []
    for chunk in page.split('data-post="')[1:]:
        pid = chunk.split('"', 1)[0]
        t = re.search(r'<time datetime="([^"]+)"', chunk)
        if not t or "/" not in pid:
            continue
        x = re.search(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', chunk, re.S)
        text = clean(x.group(1)) if x else ""
        media = bool(re.search(r"tgme_widget_message_(photo|video|roundvideo)", chunk))
        if not text and not media:
            continue
        if len(text) > MAX_TEXT:
            text = text[:MAX_TEXT].rsplit(" ", 1)[0] + "…"
        posts.append({"c": u, "id": pid, "t": t.group(1), "x": text, "m": media})
    return {"u": u, "n": title, "s": subs}, posts[-PER_CHANNEL:]

channels, feed = [], []
for u in CHANNELS:
    try:
        info, posts = parse(u, fetch(u))
        channels.append(info)
        feed += posts
    except Exception as e:
        print("שגיאה בערוץ", u, e)

feed.sort(key=lambda p: p["t"], reverse=True)
data = {"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(), "channels": channels, "feed": feed}
tpl = open("template.html", encoding="utf-8").read()
os.makedirs("public", exist_ok=True)
out = tpl.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
open("public/index.html", "w", encoding="utf-8").write(out)
print("נבנה:", len(channels), "ערוצים,", len(feed), "הודעות")
