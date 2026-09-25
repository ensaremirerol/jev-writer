#!/usr/bin/env python3
"""Audit a document for signs of AI writing (Wikipedia:Signs_of_AI_writing, tuned for papers).

Usage: ai_writing.py FILE [--config rules.json] [--bib refs.bib] [--baseline old.tex]
                          [--offline] [--hard-only] [--format json|text]

A FILE ending in .tex runs LaTeX mode: hits carry .tex line numbers; heading, bold, table,
quote and citation rules run too; a line ending in `% style-ok: RULE[,RULE]` is exempt from those
rules. Any other file is plain text with paragraphs split on blank lines.
Regex rules run locally. Jev adds semantic judgements (rule ids prefixed "jev:"), one request
per paragraph; --offline skips them. Rule ids and rationale: ../rules.md.
Exit code 1 if any hard rule fails (the report is still printed).
"""
import argparse, json, re, statistics, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import latex
from jev import ask, noul, r2, split_paragraphs, split_sentences
from latex import CITE, REF, Hit

DEFAULTS = {
    "em_dash_max_body": 3,
    "em_dash_max_abstract": 0,
    "negative_parallelism_max": 3,
    "long_sentence_words": 40,
    "emph_per_words": 250,
    "disable": ["S10"],          # colon review is one author's preference; enable it per paper
    "allow_vocabulary": [],      # words to drop from L1, e.g. ["robust"] in an ML paper
    "extra_vocabulary": [],      # words to add to L1
    "proper_nouns": [],          # capitalised words allowed in headings besides acronyms
    "glossary": [],              # [{"pattern": regex, "advice": "use X", "level": "soft", "unless_before": regex}]
    # a paragraph matching none of this and citing nothing is generic (R0.2): numbers, acronyms,
    # code-like tokens; add the study's own terms (sites, datasets) per paper
    "specific_detail": r"\d|\b[A-Z]{2,}|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b|\w[:_]\w",
    "placeholder_re": r"\bTBD\b|\bTODO\b|XXX|\[ref\]|\?\?|YYYY|\[X\]|lorem ipsum|\[(?:citation needed|needs verification|citation|cite)\]",
}


def words(pats):
    return re.compile(r"\b(?:" + "|".join(pats) + r")\b", re.I)


C1 = [r"(?:is|as|a) (?:testament|reminder)", r"(?:crucial|pivotal|vital|significant|key|central) (?:role|moment)",
      r"underscores? (?:its|the) (?:importance|significance)", r"reflects? (?:a )?broader", r"setting the stage",
      r"marks? (?:a|the) (?:shift|turning point|moment)", r"represents? a (?:shift|milestone)", r"turning point",
      r"evolving landscape", r"focal point", r"indelible", r"deeply rooted", r"lasting (?:impact|legacy)",
      r"cornerstone", r"paves? the way", r"sheds? light"]
C2 = [r"widely cited", r"leading (?:journals?|experts?|researchers?)", r"prominent", r"well-known",
      r"growing body", r"extensive literature", r"independent coverage"]
C3 = (r",\s+(?:highlighting|underscoring|emphasi[sz]ing|ensuring|reflecting|symboli[sz]ing|contributing to|"
      r"fostering|cultivating|encompassing|enhancing|showcasing|demonstrating|illustrating|reinforcing|paving)\b")
C4 = [r"groundbreaking", r"renowned", r"cutting-edge", r"state-of-the-art", r"seamless(?:ly)?", r"unprecedented",
      r"remarkabl[ey]", r"vibrant", r"nestled", r"in the heart of", r"diverse array", r"commitment to",
      r"exemplif(?:y|ies|ied)", r"boasts? a"]
C4_SOFT = [r"novel", r"innovative", r"powerful", r"comprehensive", r"holistic", r"rich"]
C5 = (r"\b(?:(?:studies|researchers|experts|scholars|observers|critics|the literature|"
      r"(?:prior|previous|existing) (?:work|studies|research)|industry reports)(?: have| has)? "
      r"(?:show|shown|shows|suggest|suggests|argue|argues|agree|agrees|found|find|report|reports|note|notes|"
      r"indicate|indicates|claim|claims|believe|demonstrate|demonstrated)|"
      r"it is (?:widely|generally|commonly) (?:known|accepted|believed|recognized))\b")
