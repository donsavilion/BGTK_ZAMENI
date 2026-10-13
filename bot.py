import os, re, csv, io, json, hashlib
from urllib.request import urlopen, Request
from urllib.parse import urlencode

BASE = ("https://docs.google.com/spreadsheets/d/e/"
        "2PACX-1vRgODzWJhSfml2SVezD2P4wdEyp92gZ7y3-tyjFssLI80j3CCTv7-"
        "cmJhcCsvQNKcPnzP-m2r9pswd8/")
TOKEN = os.environ["TG_TOKEN"]
OWNER = os.environ["TG_CHAT"]
API = f"https://api.telegram.org/bot{TOKEN}/"
DATE = re.compile(r"\b\d{1,2}\.\d{2}\.(?:\d{4}|\d{2})\b")
GRP = r"\d[А-Я]\d{3}"
LAT = str.maketrans("ABCEHKMOPTX", "АВСЕНКМОРТХ")

def get(u):
    req = Request(u, headers={"User-Agent": "Mozilla/5.0"})
    return urlopen(req, timeout=30).read().decode("utf-8")

def norm(x):
    return re.sub(r"[\s\-]", "", x).upper().translate(LAT)

def one(c):
    return re.sub(r"\s*\n\s*", ", ", c.strip())

def api(method, **p):
    return json.loads(urlopen(API + method, urlencode(p).encode(),
                              timeout=30).read())

def send(chat, text):
    try:
        api("sendMessage", chat_id=chat, text=text[:3500])
    except Exception as e:
        print("send failed", chat, e)

def who(f):
    name = " ".join(x for x in (f.get("first_name"), f.get("last_name")) if x)
    un = f"@{f['username']}" if f.get("username") else "без username"
    return f"{name} ({un}), id {f.get('id')}"

# ---------- читаем таблицу ----------
try:
    page = get(BASE + "pubhtml")
except Exception:
    page = ""
gids = list(dict.fromkeys(
    re.findall(r"gid=(\d+)", page) + re.findall(r"sheet-button-(\d+)", page)
)) or ["0"]

groups, ok = {}, False
for gid in gids:
    try:
        data = get(BASE + f"pub?output=csv&gid={gid}")
    except Exception:
        continue
    ok = True
    rows = list(csv.reader(io.StringIO(data)))
    m0 = DATE.search(" ".join(" ".join(r) for r in rows))
    first_date = m0.group(0) if m0 else ""
    head, k, prev_h, label = None, 0, -1, ""
    for idx, r in enumerate(rows):
        if any(norm(c) == "ГРУППА" for c in r):
            k += 1
            start = max(prev_h + 1, idx - 8)
            ds = DATE.findall(" ".join(" ".join(x) for x in rows[start:idx]))
            if ds:
                label = ds[-1]
            elif k == 1 and first_date:
                label = first_date
            else:
                label = f"лист {gid}, таблица {k}"
            head = [(i, re.search(r"\d", c).group(0)) for i, c in enumerate(r)
                    if re.match(r"\s*\d\s*пара", c, re.I)]
            prev_h = idx
            continue
        if head is None:
            continue
        cell = next((c for c in r if c.strip()), "")
        g = norm(cell)
        if not re.fullmatch(GRP, g):
            continue
        lines = []
        if head:
            for q, (i, n) in enumerate(head):
                j = head[q + 1][0] if q + 1 < len(head) else len(r)
                cells = [one(c) for c in r[i:j] if c.strip()]
                if cells:
                    s = f"{n} пара: {cells[0]}"
                    if len(cells) > 1:
                        s += f" (каб. {', '.join(cells[1:])})"
                    lines.append(s)
        else:
            lines.append(" | ".join(one(c) for c in r if c.strip()))
        if lines:
            groups.setdefault(g, []).append(f"📅 {label}\n" + "\n".join(lines))

# ---------- данные подписчиков ----------
D = json.load(open("data.json")) if os.path.exists("data.json") else {}
D.setdefault("offset", 0)
D.setdefault("users", {})
D.setdefault("hash", {})
if not D.get("seeded"):
    D["users"].setdefault(OWNER, "3П064")
    D["seeded"] = True

# ---------- новые сообщения боту ----------
try:
    ups = api("getUpdates", offset=D["offset"], timeout=0)["result"]
except Exception:
    ups = []
last = {}
for u in ups:
    D["offset"] = u["update_id"] + 1
    m = u.get("message") or {}
    chat = m.get("chat", {})
    if chat.get("type") == "private" and m.get("text"):
        last[str(chat["id"])] = (m["text"].strip(), m.get("from", {}))

reports = []
for chat, (t, f) in last.items():
    g = "" if t.startswith("/") else norm(t)
    if t.lower().startswith("/stop"):
        D["users"].pop(chat, None)
        D["hash"].pop(chat, None)
        send(chat, "Отписал. Чтобы вернуться, отправьте номер группы.")
        reports.append((chat, f"➖ отписался: {who(f)}"))
    elif re.fullmatch(GRP, g):
        was = D["users"].get(chat)
        D["users"][chat] = g
        D["hash"].pop(chat, None)
        msg = f"Готово! Буду присылать замены для {g}."
        if ok and not groups.get(g):
            msg += " Сейчас замен для этой группы нет, напишу, когда появятся."
        send(chat, msg)
        what = "🔄 сменил группу на" if was else "➕ новый подписчик, группа"
        reports.append((chat, f"{what} {g}: {who(f)}"))
    elif chat in D["users"]:
        send(chat, f"Вы подписаны на {D['users'][chat]}. Чтобы сменить группу, "
                   "отправьте новый номер. Отписаться: /stop")
    else:
        send(chat, "Отправьте номер вашей группы, например 3П064. "
                   "Отписаться: /stop")
        reports.append((chat, f"👀 открыл бота: {who(f)}"))

rep = "\n".join(txt for c, txt in reports if c != OWNER)
if rep:
    send(OWNER, rep)

# ---------- рассылка ----------
if ok:
    for chat, g in list(D["users"].items()):
        bl = groups.get(g)
        text = f"Замены {g}\n\n" + "\n\n".join(bl) if bl else ""
        h = hashlib.md5(text.encode()).hexdigest()
        if text and h != D["hash"].get(chat):
            send(chat, text)
        D["hash"][chat] = h

json.dump(D, open("data.json", "w"), ensure_ascii=False, indent=1)
