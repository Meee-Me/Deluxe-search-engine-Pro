"""Tiny TF-IDF search engine.
Usage: python search.py <dir> <query...> | python search.py --serve <dir> [port] | python search.py --test"""
import html, json, math, re, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse
from collections import Counter, defaultdict
from pathlib import Path

def tokens(text):
    return re.findall(r"\w+", text.lower())

class Index:
    def __init__(self):
        self.postings = defaultdict(dict)  # term -> {doc: count}
        self.lengths = {}

    def add(self, doc, text):
        toks = tokens(text)
        self.lengths[doc] = len(toks) or 1
        for t, c in Counter(toks).items():
            self.postings[t][doc] = c

    def add_dir(self, root):
        for p in Path(root).rglob("*"):
            if not p.is_file() or ".git" in p.parts:
                continue
            try:
                data = p.read_bytes()
            except OSError:
                continue
            if b"\0" not in data[:1024]:  # skip binaries
                self.add(str(p), data.decode(errors="ignore"))

    def search(self, query, k=10):
        n, scores = len(self.lengths), defaultdict(float)
        for t in set(tokens(query)):
            docs = self.postings.get(t, {})
            idf = math.log(1 + n / (1 + len(docs)))
            for d, c in docs.items():
                scores[d] += (c / self.lengths[d]) * idf
        return sorted(scores.items(), key=lambda x: -x[1])[:k]

def serve(ix, port):
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            u = urlparse(self.path)
            q = parse_qs(u.query).get("q", [""])[0]
            res = ix.search(q)
            if u.path == "/api":
                body, ctype = json.dumps(res), "application/json"
            else:
                rows = "".join(f"<li>{html.escape(d)} <small>{s:.4f}</small></li>" for d, s in res)
                body = (f'<form><input name=q value="{html.escape(q, quote=True)}" autofocus>'
                        f'<button>Search</button></form><ol>{rows}</ol>')
                ctype = "text/html"
            self.send_response(200)
            self.send_header("Content-Type", ctype + "; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode())
    # shortcut: localhost only, no auth; put a proxy in front before exposing it
    print(f"http://127.0.0.1:{port}")
    HTTPServer(("127.0.0.1", port), H).serve_forever()

def _test():
    ix = Index()
    ix.add("a", "the quick brown fox")
    ix.add("b", "the lazy dog sleeps")
    ix.add("c", "fox fox fox and a dog")
    import tempfile, os
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "x.rs"), "w").write("needle")
        open(os.path.join(d, "b.bin"), "wb").write(b"needle\0")
        t = Index(); t.add_dir(d)
        assert [os.path.basename(p) for p, _ in t.search("needle")] == ["x.rs"]
    assert [d for d, _ in ix.search("fox")] == ["c", "a"]
    assert ix.search("zebra") == []
    print("ok")

if __name__ == "__main__":
    if sys.argv[1:] == ["--test"]:
        _test()
    elif sys.argv[1:2] == ["--serve"] and len(sys.argv) >= 3:
        ix = Index()
        ix.add_dir(sys.argv[2])
        serve(ix, int(sys.argv[3]) if len(sys.argv) > 3 else 8000)
    elif len(sys.argv) < 3:
        sys.exit(__doc__)
    else:
        ix = Index()
        ix.add_dir(sys.argv[1])
        for doc, s in ix.search(" ".join(sys.argv[2:])):
            print(f"{s:.4f}  {doc}")