C6 = [r"despite (?:these|its|their|the) (?:[a-z]+ )?(?:challenges|limitations)", r"faces? (?:several |many |significant |numerous )?challenges",
      r"holds? (?:great |significant )?promise", r"future (?:outlook|prospects)", r"remains? to be seen", r"exciting"]
# Wikipedia's "words to watch" plus common additions. "key" is soft: normal in papers ("key finding").
L1 = [r"additionally", r"aligns? with", r"aligned with", r"boasts?", r"bolster(?:s|ed|ing)?", r"crucial(?:ly)?",
      r"deep dive", r"delv(?:e|es|ed|ing)", r"emphasi[sz](?:e|es|ed|ing)", r"enduring", r"enhanc(?:e|es|ed|ing|ement)",
      r"foster(?:s|ed|ing)?", r"garner(?:s|ed|ing)?", r"highlight(?:s|ed|ing)?", r"interplay", r"intricat(?:e|ely|acy|acies)",
      r"landscape", r"meticulous(?:ly)?", r"pivotal", r"robust(?:ly|ness)?", r"showcas(?:e|es|ed|ing)", r"tapestry",
      r"testament", r"underscor(?:e|es|ed|ing)", r"valuable", r"vibrant", r"notably", r"furthermore", r"moreover",
      r"leverag(?:e|es|ed|ing)", r"utili[sz](?:e|es|ed|ing|ation)", r"facilitat(?:e|es|ed|ing)", r"multifaceted",
      r"nuanced", r"paramount", r"realm", r"streamlin(?:e|es|ed|ing)", r"empower(?:s|ed|ing)?", r"unlock(?:s|ed|ing)?",
      r"resonates? with"]
L2 = [r"(?:serves?|served|serving|stands?|stood|functions?|acts?|operates?) as (?:a|an|the)", r"features an?",
      r"offers an?", r"refers? to"]
L3 = [r"associated with", r"in connection (?:with|to)", r"connected (?:to|with)", r"in association with"]
L4 = [r"not only", r"not just", r"not merely", r"rather than", r"instead of", r"isn'?t just",
      r"is not [^.,;]{1,40}, but", r"it'?s not [^.]{1,60}[,;] (?:it'?s|but)"]
M1 = [r"i hope", r"let me know", r"certainly", r"of course", r"would you like", r"as requested", r"feel free",
      r"happy to", r"as of my (?:last|latest) (?:update|knowledge)", r"knowledge cutoff", r"great question", r"as an ai"]
M2 = [r"in this (?:section|paper|note|work),? we (?:will )?(?:discuss|explore|present|describe|examine|show)",
      r"this section (?:explains|describes|presents|discusses|shows)"]
M3 = [r"not (?:widely|well|extensively) documented", r"based on (?:the )?available (?:information|data)",
      r"limited information", r"(?:to|as of) (?:my|our) knowledge"]
HEDGES = [r"may", r"might", r"could", r"likely", r"possibly", r"potentially", r"seems?", r"appears? to", r"suggests?"]
H1 = [r"it is (?:important|crucial|critical|worth) (?:to note|noting|mentioning|to remember)", r"worth noting",
      r"importantly", r"crucially", r"interestingly", r"note that"]
H2 = [r"in summary", r"in conclusion", r"overall,", r"to summari[sz]e", r"in short", r"taken together", r"all in all", r"to conclude"]
P1 = [r"utili[sz](?:e|es|ed|ing|ation)", r"leverag(?:e|es|ed|ing)", r"facilitat(?:e|es|ed|ing)", r"endeavou?r(?:s|ed|ing)?", r"commenc(?:e|es|ed|ing)"]
ARTIFACTS = (r"contentReference|oaicite|oai_citation|turn\d+search\d+|attributableIndex|\[cite:\s*\d+\]|\[span_\d+\]|"
             r"grok_card|attached_file|ppl-ai-file-upload|:::writing|utm_(?:source|medium|campaign)=")

