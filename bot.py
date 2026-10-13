import os, re, csv, io, hashlib
from urllib.request import urlopen, Request
from urllib.parse import urlencode

BASE = ("https://docs.google.com/spreadsheets/d/e/"
        "2PACX-1vRgODzWJhSfml2SVezD2P4wdEyp92gZ7y3-tyjFssLI80j3CCTv7-"
        "cmJhcCsvQNKcPnzP-m2r9pswd8/")
GROUP = "3П064"
TOKEN = os.environ["TG_TOKEN"]
CHAT = os.environ["TG_CHAT"]

def get(u):
    req = Request(u, headers={"User-Agent": "Mozilla/5.0"})
    return urlopen(req, timeout=30).read().decode("utf-8")

def norm(x):
    return re.sub(r"[\s\-]", "", x).upper()

try:
    page = get(BASE + "pubhtml")
except Exception:
    page = ""
gids = list(dict.fromkeys(
    re.findall(r"gid=(\d+)", page) + re.findall(r"sheet-button-(\d+)", page)
)) or ["0"]

lines, total, sample = [], 0, ""
for gid in gids:
    try:
        data = get(BASE + f"pub?output=csv&gid={gid}")
    except Exception:
        continue
    rows = list(csv.reader(io.StringIO(data)))
    rows = [r for r in rows if any(c.strip() for c in r)]
    total += len(rows)
    if rows and not sample:
        sample = "\n".join(" | ".join(c for c in r if c.strip())
                           for r in rows[:25])
    for r in rows:
        if any(norm(GROUP) in norm(c) for c in r):
            lines.append(" | ".join(c.strip() for c in r if c.strip()))

text = "\n".join(lines)
if not text:
    text = f"(не нашёл {GROUP}; вкладок: {len(gids)}, строк: {total})\n{sample}"
text = text[:3500]

old = open("state.txt").read() if os.path.exists("state.txt") else ""
h = hashlib.md5(text.encode()).hexdigest()
if h != old:
    data = urlencode({"chat_id": CHAT,
                      "text": f"Замены {GROUP}:\n{text}"}).encode()
    urlopen(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data)
open("state.txt", "w").write(h)
