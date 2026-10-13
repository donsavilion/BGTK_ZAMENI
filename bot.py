import os, re, csv, io, hashlib
from urllib.request import urlopen, Request
from urllib.parse import urlencode

BASE = ("https://docs.google.com/spreadsheets/d/e/"
        "2PACX-1vRgODzWJhSfml2SVezD2P4wdEyp92gZ7y3-tyjFssLI80j3CCTv7-"
        "cmJhcCsvQNKcPnzP-m2r9pswd8/")
GROUP = "3П064"
TOKEN = os.environ["TG_TOKEN"]
CHAT = os.environ["TG_CHAT"]
DATE = re.compile(r"\b\d{1,2}\.\d{2}\.(?:\d{4}|\d{2})\b")

def get(u):
    req = Request(u, headers={"User-Agent": "Mozilla/5.0"})
    return urlopen(req, timeout=30).read().decode("utf-8")

def norm(x):
    return re.sub(r"[\s\-]", "", x).upper()

def one(c):
    return re.sub(r"\s*\n\s*", ", ", c.strip())

try:
    page = get(BASE + "pubhtml")
except Exception:
    page = ""
gids = list(dict.fromkeys(
    re.findall(r"gid=(\d+)", page) + re.findall(r"sheet-button-(\d+)", page)
)) or ["0"]

blocks = []
for gid in gids:
    try:
        data = get(BASE + f"pub?output=csv&gid={gid}")
    except Exception:
        continue
    rows = list(csv.reader(io.StringIO(data)))
    m0 = DATE.search(" ".join(" ".join(r) for r in rows))
    first_date = m0.group(0) if m0 else ""
    tables, head, k, prev_h = [], None, 0, -1
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
            tables.append([label, []])
            prev_h = idx
            continue
        if tables and any(norm(c) == norm(GROUP) for c in r):
            if head:
                for q, (i, n) in enumerate(head):
                    j = head[q + 1][0] if q + 1 < len(head) else len(r)
                    cells = [one(c) for c in r[i:j] if c.strip()]
                    if cells:
                        s = f"{n} пара: {cells[0]}"
                        if len(cells) > 1:
                            s += f" (каб. {', '.join(cells[1:])})"
                        tables[-1][1].append(s)
            else:
                tables[-1][1].append(" | ".join(one(c) for c in r if c.strip()))
    for label, lines in tables:
        if lines:
            blocks.append(f"📅 {label}\n" + "\n".join(lines))

text = ""
if blocks:
    text = f"Замены {GROUP}\n\n" + "\n\n".join(blocks)

old = open("state.txt").read() if os.path.exists("state.txt") else ""
h = hashlib.md5(text.encode()).hexdigest()
if text and h != old:
    data = urlencode({"chat_id": CHAT, "text": text[:3500]}).encode()
    urlopen(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data)
open("state.txt", "w").write(h)
