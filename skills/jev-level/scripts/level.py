#!/usr/bin/env python3
"""Check whether each sentence fits the requested writing level.

Usage: level.py --level "target reader" FILE      (FILE may be "-" for stdin; paragraphs split on blank lines)
One Jev request per paragraph; every sentence is asked in parallel.
"""
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from jev import ask, emit, noul, r2, read_text, split_paragraphs, split_sentences


def check_paragraph(text, level):
    sents = split_sentences(text)
    q = {
        f"s{i}": noul(
            "Is the sentence written for the reader described in `level`?",
            "Vocabulary, sentence length and assumed background fit the reader in `level`.",
            "Too simple, too technical, or assumes background the reader in `level` lacks.",
            sentence=s,
            focus="Vocabulary, sentence length, and how much background knowledge it assumes.",
        )
        for i, s in enumerate(sents)
    }
    a = ask({"level": level, "paragraph": sents}, q)
    return [{"i": i, "text": s, "p_on_level": r2(a[f"s{i}"]["noul"]), "off_level": a[f"s{i}"]["noul"] < 0.5} for i, s in enumerate(sents)]


def main(argv):
    if len(argv) != 3 or argv[0] != "--level":
        sys.exit(__doc__)
    level = argv[1]
    with ThreadPoolExecutor(8) as pool:
        emit({"level": level, "paragraphs": list(pool.map(lambda p: check_paragraph(p, level), split_paragraphs(read_text(argv[2]))))})


if __name__ == "__main__":
    main(sys.argv[1:])