# Semantic signs regex cannot catch reliably, keyed by the rule they back: (question, true, false).
SEMANTIC = {
    "C1": ("Does the sentence inflate importance with generic claims about significance, impact, legacy or broader trends instead of stating a concrete result?",
           "Asserts importance or broader impact without a concrete, checkable detail.",
           "States concrete content; any importance claim is tied to a specific result."),
    "C3": ("Does the sentence add a vague participle phrase (such as 'highlighting ...', 'underscoring ...', 'ensuring ...', 'reflecting ...') that comments on the point but adds no information?",
           "Contains an '-ing' tail or aside that only restates importance or meaning.",
           "Every clause adds concrete information."),
    "C4": ("Is the sentence written in a promotional, advertising tone (e.g. 'groundbreaking', 'remarkable', 'seamless', 'powerful') rather than neutral academic prose?",
           "Uses marketing or hype adjectives to sell the work.",
           "Neutral, measured academic wording."),
    "C5": ("Does the sentence attribute a claim to unnamed authorities or findings (e.g. 'experts argue', 'studies show', 'comparisons find') without a specific citation?",
           "Appeals to unnamed sources or findings with no specific reference.",
           "Claims are either the authors' own or tied to a specific citation."),
    "L4": ("Does the sentence use a rhetorical contrast such as 'not only X but also Y', 'it is not X, it is Y', or 'Y rather than X' where a plain statement would do?",
           "Uses a contrast construction for rhetorical effect.",
           "States the point directly, or the contrast is a real technical comparison."),
    "L5": ("Does the sentence list exactly three adjectives, nouns or phrases for rhythm rather than because there are exactly three distinct things?",
           "A triplet used for rhetorical rhythm; items overlap or are vague.",
           "No triplet, or the three items are distinct, specific and all needed."),
    "C6": ("Does the sentence follow the formula 'Despite X, ... faces challenges ...' or give generic speculation about future prospects?",
           "Generic challenges or future-outlook boilerplate.",
           "Specific limitation or future step, or not about challenges at all."),
}


def build_rules(cfg):
    vocab = [w for w in L1 if not any(re.fullmatch(w, a, re.I) for a in cfg["allow_vocabulary"])] + [re.escape(w) for w in cfg["extra_vocabulary"]]
    return {
        "C1": (words(C1), "hard", "inflated significance"),
        "C2": (words(C2), "soft", "source described by prestige; say what it found"),
        "C3": (re.compile(C3, re.I), "hard", "trailing -ing analysis clause"),
        "C4": (words(C4), "hard", "promotional word"),
        "C4s": (words(C4_SOFT), "soft", "promotional-leaning word"),
        "C6": (words(C6), "hard", "challenges/future-prospects formula"),
        "L1": (words(vocab), "hard", "AI-vocabulary word"),
        "L1s": (words([r"key"]), "soft", "AI-vocabulary word, common in papers"),
        "L2": (words(L2), "hard", "copula avoidance; prefer is/are/has"),
        "L3": (words(L3), "soft", "vague connection; state the relation"),
        "L4": (re.compile("(?:" + "|".join(L4) + ")", re.I), "soft", "negative parallelism"),
        "M1": (words(M1), "hard", "chat residue"),
        "M2": (words(M2), "soft", "signposting"),
        "M3": (words(M3), "hard", "knowledge-gap disclaimer"),
        "M3h": (words(HEDGES), "soft", "hedge; give the reason for the uncertainty or cut it"),
        "H1": (words(H1), "hard", "didactic disclaimer"),
        "H2": (words(H2), "hard", "summary phrase"),
        "P1": (words(P1), "hard", "stiff verb; use a plain one"),
        "P1s": (words([r"attempt(?:s|ed|ing)?"]), "soft", "stiff verb ('tried')"),
        "A1": (re.compile(ARTIFACTS), "hard", "LLM markup artifact"),
        "A2": (re.compile(r"[\U0001F300-\U0001FAFF☀-➿]"), "hard", "emoji"),
        "A3": (re.compile(r"\*\*[^*]+\*\*|^#{1,6}\s"), "soft", "Markdown formatting"),
    }


def exempted(rid, ex):
    return rid in ex or rid.rstrip("sh") in ex


def text_paragraphs(path):
    """Plain text: every paragraph is one span with no line number."""
    return [[(None, " ".join(p.split()), set(), False, False)] for p in split_paragraphs(Path(path).read_text(encoding="utf-8"))]


