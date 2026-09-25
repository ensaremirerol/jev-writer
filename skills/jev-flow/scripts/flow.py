#!/usr/bin/env python3
"""Check whether ONE sentence breaks the flow of the span (paragraph) it sits in.

Usage: flow.py "SENTENCE" SPAN_FILE      (SPAN_FILE may be "-" for stdin)
The sentence must appear in the span; its previous and next sentences are quoted to Jev.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from jev import ask, emit, noul, r2, read_text, split_sentences


def locate(sentence, span):
    sents = split_sentences(span)
    target = " ".join(sentence.split())
    for i, s in enumerate(sents):
        if target in s or s in target:
            return sents, i
    sys.exit("error: sentence not found in span")


def main(argv):
    if len(argv) != 2:
        sys.exit(__doc__)
    sents, i = locate(argv[0], read_text(argv[1]))
    ctx = {}
    if i:
        ctx["previous_sentence"] = sents[i - 1]
    if i + 1 < len(sents):
        ctx["next_sentence"] = sents[i + 1]
    if not ctx:
        sys.exit("error: span has only this sentence; flow needs at least one neighbour")
    a = ask({"span": sents}, {"flow": noul(
        "Does the sentence break the flow between the previous and next sentence of `span`?",
        "The reader must stop: it jumps topic, lacks the link to its neighbours, or repeats them.",
        "It continues or develops the previous sentence and leads into the next.",
        sentence=sents[i], **ctx,
    )})["flow"]
    emit({"sentence": sents[i], "index": i, **ctx, "p_breaks_flow": r2(a["noul"]), "breaks_flow": a["noul"] >= 0.5})


if __name__ == "__main__":
    main(sys.argv[1:])
