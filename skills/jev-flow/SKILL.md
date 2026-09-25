---
name: jev-flow
description: Check whether a single sentence breaks the flow of the span (paragraph) it sits in, using Jev (TypeSafe System One model) with the previous and next sentences as context. Call it once per sentence. Use when a paragraph reads choppy, when a sentence may jump topic or lack a transition, or to verify that an inserted or rewritten sentence fits its surroundings.
---

# jev-flow

`scripts/flow.py` checks **one sentence against its span** per call. The agent calls it sentence by sentence.

Needs a Jev API key. It is set when the plugin is installed, or by running `scripts/setup.py` at the plugin root. If a run fails for a missing key, ask the user to run that script in their own terminal, and never ask them to paste the key into the chat.

## Usage
```
python3 ${CLAUDE_SKILL_DIR}/scripts/flow.py "The sentence to check." span.txt
```
- `span.txt` holds the paragraph containing the sentence. Pass `-` to read the span from stdin.
- The sentence must appear in the span. Copy it verbatim, or pass a distinctive substring of it.
- A span with only one sentence is rejected, because there is nothing to flow from.

## Workflow
1. **Pick sentences to check.** Good candidates are:
   - paragraph openers and closers;
   - sentences after a topic shift;
   - short standalone statements;
   - anything the user inserted or rewrote.
2. **Run the script on each one.**
3. **For `breaks_flow` (p ≥ 0.5)**, propose a fix:
   - a transition phrase;
   - moving the sentence to a different place;
   - or cutting it.
4. **Re-run on the edited span** to confirm the fix.

## Reading the output
- **`p_breaks_flow`** is the main signal. The output also echoes `previous_sentence` and `next_sentence` so you can see the context Jev judged.
- **Values around 0.5–0.6 are borderline.** Read the three sentences yourself before rewriting.
