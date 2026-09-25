# AI-writing rules

Adapted from Wikipedia's field guide [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)
for academic papers, merged with a project checklist written for a 5-page CEUR paper in LaTeX.

- **hard**: must be zero in the body. **soft**: review every hit; keep it only if it is the plainest way to say something true.
- `jev:` rules are Jev's semantic judgements (probability ≥ 0.5). They back the regex rule with the same ID and catch
  paraphrases no word list matches. They are always soft.
- In LaTeX, a line ending in `% style-ok: RULE[,RULE]` is exempt from those rules. Use it rarely, never for L1.
- Back matter (Ethics, Data availability, Acknowledgments, declarations) only gets M1, A1 and the mechanical LaTeX checks.

## 0. The rule behind the rules
These patterns are **signs** of a deeper problem, not the problem itself. Replacing "crucial" with "important" fixes
nothing if the sentence still claims more than the evidence shows. Check claims against the sources first (the
`jev-fact-check` skill), then style. R0.2 flags a paragraph that has no study-specific detail (a number, acronym,
code-like token or citation) and so could be pasted into any other paper.

## 1. Content
| ID | Sign | Check |
|---|---|---|
| C1 | Undue emphasis on significance, legacy, broader trends | hard: *is a testament/reminder, crucial/pivotal/vital/key role, underscores the importance, reflects broader, setting the stage, marks a shift, turning point, evolving landscape, focal point, deeply rooted, lasting impact, cornerstone, paves the way, sheds light*; `jev:C1` |
| C2 | Sources described by prestige instead of content | soft: *widely cited, leading journals, prominent, well-known, growing body, extensive literature* |
| C3 | Superficial analysis in a trailing *-ing* clause | hard: comma + *highlighting, underscoring, ensuring, reflecting, contributing to, fostering, enhancing, showcasing, demonstrating…*; `jev:C3` |
| C4 | Promotional language | hard: *groundbreaking, renowned, cutting-edge, state-of-the-art, seamless, unprecedented, remarkable, vibrant…*; soft (C4s): *novel, innovative, powerful, comprehensive, holistic, rich*; `jev:C4` |
| C5 | Vague attribution | hard: *studies/researchers/experts/prior work show/suggest/argue…*, *it is widely known*, in a sentence with no citation; `jev:C5` |
| C6 | "Challenges and future prospects" formula | hard: *despite these challenges, faces challenges, holds promise, future outlook, remains to be seen, exciting*; `jev:C6` |
| C8 | Template "X and Y" headings | soft (LaTeX) |

## 2. Language and grammar
| ID | Sign | Check |
|---|---|---|
| L1 | AI vocabulary | hard: *additionally, align with, bolster, crucial, delve, emphasize, enduring, enhance, foster, garner, highlight, interplay, intricate, landscape, meticulous, pivotal, robust, showcase, tapestry, testament, underscore, valuable, vibrant, notably, furthermore, moreover, leverage, utilize, facilitate, multifaceted, nuanced, paramount, realm, streamline, empower, unlock, resonate with*; soft (L1s): *key* |
| L2 | Avoiding plain *is/are/has* | hard: *serves/stands/functions/acts/operates as a/an/the, features a, offers a, refers to* |
| L3 | Vague connection | soft: *associated with, in connection with, connected to* |
| L4 | Negative parallelism | soft, counted: *not only, not just, not merely, rather than, instead of, is not … but, it's not … it's*; a summary hit when above `negative_parallelism_max` (3); `jev:L4` |
| L5 | Rule of three | soft: every "A, B and C" sentence, and paragraphs with two or more; `jev:L5` |

