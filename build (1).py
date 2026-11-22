# בונה את אתר החדשות מערוצי טלגרם ציבוריים. רץ אוטומטית דרך GitHub Actions.
# רשימת הערוצים נמצאת בקובץ channels.txt (ערוץ אחד בכל שורה).
import json, re, html, urllib.request, datetime, os

CHANNELS = []
for line in open("channels.txt", encoding="utf-8"):
    u = line.strip().lstrip("@")
    if u and not u.startswith("#") and u not in CHANNELS:
        CHANNELS.append(u)
PER_CHANNEL = 20
MAX_TEXT = 1200
REPO = os.environ.get("GITHUB_REPOSITORY", "")

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

# ---- זיהוי ידיעות גדולות: אותה ידיעה בכמה ערוצים ----
STOP = set("""של את על עם זה זו זאת גם לא כי אם או הוא היא הם הן אני אנחנו יש אין כל כך רק עוד כבר היום
אחרי לפני בין תוך מול אל לו לה להם שלא מה מי איך למה כמו יותר פי בו בה הזה הזאת היה היו יהיה בעקבות לפי
נגד אצל עד אמר אמרה נמסר דיווח מדווח עכשיו כעת חדשות מבזק ערוץ טלגרם הצטרפו קישור למבזק המלא שלנו""".split())
PRE = "והבלמשכ"

def tokens(t):
    out = set()
    for w in re.findall(r"[֐-׿A-Za-z0-9]+", t):
        w = re.sub(r"[֑-ׇ]", "", w).lower()
        for _ in range(2):
            if len(w) >= 5 and w[0] in PRE:
                w = w[1:]
        if len(w) >= 3 and w not in STOP and not w.isdigit():
            out.add(w)
    return out

def ts(p):
    return datetime.datetime.fromisoformat(p["t"].replace("Z", "+00:00"))

def stories(feed):
    now = datetime.datetime.now(datetime.timezone.utc)
    recent = [p for p in feed if p["x"] and now - ts(p) < datetime.timedelta(hours=12)]
    tk = [tokens(p["x"][:400]) for p in recent]
    df = {}
    for s in tk:
        for w in s:
            df[w] = df.get(w, 0) + 1
    limit = max(4, len(recent) * 0.12)
    tk = [{w for w in s if df[w] <= limit} for s in tk]
    parent = list(range(len(recent)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i in range(len(recent)):
        for j in range(i + 1, len(recent)):
            a, b = recent[i], recent[j]
            if a["c"] == b["c"] or abs(ts(a) - ts(b)) > datetime.timedelta(hours=6):
                continue
            common = len(tk[i] & tk[j])
            small = min(len(tk[i]), len(tk[j])) or 1
            if common >= 3 and common / small >= 0.25:
                parent[find(i)] = find(j)
    groups = {}
    for i in range(len(recent)):
        groups.setdefault(find(i), []).append(recent[i])
    out = []
    for g in groups.values():
        chans = {p["c"] for p in g}
        if len(chans) >= 2:
            g.sort(key=lambda p: p["t"], reverse=True)
            out.append({"ids": [p["id"] for p in g], "n": len(chans), "t": g[0]["t"]})
    out.sort(key=lambda s: (s["n"], s["t"]), reverse=True)
    return out[:30]

channels, feed = [], []
for u in CHANNELS:
    try:
        info, posts = parse(u, fetch(u))
        channels.append(info)
        feed += posts
    except Exception as e:
        print("שגיאה בערוץ", u, e)
        channels.append({"u": u, "n": u, "s": "", "err": True})

feed.sort(key=lambda p: p["t"], reverse=True)
data = {"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(), "repo": REPO,
        "channels": channels, "feed": feed, "stories": stories(feed)}
os.makedirs("public", exist_ok=True)
js = json.dumps(data, ensure_ascii=False)
open("public/data.json", "w", encoding="utf-8").write(js)
tpl = open("template.html", encoding="utf-8").read()
open("public/index.html", "w", encoding="utf-8").write(tpl.replace("__DATA__", js.replace("</", "<\\/")))
print("נבנה:", len(channels), "ערוצים,", len(feed), "הודעות,", len(data["stories"]), "ידיעות גדולות")
