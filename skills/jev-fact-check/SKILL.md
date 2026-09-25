---
name: jev-fact-check
description: Check whether each sentence and paragraph of paper prose is backed by the underlying source material (code repo, result files, logs, configs, data, cited papers), using Jev (TypeSafe System One model) for claim support and code for every number. The agent first gathers relevant facts from the sources, then checks the prose against them. Use when verifying that a draft's claims, numbers, ranges and comparisons match the actual experiments, or when the user asks "does this paragraph hold up", "check the numbers", or "is this supported".
---

# jev-fact-check

`scripts/fact_check.py` sends one Jev request per paragraph. The request asks whether the paragraph as a whole is supported and, in parallel, whether each sentence is. A code pass then looks up every number in the sentence in the facts.

**The check is only as good as the facts.** Facts copied from the paper itself are circular: they catch internal inconsistencies, such as the abstract disagreeing with Table 1, but they can't show that a claim is true. Your job is to gather facts **from the source material** before running the check.

Needs a Jev API key. It is set when the plugin is installed, or by running `scripts/setup.py` at the plugin root. If a run fails for a missing key, ask the user to run that script in their own terminal, and never ask them to paste the key into the chat.

## Workflow
1. **Locate the sources.** Ask the user where they are if it isn't obvious. Typical sources:
   - **Code repo:** results and outputs folders, eval scripts, configs, logs, the README, notebooks.
   - **Data:** schema files (ontologies, SHACL shapes), dataset manifests.
   - **Cited papers:** for claims that carry a citation.
   - **The paper's own tables and figures:** for internal consistency only.
2. **Go through the paragraph claim by claim.** For each claim, find where the source establishes it, and write the fact from there. Examples:
   - "temperature 0.1" → the model config
   - "56 node shapes" → the shapes file
   - "0.839 macro F1" → the eval output
   - "Text2KGBench formalises … hallucination" → that paper's abstract
3. **Compute, don't eyeball.** Get counts, means, ranges and differences with code (`grep -c`, `python`, `jq`), and write each result as a fact. Jev cannot do arithmetic, so a derived number must already be in the facts.
4. **Write the facts.**
   - Write one atomic claim per fact, with exact numbers, in words close to the paper's.
   - Keep a side list mapping each fact to its source (`file:line`, a command, or a paper and section), so the report can cite it.
   - Give each paragraph only the facts relevant to it. About 20 facts per paragraph is enough; unrelated facts lower Jev's accuracy.
5. **When no source backs a claim, leave it out.** Don't write a fact from the paper's own sentence. Leaving it out means the check reports the claim as `unsupported`, which is the correct outcome.
6. **Write the input JSON:** `{"facts": [...], "paragraphs": ["text", {"text": "...", "facts": [...]}]}`
   - Strip LaTeX commands that carry no meaning. Keep `\cite{}` and `[n]` citation markers.
7. **Run:** `python3 ${CLAUDE_SKILL_DIR}/scripts/fact_check.py input.json`

## Reading the output
Per paragraph you get `support` and `confidence`. Per sentence you get `support`, `confidence`, `numbers` and `flags`:

| Flag | Meaning | What to do |
|---|---|---|
| `contradicted` | The prose conflicts with the source | Most serious; always report it, with the source location |
| `unsupported` / `partial` | Part of the claim isn't in the facts | Search the sources once more for it. If nothing backs it, report "no source found" |
| `uncertain` | Jev's confidence < 0.5 | Check it yourself against the source |
| `numbers_not_in_facts` | A number that no fact contains | Find it in the source or recompute it. If you can't, it's wrong or unsourced |
| `range_check` | A range like "55 to 59" whose endpoints come from one fact that also holds values outside the range | Often a real error. For example, if one system had 46, the range should read "46 to 59" |

**Never trust `supported` on a sentence with numbers without reading `numbers`.** Jev reads numbers as text and has passed wrong ranges as supported.

`not_in_facts` also catches incidental numbers such as section numbers, "two rounds" or model sizes. Ignore the ones that aren't factual claims.

**In the report**, cite the source location for each finding, e.g. `results/table1.csv:4 says C = 46`.