## 3. Style
| ID | Sign | Check |
|---|---|---|
| S1 | Title case in headings | hard (LaTeX); acronyms and `proper_nouns` are allowed |
| S2 | Heading that holds only headings | hard (LaTeX) |
| S3 | Boldface in running text | hard (LaTeX), outside tables and `\paragraph` titles |
| S4 | Inline-header lists; one run-in title repeated 3+ times | hard / soft (LaTeX) |
| S5 | Em dashes | hard: any in the abstract (`em_dash_max_abstract` 0) or more than `em_dash_max_body` (3); soft: each one; spaced ` -- ` used as a dash |
| S6 | Tiny tables | soft (LaTeX): fewer than 3 body rows |
| S7 | Curly or straight quotes in LaTeX source | hard (LaTeX), code listings excepted |
| S8 | Skipped heading levels | hard (LaTeX) |
| S9 | `\emph` as decoration | soft (LaTeX): more than 1 per `emph_per_words` (250) |
| S10 | Explanatory colons | soft, **off by default** (one author's preference); enable by removing it from `disable` |

## 4. Communication meant for the user
| ID | Sign | Check |
|---|---|---|
| M1 | Chat residue | hard: *here is, I hope, let me know, certainly, as requested, as of my last update, knowledge cutoff, as an AI…* |
| M2 | Signposting as padding | soft: *in this section we discuss…* |
| M3 | Knowledge-gap disclaimers; hedges | hard: *not widely documented, based on available information*; soft (M3h): *may, might, could, likely, possibly, seems, appears to, suggests*, each needing a reason |
| M4 | Placeholders | hard: *TBD, TODO, XXX, [ref], ??, [citation needed]* in rendered text |
| M5 | Prose trapped in a comment | hard (LaTeX): comment lines over 100 characters |

## 5. Citations (LaTeX)
| ID | Sign | Check |
|---|---|---|
| R1 | Unusable references | hard: `\cite` key missing from the bib; soft: cited entry with no DOI or URL |
| R2 | Citation that doesn't support the sentence | manual, or `jev-fact-check` with facts from the cited paper |
| R3 | Citation stacks | soft: more than 4 keys in one `\cite`; review only, never delete a citation to satisfy it |
| R4 | Lost citations | hard, with `--baseline old.tex`: a key the baseline cites that the draft no longer cites. Record a deliberate removal as `% cite-removed: key (who, date: why)` |

## 6. Older signs and plain-language rules
| ID | Sign | Check |
|---|---|---|
| H1 | Didactic disclaimers | hard: *it is important to note, worth noting, importantly, interestingly, note that* |
| H2 | Section summaries | hard: *in summary, in conclusion, overall, taken together*; soft: a paragraph ending *This shows… / These results demonstrate…* |
| H3 | Elegant variation | from the config `glossary`: one term per concept |
| P1 | Stiff verbs | hard: *utilize, leverage, facilitate, endeavour, commence*; soft (P1s): *attempt* |
| P4 | Sentence length | soft: over `long_sentence_words` (40); paragraphs of 4+ sentences whose lengths hardly vary |
| A1–A3 | LLM markup artifacts, emoji, Markdown | hard, hard, soft |

## What human writing does (don't polish it away)
Plain *is/has/there is*; plain verbs (*used, tried, wrote*); definitive statements where the evidence is definitive;
hedges only where the evidence is uncertain; varied sentence length. Perfect grammar, formal register and transition
words on their own are **not** signs of AI writing.

## Config (`--config file.json`)
Every key is optional. See `config.example.json`.

| Key | Default | Meaning |
|---|---|---|
| `disable` | `["S10"]` | rule IDs to turn off |
| `em_dash_max_body`, `em_dash_max_abstract` | 3, 0 | S5 limits |
| `negative_parallelism_max` | 3 | L4 summary limit |
| `long_sentence_words` | 40 | P4 limit |
| `emph_per_words` | 250 | S9 density |
| `allow_vocabulary`, `extra_vocabulary` | `[]` | remove words from, or add words to, L1 |
| `proper_nouns` | `[]` | capitalised words allowed in headings |
| `glossary` | `[]` | H3 entries: `{"pattern", "advice", "level", "unless_before"}` |
| `specific_detail` | numbers, acronyms, number words, code-like tokens | R0.2: add the study's own terms |
