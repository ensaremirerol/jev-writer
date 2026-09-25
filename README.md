# jev-writer

A Claude Code plugin with five skills for checking academic writing with
[Jev](https://docs.typesafe.ai/), TypeSafe's System One model, called through OpenRouter.

| Skill | Checks | Called on |
|---|---|---|
| `jev-fact-check` | whether each sentence and paragraph is backed by facts gathered from the source (repo, results, cited papers); numbers are also checked in code | paragraphs + facts |
| `jev-level` | whether each sentence fits a target reader | text |
| `jev-complexity` | how dense a sentence is (Jev score + Flesch-Kincaid) | one sentence |
| `jev-flow` | whether a sentence breaks the flow of its paragraph | one sentence + its span |
| `jev-ai-writing` | signs of AI writing ([Wikipedia list](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)), tuned for papers; on `.tex` also headings, quotes and citations, with line numbers | whole document (`.tex` or text) |

## Install

From a clone or local copy:
```bash
claude plugin marketplace add /path/to/jev-writer
claude plugin install jev-writer@jev-writer
```
From GitHub, once the repo is pushed:
```bash
claude plugin marketplace add <owner>/jev-writer
claude plugin install jev-writer@jev-writer
```
Inside a session, `/plugin` does the same interactively. The skills show up as
`jev-writer:jev-flow`, `jev-writer:jev-fact-check`, and so on, in every repository.

## API key

You need an [OpenRouter](https://openrouter.ai/) key, or a direct TypeSafe key. Keys never go in a repository.
Any of these works; the first one found wins:

1. `OPENROUTER_API_KEY` (or `TYPESAFE_API_KEY`) in your shell environment.
2. The key entered when the plugin is installed or enabled. It is stored by Claude Code as a sensitive value.
3. A `.env` in the current directory or any folder above it. Add it to that repo's `.gitignore`.
4. `~/.config/jev-writer/.env`, written by the setup script:
   ```bash
   python3 /path/to/jev-writer/scripts/setup.py
   ```
   The script asks for the key without echoing it, checks it with one tiny Jev request, and saves it with mode 600.

If a skill reports a missing key, run the setup script in your own terminal. Don't paste the key into the chat.

Optional: `JEV_MODEL` (default `jev-latest`) and `TYPESAFE_BASE_URL`.

## Develop

```bash
python3 tests/test_jev.py                       # offline tests, no key needed
claude --plugin-dir /path/to/jev-writer         # try local changes without reinstalling
claude plugin validate .                        # check the manifests
```
The scripts use only the Python 3.10+ standard library. Shared code lives in `lib/jev.py`.
