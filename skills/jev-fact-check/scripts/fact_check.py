#!/usr/bin/env python3
"""Check whether each sentence (and the paragraph as a whole) is backed by given facts.

Usage: fact_check.py INPUT.json      (INPUT may be "-" for stdin)
INPUT: {"facts": [...], "paragraphs": ["text", {"text": "...", "facts": [...]}]}

Two layers per sentence:
- Jev: support choice (supported / partial / unsupported / contradicted / no_claim).
- Code: every number in the sentence is looked up in the facts. Jev reads numbers as text and
  misses wrong values, so numbers are never left to Jev alone.
"""
import json, re, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from jev import ask, emit, r2, read_text, split_sentences

SUPPORT = {
    "supported": "Every factual claim in the text is backed by an entry in `facts`.",
    "partial": "Some claims are backed by `facts`; at least one other claim is not in `facts`.",
    "unsupported": "Makes a factual claim (number, result, causal statement, comparison) that no entry in `facts` backs, including claims about topics `facts` does not mention.",
    "contradicted": "Gives a different value or outcome for the same thing an entry in `facts` describes, e.g. a different number for the same quantity.",
    "no_claim": "Makes no factual claim: a transition, roadmap, definition of notation, or framing sentence.",
}

CITE = re.compile(r"\[\d+(?:\s*[,–-]\s*\d+)*\]")  # [3], [5, 7], [2–4]
# Thousands may be grouped by comma, space or thin space: 12 546, 12,546. Skips Q1, v2.
NUM = re.compile(r"(?<![A-Za-z\d.])[−-]?(?:\d{1,3}(?:[,   ]\d{3})+(?!\d)|\d+)(?:\.\d+)?")
RANGE = re.compile(r"(?<![A-Za-z\d./])(\d+(?:\.\d+)?)\s*(?:to|–|-)\s*(\d+(?:\.\d+)?)(?![\d./])")  # not "44/200 to 174/200"


def numbers(text):
    return {abs(float(re.sub(r"[, \u2009\u202f]", "", n).replace("−", "-"))) for n in NUM.findall(CITE.sub("", text))}


def number_check(sentence, facts):
    fact_nums = [numbers(f) for f in facts]
    out = {"not_in_facts": sorted(n for n in numbers(sentence) if not any(n in fs for fs in fact_nums))}
    # A range whose endpoints come from one fact: list that fact's other values outside it,
    # e.g. "55 to 59" from a fact that also contains 46.
    for lo, hi in RANGE.findall(CITE.sub("", sentence)):
        lo, hi = float(lo), float(hi)
        if lo >= hi:  # codes like LOINC 8302-2, not ranges
            continue
        for i, fs in enumerate(fact_nums):
            if lo in fs and hi in fs:
                outside = sorted(v for v in fs if not lo <= v <= hi)
                if outside:
                    out.setdefault("ranges", []).append({"range": [lo, hi], "fact": i, "fact_values_outside": outside})
    return out


def check_paragraph(par, default_facts):
    text, facts = (par, default_facts) if isinstance(par, str) else (par["text"], par.get("facts") or default_facts)
    if not facts:
        sys.exit("error: every paragraph needs facts (own or top-level)")
    sents = split_sentences(text)
    q = {"paragraph": {"type": "choice", "instructions": "Are the claims in `paragraph` (all sentences together) backed by `facts`?", "criteria": SUPPORT}}
    for i, s in enumerate(sents):
        q[f"s{i}"] = {"type": "choice", "instructions": {"question": "Are the claims in the sentence backed by `facts`?", "sentence": s}, "criteria": SUPPORT}
    a = ask({"facts": facts, "paragraph": sents}, q)

    rows = []
    for i, s in enumerate(sents):
        ans, nums = a[f"s{i}"], number_check(s, facts)
        flags = []
        if ans["choice"] in ("partial", "unsupported", "contradicted"):
            flags.append(ans["choice"])
        if ans["confidence"] < 0.5:
            flags.append("uncertain")
        if nums["not_in_facts"]:
            flags.append("numbers_not_in_facts")
        if nums.get("ranges"):
            flags.append("range_check")
        rows.append({"i": i, "text": s, "support": ans["choice"], "confidence": r2(ans["confidence"]), "numbers": nums, "flags": flags})
    return {"support": a["paragraph"]["choice"], "confidence": r2(a["paragraph"]["confidence"]), "usage": a["_usage"], "sentences": rows}


def main(argv):
    if len(argv) != 1:
        sys.exit(__doc__)
    data = json.loads(read_text(argv[0]))
    with ThreadPoolExecutor(8) as pool:
        emit(list(pool.map(lambda p: check_paragraph(p, data.get("facts")), data["paragraphs"])))


if __name__ == "__main__":
    main(sys.argv[1:])
