"""LaTeX side of the AI-writing audit: prose paragraphs with source line numbers, plus the
structural and citation rules that only make sense on .tex (headings, bold, tables, quotes,
bib keys, lost citations). Ported from a project-specific checker (WRITING_RULES.md)."""
import re
from pathlib import Path

CITE, REF = "〔CITE〕", "〔REF〕"
SKIP_ENVS = {"tikzpicture", "equation", "equation*", "align", "align*", "verbatim", "lstlisting", "keywords"}
TABLE_ENVS = {"tabular", "tabular*", "tabularx"}
BACKMATTER = re.compile(r"ethics|data availability|reproducibility|acknowledg|declaration", re.I)


class Hit(dict):
    def __init__(self, rule, level, msg, excerpt="", line=None, **kw):
        super().__init__(rule=rule, level=level, msg=msg, excerpt=" ".join(excerpt.split())[:120], line=line, **kw)


def clean(text):
    """A comment-free LaTeX line as plain prose; citations and refs become markers."""
    t = re.sub(r"\\(begin|end)\{[^}]*\}", " ", text)
    t = re.sub(r"\\(cite|citep|citet)\{[^}]*\}", f" {CITE} ", t)
    t = re.sub(r"\\(ref|autoref|cref|eqref|label)\{[^}]*\}", f" {REF} ", t)
    t = re.sub(r"\\(url|input|include|href)\{[^}]*\}", " ", t)
    t = re.sub(r"\$[^$]*\$", " MATH ", t)
    t = t.replace("``", '"').replace("''", '"').replace("~", " ").replace("\\%", "%").replace("---", "\u2014").replace("--", "–")
    t = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", " ", t)
    t = re.sub(r"[{}]", "", t)
    return re.sub(r"\s+", " ", t)


def title_case_hits(title, line, proper):
    toks = re.findall(r"[A-Za-z][\w.\-]*", title)
    return [Hit("S1", "hard", f"title case in heading ('{w}'); use sentence case", title, line)
            for w in toks[1:] if w[0].isupper() and not w.isupper() and w not in proper]


