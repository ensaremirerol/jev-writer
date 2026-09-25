"""Offline self-check for the jev-* skills: python3 tests/test_jev.py"""
import importlib.util, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SK = ROOT / "skills"
sys.path.insert(0, str(ROOT / "lib"))


def load(skill, name):
    spec = importlib.util.spec_from_file_location(name, SK / skill / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


from jev import split_paragraphs, split_sentences

fc = load("jev-fact-check", "fact_check")
cx = load("jev-complexity", "complexity")
fl = load("jev-flow", "flow")
ai = load("jev-ai-writing", "ai_writing")

assert split_sentences("It was mistyped. pySHACL runs, e.g. on shapes.") == ["It was mistyped.", "pySHACL runs, e.g. on shapes."]
s = split_sentences("We follow Smith et al. (2020) here. Results in Fig. 3 show a 3.5% gain, e.g. on MNLI. Next we ablate.")
assert s == ["We follow Smith et al. (2020) here.", "Results in Fig. 3 show a 3.5% gain, e.g. on MNLI.", "Next we ablate."], s
assert len(split_paragraphs("a\n\n  \nb\nc")) == 2

# fact-check numbers: the real bug from the SWAT4HCLS draft ("55 to 59" when C had 46).
fact = "Graphs with an undeclared term: proposed 0 of 200, A 59 of 200, B 55 of 200, C 46 of 200."
n = fc.number_check("single-pass systems do so in 55 to 59 of theirs [5].", [fact])
assert n["not_in_facts"] == [] and n["ranges"][0]["fact_values_outside"] == [0, 46, 200], n
assert "ranges" not in fc.number_check("raises it from 44/200 to 174/200.", ["A 44 of 200, B 174 of 200, C 41 of 200."])
assert fc.number_check("Of 12 546 typed individuals, 4 377 are measurements (Q1 384, Q3 1 265).", ["12,546 individuals; 4377 measurements; Q1 384, Q3 1265."])["not_in_facts"] == []
assert "ranges" not in fc.number_check("Body Height (LOINC: 8302-2)", ["LOINC 8302-2 is body height; 2 codes"])
assert fc.number_check("F1 rose to 0.84 in Q1.", ["F1 was 0.839."])["not_in_facts"] == [0.84]
assert fc.number_check("changes F1 by −0.004.", ["F1 drops by 0.004."])["not_in_facts"] == []

assert cx.metrics("The cat sat.")["words"] == 3
assert cx.metrics("Hierarchical representations facilitate compositional generalization.")["fk_grade"] > 15

sents, i = fl.locate("Second  one.", "First one. Second one. Third one.")
assert i == 1 and sents[2] == "Third one."

cfg = dict(ai.DEFAULTS, proper_nouns=set())
rules = ai.build_rules(cfg)

def rids(text, exempt=(), backmatter=False):
    hits, _, _ = ai.audit_paragraph(0, [(None, text, set(exempt), backmatter, False)], cfg, rules, True)
    return {h["rule"] for h in hits}

assert {"C1", "C3", "L1", "L2"} <= rids("This work stands as a testament to our meticulous approach, highlighting its value.")
assert rids("We keep the union rather than the merge.") == {"L4"}
assert rids("We train for 10 epochs with a key-value cache.") == set()
assert "A1" in rids("as shown :contentReference[oaicite:0]")
assert "C5" in rids("Studies show that decomposition improves recall.")
assert "C5" not in rids("Studies show that decomposition improves recall [3].")
assert "C5" not in rids("Studies show that decomposition improves recall 〔CITE〕.")
assert rids("Additionally, I hope this helps.", backmatter=True) == {"M1"}   # back matter: chat residue only
assert "L1" not in rids("Additionally, recall rose to 0.9.", exempt={"L1"})  # % style-ok: L1

# LaTeX mode: structure, quotes, citations, line numbers
import tempfile
with tempfile.TemporaryDirectory() as tmp:
    tex = Path(tmp) / "p.tex"
    tex.write_text("\n".join([
        r"\begin{document}",
        r"\begin{abstract}We parse --- then merge.\end{abstract}",
        r"\maketitle",
        r"\section{Related Work}",
        r"\subsection{Extraction}",
        r"Prior extraction is \textbf{slow} \cite{known,missing}.",
        r"\begin{lstlisting}",
        r'ex:n1 "Body temperature"',
        r"\end{lstlisting}",
        r"\end{document}"]))
    (Path(tmp) / "refs.bib").write_text("@article{known,\n  title = {T},\n  year = {2020}\n}\n")
    _, lhits, _ = ai.latex.parse(tex, dict(cfg, bib=None, baseline=None))
    got = {(h["rule"], h["level"], h["line"]) for h in lhits}
    assert ("S5", "hard", 2) in got and ("S1", "hard", 4) in got and ("S2", "hard", 4) in got, got
    assert ("S3", "hard", 6) in got and ("R1", "hard", 6) in got and ("R1", "soft", 6) in got, got
    assert not any(h["rule"] == "S7" for h in lhits), "quotes inside lstlisting are code"
print("ok")

# key lookup order: environment > plugin install prompt > nearest .env from cwd up > ~/.config/jev-writer/.env
import os, tempfile
import jev

def keys_from(env, cwd_env=None, user_env=None):
    saved, here = dict(os.environ), os.getcwd()
    try:
        os.environ.clear(); os.environ.update(env)
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "repo" / "sub"; proj.mkdir(parents=True)
            if cwd_env:
                (Path(tmp) / "repo" / ".env").write_text(cwd_env)
            jev.USER_ENV = Path(tmp) / "cfg" / ".env"
            if user_env:
                jev.USER_ENV.parent.mkdir(); jev.USER_ENV.write_text(user_env)
            os.chdir(proj)
            jev.load_keys()
            return os.environ.get("OPENROUTER_API_KEY")
    finally:
        os.chdir(here); os.environ.clear(); os.environ.update(saved)

assert keys_from({}, user_env="OPENROUTER_API_KEY=user") == "user"
assert keys_from({}, cwd_env="OPENROUTER_API_KEY=repo", user_env="OPENROUTER_API_KEY=user") == "repo"
assert keys_from({"CLAUDE_PLUGIN_OPTION_openrouter_api_key": "plugin"}, cwd_env="OPENROUTER_API_KEY=repo") == "plugin"
assert keys_from({"OPENROUTER_API_KEY": "env", "CLAUDE_PLUGIN_OPTION_OPENROUTER_API_KEY": "plugin"}) == "env"
assert keys_from({}) is None
print("keys ok")
