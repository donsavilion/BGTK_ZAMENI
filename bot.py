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

def one(c):
    return re.sub(r"\s*\n\s*", ", ", c.strip())

try:
    page = get(BASE + "pubhtml")
except Exception:
    page = ""
gids = list(dict.fromkeys(
    re.findall(r"gid=(\d+)", page) + re.findall(r"sheet-button-(\d+)", page)
)) or ["0"]

blocks, date = [], ""
for gid in gids:
    try:
        data = get(BASE + f"pub?output=csv&gid={gid}")
    except Exception:
        continue
    head = None
    for r in csv.reader(io.StringIO(data)):
        if not date:
            m = re.search(r"\b\d{1,2}\.\d{2}\.(?:\d{4}|\d{2})\b", " ".join(r))
            if m:
                date = m.group(0)
        if any(norm(c) == "ГРУППА" for c in r):
            head = [(i, re.search(r"\d", c).group(0)) for i, c in enumerate(r)
                    if re.match(r"\s*\d\s*пара", c, re.I)]
            continue
        if any(norm(c) == norm(GROUP) for c in r):
            out = []
            if head:
                for k, (i, n) in enumerate(head):
                    j = head[k + 1][0] if k + 1 < len(head) else len(r)
                    cells = [one(c) for c in r[i:j] if c.strip()]
                    if cells:
                        s = f"{n} пара: {cells[0]}"
                        if len(cells) > 1:
                            s += f" (каб. {', '.join(cells[1:])})"
                        out.append(s)
            else:
                out.append(" | ".join(one(c) for c in r if c.strip()))
            blocks.append("\n".join(out))

text = "\n\n".join(b for b in blocks if b)
if text:
    text = f"Замены {GROUP}" + (f" на {date}" if date else "") + "\n" + text

old = open("state.txt").read() if os.path.exists("state.txt") else ""
h = hashlib.md5(text.encode()).hexdigest()
if text and h != old:
    data = urlencode({"chat_id": CHAT, "text": text[:3500]}).encode()
    urlopen(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data)
open("state.txt", "w").write(h)
