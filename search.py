"""Tiny TF-IDF search engine. Usage: python search.py <dir> <query...> | python search.py --test"""
import math, re, sys
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

    def add_dir(self, root, exts=(".txt", ".md", ".py", ".html")):
        for p in Path(root).rglob("*"):
            if p.is_file() and p.suffix in exts:
                self.add(str(p), p.read_text(errors="ignore"))

    def search(self, query, k=10):
        n, scores = len(self.lengths), defaultdict(float)
        for t in set(tokens(query)):
            docs = self.postings.get(t, {})
            idf = math.log(1 + n / (1 + len(docs)))
            for d, c in docs.items():
                scores[d] += (c / self.lengths[d]) * idf
        return sorted(scores.items(), key=lambda x: -x[1])[:k]

def _test():
    ix = Index()
    ix.add("a", "the quick brown fox")
    ix.add("b", "the lazy dog sleeps")
    ix.add("c", "fox fox fox and a dog")
    assert [d for d, _ in ix.search("fox")] == ["c", "a"]
    assert ix.search("zebra") == []
    print("ok")

if __name__ == "__main__":
    if sys.argv[1:] == ["--test"]:
        _test()
    elif len(sys.argv) < 3:
        sys.exit(__doc__)
    else:
        ix = Index()
        ix.add_dir(sys.argv[1])
        for doc, s in ix.search(" ".join(sys.argv[2:])):
            print(f"{s:.4f}  {doc}")