def audit_paragraph(pi, para, cfg, rules, offline):
    joined, spans = "", []
    for ln, text, ex, bm, ab in para:
        spans.append((len(joined), ln, ex))
        joined += text + " "
    joined = joined.strip()
    backmatter, abstract = para[0][3], para[0][4]

    def at(pos):
        ln, ex = spans[0][1], spans[0][2]
        for start, l, e in spans:
            if start <= pos:
                ln, ex = l, e
        return ln, ex

    hits = []

    def add(rid, level, msg, pos, excerpt, **kw):
        ln, ex = at(pos)
        if not exempted(rid, ex):
            hits.append(Hit(rid, level, msg, excerpt, ln, paragraph=pi, **kw))

    for rid, (rx, level, msg) in rules.items():
        if backmatter and rid not in ("M1", "A1"):   # formulaic back matter: only chat residue and artifacts
            continue
        for m in rx.finditer(joined):
            if rid == "M3h" and m.group(0) == "May":
                continue  # the month
            if rid == "L1s" and re.match(r"key[\s-]+(?:identifier|column|field|value)", joined[m.start():m.start() + 20], re.I):
                continue
            add(rid, level, msg, m.start(), joined[max(0, m.start() - 35): m.end() + 35])
    if backmatter:
        return hits, [], 0
    if "S10" not in cfg["disable"]:
        for m in re.finditer(r"[^\s:]:(?=\s|$)", joined):
            add("S10", "soft", "colon; avoid if it introduces an explanation", m.start(), joined[max(0, m.start() - 50): m.end() + 40])
    for g in cfg["glossary"]:
        for m in re.finditer(g["pattern"], joined, re.I):
            before = joined[max(0, m.start() - 40):m.start()]
            if m.group(0)[0].isupper() and m.start() > 1 and joined[m.start() - 2] not in ".!?":
                continue  # capitalised mid-sentence: part of a proper name, e.g. 'Medical Centre'
            if g.get("unless_before") and re.search(g["unless_before"], before):
                continue
            add("H3", g.get("level", "soft"), g["advice"], m.start(), joined[max(0, m.start() - 30): m.end() + 30])

    # sentences
    sents, pos = [], 0
    for s in split_sentences(joined):
        start = joined.find(s, pos)
        pos = max(start, pos) + len(s)
        sents.append((max(start, 0), s))
    cited = lambda s: CITE in s or re.search(r"\[\d+(?:\s*[,–-]\s*\d+)*\]", s)
    lengths, triads = [], 0
    for start, s in sents:
        n = len(re.findall(r"[A-Za-z0-9]+", s))
        lengths.append(n)
        if n > cfg["long_sentence_words"]:
            add("P4", "soft", f"long sentence ({n} words)", start, s)
        if re.search(C5, s, re.I) and not cited(s):
            add("C5", "hard", "vague attribution without a citation", start, s)
        tri = [m for m in re.finditer(r"\b([\w-]+(?: [\w-]+)?), ([\w-]+(?: [\w-]+)?),? (and|or) ([\w-]+(?: [\w-]+)?)\b", s)
               if not s[:m.start()].rstrip().endswith(",")]
        if tri:
            triads += 1
            add("L5", "soft", "list of three; keep only if all three are real", start, s)
    if triads >= 2:
        add("L5", "soft", f"{triads} lists of three in one paragraph", 0, "")
    if len(lengths) >= 4 and statistics.pstdev(lengths) < 4:
        add("P4", "soft", "sentence lengths hardly vary in this paragraph", 0, "")
    if sents and re.match(r"(This|These|Together|Taken together|Thus|Hence)\b.*\b(shows?|demonstrates?|illustrates?|confirms?|suggests?|highlights?)\b", sents[-1][1]):
        add("H2", "soft", "paragraph ends by restating its point", sents[-1][0], sents[-1][1])
    nwords = len(re.findall(r"[A-Za-z]+", joined))
    if nwords >= 25 and not abstract and not re.search(cfg["specific_detail"], joined) and not cited(joined) and REF not in joined:
        add("R0.2", "soft", "generic paragraph: no study-specific detail", 0, joined)

    # Jev: one request per paragraph, every sentence and sign in parallel
    if not offline and sents:
        plain = [s.replace(CITE, "[1]").replace(REF, "1") for _, s in sents]
        q = {f"s{i}_{k}": noul(qq, t, f, sentence=s) for i, s in enumerate(plain) for k, (qq, t, f) in SEMANTIC.items()}
        a = ask({"paragraph": plain}, q)
        for i, (start, s) in enumerate(sents):
            for k in SEMANTIC:
                p = a[f"s{i}_{k}"]["noul"]
                if p >= 0.5:
                    add(f"jev:{k}", "soft", f"Jev: {SEMANTIC[k][1][0].lower() + SEMANTIC[k][1][1:]}", start, s, p=r2(p))
    return hits, lengths, nwords


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file")
    ap.add_argument("--config", help="JSON file overriding the defaults (thresholds, glossary, vocabulary, disabled rules)")
    ap.add_argument("--bib", help="bibliography for citation checks (default: refs.bib next to the .tex)")
    ap.add_argument("--baseline", help="earlier .tex; every key it cites must still be cited (R4)")
    ap.add_argument("--offline", action="store_true", help="regex rules only, no Jev calls")
    ap.add_argument("--hard-only", action="store_true", help="list hard hits only (the summary still counts all)")
    ap.add_argument("--format", choices=["json", "text"], default="json")
    args = ap.parse_args(argv)

    cfg = dict(DEFAULTS)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text()))
    cfg["proper_nouns"] = set(cfg["proper_nouns"])
    cfg["bib"], cfg["baseline"] = args.bib, args.baseline
    rules = {k: v for k, v in build_rules(cfg).items() if k not in cfg["disable"]}

    tex = args.file.endswith(".tex")
    if tex:
        paras, hits, doc = latex.parse(args.file, cfg)
    else:
        paras, hits, doc = text_paragraphs(args.file), [], {}
    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(lambda ip: audit_paragraph(ip[0], ip[1], cfg, rules, args.offline), enumerate(paras)))

    lengths, body_words = [], 0
    for h, ls, nw in results:
        hits += h
        lengths += ls
        body_words += nw
    if not tex:
        n = sum(p[0][1].count("—") for p in paras)
        doc["em_dashes_body"] = n
        if n > cfg["em_dash_max_body"]:
            hits.append(Hit("S5", "hard", f"{n} em dashes (max {cfg['em_dash_max_body']})"))
    neg = sum(1 for h in hits if h["rule"] == "L4")
    if neg > cfg["negative_parallelism_max"]:
        hits.append(Hit("L4", "soft", f"{neg} negative parallelisms (max {cfg['negative_parallelism_max']})"))
    if tex and body_words and doc["emph"] > body_words / cfg["emph_per_words"]:
        hits.append(Hit("S9", "soft", f"{doc['emph']} \\emph for {body_words} words (max 1 per {cfg['emph_per_words']})"))
    hits = [h for h in hits if h["rule"] not in cfg["disable"]]
    hits.sort(key=lambda h: (h["line"] or 0, h.get("paragraph", -1), h["rule"]))

    by_rule = {}
    for h in hits:
        by_rule[h["rule"]] = by_rule.get(h["rule"], 0) + 1
    hard = sum(h["level"] == "hard" for h in hits)
    report = {
        "file": args.file,
        "mode": "latex" if tex else "text",
        "document": {
            "paragraphs": len(paras), "sentences": len(lengths), "words": body_words,
            "sentence_words_mean": r2(statistics.mean(lengths)) if lengths else 0,
            # Uniform sentence lengths are a machine-prose tell; human prose varies more.
            "sentence_words_stdev": r2(statistics.pstdev(lengths)) if lengths else 0,
            **doc,
            "negative_parallelisms": neg,
            "per_1k_words": {k: r2(v * 1000 / body_words) for k, v in by_rule.items() if body_words},
        },
        "summary": {"hard": hard, "soft": len(hits) - hard, "by_rule": dict(sorted(by_rule.items()))},
        "hits": [h for h in hits if not (args.hard_only and h["level"] == "soft")],
    }
    if args.format == "text":
        name = Path(args.file).name
        for h in report["hits"]:
            where = h["line"] if h["line"] else f"p{h.get('paragraph', '?')}"
            p = f" (p={h['p']})" if "p" in h else ""
            print(f"{name}:{where} [{h['rule']}/{h['level']}] {h['msg']}{p}" + (f" :: {h['excerpt']}" if h["excerpt"] else ""))
        s = report["summary"]
        print(f"\n--- summary ---\nwords: {body_words}  em dashes: {doc.get('em_dashes_body', 0)} body"
              + (f", {doc['em_dashes_abstract']} abstract" if tex else "") + f"  negative parallelisms: {neg}")
        print(f"hard: {s['hard']}   soft: {s['soft']}\nby rule: " + ", ".join(f"{k}={v}" for k, v in s["by_rule"].items()))
    else:
        json.dump(report, sys.stdout, indent=1, ensure_ascii=False)
        print()
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
