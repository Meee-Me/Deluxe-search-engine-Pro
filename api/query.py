import json, sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from search import Index, snippet

ix = Index()  # built once per cold start
ix.add_dir(ROOT)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        q = parse_qs(urlparse(self.path).query).get("q", [""])[0][:200]
        out = [{"path": str(Path(d).relative_to(ROOT)), "score": round(s, 4),
                "snippet": snippet(ix.text[d], q)} for d, s in ix.search(q)]
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"docs": len(ix.lengths), "results": out}).encode())
