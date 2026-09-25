#!/usr/bin/env python3
"""One-time key setup for the jev-writer skills. Run it in your own terminal:

    python3 scripts/setup.py

Prompts for the key without echoing it, checks it with one tiny Jev request, and saves it to
~/.config/jev-writer/.env (mode 600), where every jev-* skill finds it from any repo.
"""
import getpass, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import jev


def main():
    print("Jev key setup. OpenRouter keys start with 'sk-or-'; a direct TypeSafe key also works.")
    key = getpass.getpass("API key (input hidden): ").strip()
    if not key:
        sys.exit("no key entered; nothing saved")
    name = "OPENROUTER_API_KEY" if key.startswith("sk-or-") else "TYPESAFE_API_KEY"

    # Check the key before saving it; this one question costs a fraction of a cent.
    for k in ("OPENROUTER_API_KEY", "TYPESAFE_API_KEY", "TYPESAFE_BASE_URL"):
        os.environ.pop(k, None)
    os.environ[name] = key
    jev.ask("The sky is blue.", {"t": jev.noul("Does the text describe a colour?", "Yes.", "No.")})

    jev.USER_ENV.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(jev.USER_ENV, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(f"{name}={key}\n")
    os.chmod(jev.USER_ENV, 0o600)
    print(f"key works; saved {name} to {jev.USER_ENV}")


if __name__ == "__main__":
    main()
