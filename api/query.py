"""Web search. Brave Search if BRAVE_API_KEY is set (full web), else Wikipedia (keyless)."""
import html, json, os, re
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, quote, urlencode, urlparse
from urllib.request import Request, urlopen

def clean(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or ""))

def fetch(url, headers=None):
    req = Request(url, headers={"User-Agent": "DeluxeSearch/1.0", **(headers or {})})
    with urlopen(req, timeout=8) as r:
        return json.load(r)

def parse_brave(d):
    return [{"title": clean(r["title"]), "url": r["url"], "snippet": clean(r.get("description"))}
            for r in d.get("web", {}).get("results", [])]

def parse_wiki(d):
    return [{"title": r["title"], "url": "https://en.wikipedia.org/wiki/" + quote(r["title"].replace(" ", "_")),
             "snippet": clean(r["snippet"])} for r in d.get("query", {}).get("search", [])]

def search(q):
    key = os.environ.get("BRAVE_API_KEY")
    if key:
        return "Brave", parse_brave(fetch("https://api.search.brave.com/res/v1/web/search?" + urlencode({"q": q, "count": 10}),
                                          {"X-Subscription-Token": key, "Accept": "application/json"}))
    return "Wikipedia", parse_wiki(fetch("https://en.wikipedia.org/w/api.php?" + urlencode(
        {"action": "query", "list": "search", "srsearch": q, "srlimit": 10, "format": "json"})))

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        q = parse_qs(urlparse(self.path).query).get("q", [""])[0].strip()[:200]
        try:
            src, results = search(q) if q else ("", [])
            body, code = {"source": src, "results": results}, 200
        except Exception as e:  # upstream down / bad key: tell the UI, don't 500 blank
            body, code = {"error": type(e).__name__}, 502
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

if __name__ == "__main__":
    w = parse_wiki({"query": {"search": [{"title": "Cat food", "snippet": 'a <span class="searchmatch">cat</span> &amp; dog'}]}})
    assert w == [{"title": "Cat food", "url": "https://en.wikipedia.org/wiki/Cat_food", "snippet": "a cat & dog"}]
    b = parse_brave({"web": {"results": [{"title": "<b>Cat</b>", "url": "https://x.y", "description": "d <strong>c</strong>"}]}})
    assert b == [{"title": "Cat", "url": "https://x.y", "snippet": "d c"}]
    assert parse_brave({}) == []
    print("ok")
