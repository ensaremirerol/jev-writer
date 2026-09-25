#!/usr/bin/env python3
"""Rate how complex ONE sentence is to read.

Usage: complexity.py "SENTENCE"      ("-" reads the sentence from stdin)
Returns a Jev score (0 plain .. 3 very dense) plus word count and Flesch-Kincaid grade computed locally.
"""
import re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from jev import ask, emit, r2

LEVELS = [
    "Plain: one idea in everyday words.",
    "Moderate: one idea with a few technical terms.",
    "Dense: several ideas or clauses, specialist terms.",
    "Very dense: nested clauses, stacked jargon or undefined terms; hard to parse on first read.",
]


def syllables(word):
    w = word.lower()
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and not w.endswith("le") and n > 1:
        n -= 1
    return max(n, 1)


def metrics(sentence):
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", sentence)
    if not words:
        return {"words": 0, "fk_grade": 0.0}
    # Flesch-Kincaid grade for a single sentence.
    fk = 0.39 * len(words) + 11.8 * sum(map(syllables, words)) / len(words) - 15.59
    return {"words": len(words), "fk_grade": round(fk, 1)}


def main(argv):
    if len(argv) != 1:
        sys.exit(__doc__)
    sentence = " ".join((sys.stdin.read() if argv[0] == "-" else argv[0]).split())
    a = ask(sentence, {"complexity": {"type": "score", "instructions": "How complex is this sentence to read?", "criteria": LEVELS}})["complexity"]
    emit({"sentence": sentence, "score": r2(a["score"]), "of": len(LEVELS) - 1, "level": LEVELS[round(a["score"])].split(":")[0],
          "confidence": r2(a["confidence"]), **metrics(sentence), "very_dense": a["score"] >= 2.5})


if __name__ == "__main__":
    main(sys.argv[1:])
