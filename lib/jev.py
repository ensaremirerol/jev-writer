"""Shared helpers for the jev-* skills: .env loading, Jev (TypeSafe System One) calls, text splitting.

Scripts import this with: sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
"""
import json, os, re, sys, time, urllib.error, urllib.request
from pathlib import Path

ABBR = re.compile(r"\b(?:e\.g|i\.e|et al|etc|vs|cf|approx|resp|Fig|Figs|Eq|Eqs|Sec|Tab|Ref|Refs|No|Dr|Prof)\.$")


def split_sentences(text):
    parts = re.split(r"(?<=[.!?])\s+(?=[\"“(\[]?[A-Za-z0-9\\])", " ".join(text.split()))
    out = []
    for p in parts:
        if out and ABBR.search(out[-1]):
            out[-1] += " " + p
        else:
            out.append(p)
    return [s for s in out if s]


def split_paragraphs(text):
    return [p for p in re.split(r"\n\s*\n", text) if p.strip()]


def read_text(arg):
    return sys.stdin.read() if arg in (None, "-") else Path(arg).read_text()


def emit(obj):
    json.dump(obj, sys.stdout, indent=1, ensure_ascii=False)
    print()


def noul(question, true, false, **extra):
    return {"type": "noul", "instructions": {"question": question, **extra}, "criteria": {"true": true, "false": false}}


# Written by scripts/setup.py; lives outside every repo so keys never get committed.
USER_ENV = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "jev-writer" / ".env"
SETUP = Path(__file__).resolve().parents[1] / "scripts" / "setup.py"


def read_env_file(path):
    for line in path.read_text().splitlines():
        k, sep, v = line.strip().partition("=")
        if sep and not k.startswith("#"):
            os.environ.setdefault(k.strip().removeprefix("export "), v.strip().strip("'\""))


def load_keys():
    """First found wins: environment > plugin install prompt > nearest .env from cwd up > USER_ENV."""
    for k, v in list(os.environ.items()):
        if k.upper() == "CLAUDE_PLUGIN_OPTION_OPENROUTER_API_KEY" and v:
            os.environ.setdefault("OPENROUTER_API_KEY", v)
    for d in [Path.cwd(), *Path.cwd().parents]:
        if (d / ".env").is_file():
            read_env_file(d / ".env")
            break
    if USER_ENV.is_file():
        read_env_file(USER_ENV)


def ask(state, questions):
    """One Jev request; returns the `answers` dict (plus `_usage`)."""
    load_keys()
    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("TYPESAFE_API_KEY")
    if not key:
        sys.exit(f"error: no Jev API key. Run `python3 {SETUP}` in your own terminal, "
                 "or set OPENROUTER_API_KEY (or TYPESAFE_API_KEY).")
    base = os.environ.get("TYPESAFE_BASE_URL") or ("https://openrouter.ai/api" if os.environ.get("OPENROUTER_API_KEY") else "https://api.typesafe.ai")
    body = json.dumps({"model": os.environ.get("JEV_MODEL", "jev-latest"), "state": state, "questions": questions}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/v1/systemone", body, {"Authorization": f"Bearer {key.strip()}", "Content-Type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                resp = json.load(r)
                return {**resp["answers"], "_usage": resp.get("usage")}
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 529) and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            sys.exit(f"error: Jev HTTP {e.code}: {e.read().decode(errors='replace')[:500]}")


def r2(x):
    return round(x, 2)