def parse(path, cfg):
    """Returns (paragraphs, hits, doc). A paragraph is a list of (line, text, exempt, backmatter, abstract)."""
    raw_lines = Path(path).read_text(encoding="utf-8").splitlines()
    hits, paras, cur = [], [], []
    env_stack, started, after_title, in_abstract, backmatter = [], False, False, False, False
    headings, para_titles, cite_keys, dash_body, dash_abs, table_rows = [], {}, [], [], [], []
    emph, rows = 0, None

    def flush():
        nonlocal cur
        if cur:
            paras.append(cur)
        cur = []

    for i, raw in enumerate(raw_lines, 1):
        if re.match(r"\s*%", raw) and len(raw) > 100:
            hits.append(Hit("M5", "hard", "long comment line: is prose trapped in a comment?", raw[-60:], i))
        if not started:
            started = r"\begin{document}" in raw
            continue
        if r"\end{document}" in raw:
            break
        after_title |= r"\maketitle" in raw
        m = re.search(r"%\s*style-ok:\s*([\w\-., ]+)", raw)
        exempt = {x.strip() for x in m.group(1).split(",")} if m else set()
        line = re.sub(r"(?<!\\)%.*", "", raw)
        abstract_line = in_abstract or r"\begin{abstract}" in line   # also a one-line abstract

        for kind, env in re.findall(r"\\(begin|end)\{([^}]+)\}", line):
            if kind == "begin":
                env_stack.append(env)
                if env == "abstract":
                    in_abstract = True
                    flush()
                if env in TABLE_ENVS:
                    rows = None
            else:
                while env in env_stack and env_stack.pop() != env:
                    pass
                if env == "abstract":
                    in_abstract = False
                if env in TABLE_ENVS and rows is not None:
                    table_rows.append((i, rows))
                    rows = None
        in_skip = any(e in SKIP_ENVS for e in env_stack)
        in_table = any(e in TABLE_ENVS for e in env_stack)

        if not in_skip:  # quotes inside listings and code are fine
            for _ in re.findall(r"[“”‘’]", line):
                hits.append(Hit("S7", "hard", "curly quote; use `` '' or '", line, i))
            if re.search(r'(?<!\\)"', line):
                hits.append(Hit("S7", "hard", 'straight " in text; use `` \'\'', line, i))
        if re.search(cfg["placeholder_re"], line) and not in_skip:
            hits.append(Hit("M4", "hard", "placeholder in rendered text", line, i))

        if in_table:
            if r"\midrule" in line and rows is None:
                rows = 0
            elif rows is not None and r"\\" in line and r"\bottomrule" not in line:
                rows += 1

        hm = re.search(r"\\(section|subsection|subsubsection|paragraph)(\*?)\{(.+?)\}", line)
        if hm:
            flush()
            level, title = hm.group(1), hm.group(3)
            headings.append((i, level, title))
            if level == "section":
                backmatter = bool(BACKMATTER.search(title))
            if level == "paragraph":
                para_titles.setdefault(title.strip(), []).append(i)
            elif not backmatter and "S1" not in exempt:
                hits += title_case_hits(title, i, cfg["proper_nouns"])
                if re.search(r"\band\b", title):
                    hits.append(Hit("C8", "soft", "'X and Y' heading; both halves need content", title, i))
            rest = line[hm.end():].strip()
            if level != "paragraph" or not rest:
                continue
            line = rest

        if in_skip or (not after_title and not abstract_line):
            flush()
            continue
        if re.search(r"\\textbf\{", line) and not in_table and not backmatter:
            hits.append(Hit("S3", "hard", "\\textbf outside a table", line, i))
        if re.search(r"\\item\s*(\[[^\]]*\])?\s*\\(textbf|emph)\{", line):
            hits.append(Hit("S4", "hard", "inline-header list item; write prose", line, i))
        if not backmatter:
            emph += len(re.findall(r"\\emph\{", line))
        for k in re.findall(r"\\cite[pt]?\{([^}]*)\}", line):
            cite_keys.append((i, [x.strip() for x in k.split(",") if x.strip()]))
        if not in_table and "S5" not in exempt:
            (dash_abs if abstract_line else dash_body).extend([i] * len(re.findall(r"---|\u2014", line)))
            if re.search(r"\w \-\- \w", line):
                hits.append(Hit("S5", "soft", "spaced -- used as a dash; '--' is for ranges", line, i))
        if in_table and r"\caption" not in line:
            flush()
            continue
        text = clean(line).strip()
        if not text:
            flush()
            continue
        cur.append((i, text, exempt, backmatter, abstract_line))
        if r"\end{abstract}" in line:
            flush()
    flush()

    # document structure
    for idx, (ln, level, title) in enumerate(headings):
        if level == "section" and idx + 1 < len(headings) and headings[idx + 1][1] == "subsection":
            between = [clean(re.sub(r"(?<!\\)%.*", "", l)) for l in raw_lines[ln:headings[idx + 1][0] - 1]]
            if not any(re.search(r"[A-Za-z]{3}", b.replace(REF, "")) for b in between):
                hits.append(Hit("S2", "hard", "section contains only subsections; add text", title, ln))
    seen = set()
    for ln, level, title in headings:
        if level == "subsection" and "section" not in seen:
            hits.append(Hit("S8", "hard", "subsection before any section", title, ln))
        if level == "subsubsection" and "subsection" not in seen:
            hits.append(Hit("S8", "hard", "subsubsection without a subsection", title, ln))
        seen.add(level)
        if level == "section":
            seen.discard("subsection")
    for title, lns in para_titles.items():
        if len(lns) >= 3:
            hits.append(Hit("S4", "soft", f"run-in header '{title}' repeated {len(lns)} times", "", lns[0]))
    for ln, n in table_rows:
        if n < 3:
            hits.append(Hit("S6", "soft", f"table with {n} body rows; could it be a sentence?", "", ln))
    for ln in dash_abs:
        if len(dash_abs) > cfg["em_dash_max_abstract"]:
            hits.append(Hit("S5", "hard", "em dash in the abstract", raw_lines[ln - 1], ln))
    for ln in dash_body:
        hits.append(Hit("S5", "soft", f"em dash (max {cfg['em_dash_max_body']} in the body)", raw_lines[ln - 1], ln))
    if len(dash_body) > cfg["em_dash_max_body"]:
        hits.append(Hit("S5", "hard", f"{len(dash_body)} em dashes in the body (max {cfg['em_dash_max_body']})", "", dash_body[0]))

    hits += citation_hits(Path(path), cite_keys, raw_lines, cfg)
    doc = {"em_dashes_body": len(dash_body), "em_dashes_abstract": len(dash_abs), "emph": emph}
    return paras, hits, doc


def citation_hits(path, cite_keys, raw_lines, cfg):
    hits = []
    bib = Path(cfg["bib"]) if cfg.get("bib") else path.with_name("refs.bib")
    if bib.exists():
        entries = {m.group(1): m.group(2) for m in re.finditer(r"@\w+\{([^,\s]+),(.*?)(?=\n@|\Z)", bib.read_text(encoding="utf-8"), re.S)}
        for ln, keys in cite_keys:
            if len(keys) > 4:
                hits.append(Hit("R3", "soft", f"{len(keys)} keys in one \\cite; review only, never delete a citation for this", ",".join(keys), ln))
            for k in keys:
                if k not in entries:
                    hits.append(Hit("R1", "hard", f"cite key not in {bib.name}", k, ln))
                elif not re.search(r"\b(doi|url)\s*=", entries[k], re.I) and "\\url" not in entries[k]:
                    hits.append(Hit("R1", "soft", "cited entry has no doi/url", k, ln))
    else:
        hits.append(Hit("R1", "soft", f"{bib} not found; citation checks skipped"))
    if cfg.get("baseline"):
        def keyset(txt):
            txt = "\n".join(re.sub(r"(?<!\\)%.*", "", l) for l in txt.splitlines())
            return {k.strip() for c in re.findall(r"\\cite[pt]?\{([^}]*)\}", txt) for k in c.split(",") if k.strip()}
        removed = {k.strip() for m in re.finditer(r"%\s*cite-removed:\s*([^(\n]*)", "\n".join(raw_lines)) for k in m.group(1).split(",") if k.strip()}
        now = {k for _, ks in cite_keys for k in ks}
        for k in sorted(keyset(Path(cfg["baseline"]).read_text(encoding="utf-8")) - now - removed):
            hits.append(Hit("R4", "hard", f"cited in {Path(cfg['baseline']).name} but no longer cited; record a deliberate removal as '% cite-removed: {k} (why)'", k, 1))
    return hits
