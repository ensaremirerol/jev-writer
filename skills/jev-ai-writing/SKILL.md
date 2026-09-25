---
name: jev-ai-writing
description: Audit a whole paper for signs of AI writing (Wikipedia:Signs_of_AI_writing, tuned for academic papers). Works on LaTeX directly, reporting .tex line numbers and checking headings, bold, tables, quotes and citations (missing bib keys, lost citations), or on plain text. Regex rules cover AI vocabulary, puffery, trailing -ing clauses, vague attribution without a citation, negative parallelism, em dashes, chat residue, placeholders and LLM markup artifacts; Jev (TypeSafe System One model) adds semantic judgements. Use when the user asks whether a paper or draft "sounds like AI", wants AI tells removed, or wants a style audit or pre-submission lint.
---

# jev-ai-writing

`scripts/ai_writing.py` audits the **whole document**. It reports each hit with a rule ID, a hard or soft level, and a location, plus document-wide counts. Rule IDs, rationale and config keys are in `${CLAUDE_SKILL_DIR}/rules.md`; read it when you need to explain a rule.

Needs a Jev API key. It is set when the plugin is installed, or by running `scripts/setup.py` at the plugin root. If a run fails for a missing key, ask the user to run that script in their own terminal, and never ask them to paste the key into the chat. `--offline` runs only the regex rules and needs no key.

## Usage
```
python3 ${CLAUDE_SKILL_DIR}/scripts/ai_writing.py paper.tex [--baseline old.tex] [--config style.json]
```
- **LaTeX (`.tex`):** pass the source file directly.
  - Hits carry `.tex` line numbers.
  - Structure and citation rules also run. The bib defaults to `refs.bib` next to the file; change it with `--bib`.
  - `--baseline old.tex` flags citations the new draft dropped.
- **Anything else:** plain text, with paragraphs separated by blank lines. From a PDF, run `pdftotext` and remove headers, footers and the reference list.
- **`--config style.json`:** per-paper thresholds, glossary, allowed vocabulary and disabled rules. See `${CLAUDE_SKILL_DIR}/config.example.json` and the Config section of `rules.md`. Suggest one when a paper has fixed terminology.
- **`--format text`:** human-readable `file:line [RULE/level] message :: excerpt` lines.
- **`--hard-only`:** lists only hard hits.
- **Exit code 1 means hard hits were found,** not that the script crashed. The report is still printed.

## Reading the output
- **Start with `summary.by_rule` and `document`.** A single hit is normal in human prose. The tell is a pattern repeated across the document:
  - many contrast phrases (L4);
  - em dashes above the limit (S5);
  - several `jev:` hits of the same kind;
  - a low `sentence_words_stdev` relative to the mean.
- **Hard hits must be fixed or justified.** Justify one with `% style-ok: RULE` at the end of the line, used rarely and never for L1.
- **Soft hits are for review.** Many are fine in a paper, for example a real list of three, or a hedge where the evidence really is uncertain.
- **A regex hit and a `jev:` hit on the same sentence** (C1 with jev:C1, L4 with jev:L4) is strong evidence. A `jev:` hit on its own catches paraphrases the word lists miss, but read the sentence before acting.
- **Look for the same phrase repeated verbatim** in different sections, e.g. the introduction and the conclusion. The script doesn't detect this.
- **Report patterns and the worst examples**, each with a rewrite. Don't list every hit.
- **Rewrite in the paper's register.** Plainer is not always better: keep the prose formal and academic, and replace the sign rather than simplifying the sentence.
