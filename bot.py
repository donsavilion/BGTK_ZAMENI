import os, re, hashlib
from html.parser import HTMLParser
from urllib.request import urlopen, Request
from urllib.parse import urlencode

URL = ("https://docs.google.com/spreadsheets/d/e/"
       "2PACX-1vRgODzWJhSfml2SVezD2P4wdEyp92gZ7y3-tyjFssLI80j3CCTv7-"
       "cmJhcCsvQNKcPnzP-m2r9pswd8/pubhtml?widget=true&headers=false")
GROUP = "3П064"
TOKEN = os.environ["TG_TOKEN"]
CHAT = os.environ["TG_CHAT"]

class P(HTMLParser):
    def __init__(s):
        super().__init__(); s.rows = []; s.cur = None; s.cell = None
    def handle_starttag(s, t, a):
        if t == "tr": s.cur = []
        elif t == "td" and s.cur is not None: s.cell = ""
        elif t == "br" and s.cell is not None: s.cell += " "
    def handle_endtag(s, t):
        if t == "td" and s.cell is not None:
            s.cur.append(s.cell.strip()); s.cell = None
        elif t == "tr" and s.cur is not None:
            if any(s.cur): s.rows.append(s.cur)
            s.cur = None
    def handle_data(s, d):
        if s.cell is not None: s.cell += d

def norm(x):
    return re.sub(r"[\s\-]", "", x).upper()

html = urlopen(Request(URL, headers={"User-Agent": "Mozilla/5.0"})).read().decode("utf-8")
p = P(); p.feed(html)
lines = [" | ".join(c for c in r if c) for r in p.rows
         if any(norm(GROUP) in norm(c) for c in r)]
text = "\n".join(lines)
if not text:
    sample = "\n".join(" | ".join(c for c in r if c) for r in p.rows[:25])
    text = f"(не нашёл {GROUP}; строк: {len(p.rows)})\n{sample}"[:3500]


old = open("state.txt").read() if os.path.exists("state.txt") else ""
h = hashlib.md5(text.encode()).hexdigest()
if h != old:
    if text:
        data = urlencode({"chat_id": CHAT,
                          "text": f"Замены {GROUP}:\n{text}"}).encode()
        urlopen(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data)
open("state.txt", "w").write(h)
