"""Regression: no hand-set per-enzyme score overrides remain in the scoring path (Step 0.3).

The prior pipeline injected per-enzyme axis values (e.g. for ISCro4) to make gates pass. v3.0 forbids
any enzyme-conditioned score override: the scoring modules must be enzyme-agnostic. The scan strips
comments AND string literals first, so docstrings that *describe* the old bug do not trip the check —
only executable code is inspected.
"""
import re
import tokenize
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "pen_stack"
SCORING_PATH_FILES = [SRC / "score" / "recalibrate.py", SRC / "atlas" / "universe.py"]
ENZYME_LITERALS = re.compile(r"\b(ISCro4|IS621|SpCas9|AsCas12a|Bxb1|evoCAST)\b")
OVERRIDE_LITERAL = re.compile(r"\b(S_Prog|S_Cargo|s_prog|s_cargo)\s*=\s*1\.0\b")


def _code_only(path: Path) -> str:
    """Return source with comments and string literals removed (executable tokens only)."""
    out = []
    with open(path, "rb") as fh:
        for tok in tokenize.tokenize(fh.readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING, tokenize.ENCODING):
                continue
            out.append(tok.string)
    return " ".join(out)


def test_scoring_modules_are_enzyme_agnostic():
    for f in SCORING_PATH_FILES:
        assert not ENZYME_LITERALS.search(_code_only(f)), f"enzyme name hard-coded in scoring path: {f.name}"


def test_no_constant_axis_override():
    for f in SCORING_PATH_FILES:
        assert not OVERRIDE_LITERAL.search(_code_only(f)), f"hand-set axis=1.0 override in {f.name}"


def test_prereg_does_not_name_an_enzyme_in_predictions():
    prereg = (SRC.parent / "prereg" / "phase0.yaml").read_text(encoding="utf-8")
    assert "scorecard_no_named_enzyme: true" in prereg
