---
name: jev-level
description: Check whether each sentence of a text fits a requested writing level or target reader (e.g. "NeurIPS reviewers", "clinicians without ML background") using Jev (TypeSafe System One model). Use when the user asks whether a paper, abstract or section is pitched right for its audience, too technical, too simple, or assumes too much background.
---

# jev-level

`scripts/level.py` checks every sentence against a target reader. Paragraphs are split on blank lines, and each paragraph is one Jev request.

Needs a Jev API key. It is set when the plugin is installed, or by running `scripts/setup.py` at the plugin root. If a run fails for a missing key, ask the user to run that script in their own terminal, and never ask them to paste the key into the chat.

## Usage
```
python3 ${CLAUDE_SKILL_DIR}/scripts/level.py --level "SWAT4HCLS reviewers: semantic web and health informatics researchers" text.txt
```
- Describe the reader concretely: their field, what they already know, and what they don't.
- The input is plain text, with paragraphs separated by blank lines. Convert PDF or LaTeX to text first, e.g. with `pdftotext`.

## Reading the output
- Each sentence gets `p_on_level`, and `off_level` is true when it is below 0.5.
- The signal is soft. Scores often sit between 0.6 and 0.9 even for good prose.
- Rank the sentences by `p_on_level` and look at the bottom few rather than trusting the 0.5 cut-off.
- When you report a sentence, say whether it is too technical or too simple. Jev doesn't say which.
