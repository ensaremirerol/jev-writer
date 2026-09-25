---
name: jev-complexity
description: Rate how complex a single sentence is to read (Jev score 0 plain to 3 very dense, plus word count and Flesch-Kincaid grade). Call it once per sentence. Use when checking whether a specific sentence in a paper draft is too dense, when choosing which long sentences to split, or when comparing a rewrite against the original.
---

# jev-complexity

`scripts/complexity.py` rates **one sentence per call**. The agent calls it sentence by sentence: pick candidates first, then check each one.

Needs a Jev API key. It is set when the plugin is installed, or by running `scripts/setup.py` at the plugin root. If a run fails for a missing key, ask the user to run that script in their own terminal, and never ask them to paste the key into the chat.

## Usage
```
python3 ${CLAUDE_SKILL_DIR}/scripts/complexity.py "The sentence to rate."
```
Use `-` to read the sentence from stdin, for sentences containing quotes.

## Workflow
1. **Pick candidates.** Long sentences (about 35 words or more), sentences stacked with clauses, or sentences the user points at.
2. **Run the script on each candidate.**
3. **For each sentence with `very_dense` (score ≥ 2.5)**, propose a split.
4. **Re-run on the rewrite** to confirm the score dropped.

## Reading the output
- **`score`:** 0–3, and can be fractional. `level` is the name of the nearest level.
- **`confidence`** is often low. Use `words` and `fk_grade`, which are computed locally, as the steadier signal.
- **Density isn't automatically wrong in a paper.** Judge it against the audience and against the sentences around it.
