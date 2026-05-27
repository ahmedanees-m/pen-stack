"""CI-runnable version of Step 3 cross-package smoke test.

These tests are skipped if upstream packages are not installed at v3-compat versions.
Run in the Docker container where all 4 packages are guaranteed to be present.
"""

import warnings

import pytest
from packaging.version import Version


def _compat(installed: str, min_v: str, max_v: str) -> bool:
    """Version range check that handles setuptools-scm dev versions."""
    return Version(installed) >= Version(min_v) and Version(installed) < Version(max_v)


# Gracefully skip all tests if upstream packages are not installed
ga = pytest.importorskip("genome_atlas", reason="genome-atlas not installed")
mc = pytest.importorskip("mech_class", reason="mech-class not installed")
ps = pytest.importorskip("pen_score", reason="pen-score not installed")
pa = pytest.importorskip("pen_assemble", reason="pen-assemble not installed")


class TestGenomeAtlasV372:
    def test_version(self):
        assert _compat(ga.__version__, "0.7.2", "0.8.0"), ga.__version__

    def test_iscro4_canonical(self):
        systems = ga.load_systems()
        assert "ISCro4" in systems

    def test_iscro4_uniprot(self):
        systems = ga.load_systems()
        iscro4 = systems["ISCro4"]
        uniprot = getattr(iscro4, "uniprot", None)
        if uniprot is None:
            proteins = getattr(iscro4, "proteins", None) or []
            uniprot = proteins[0] if proteins else None
        assert uniprot == "D2TGM5"

    def test_iscro4_pfam(self):
        systems = ga.load_systems()
        pfam = systems["ISCro4"].pfam
        assert "PF01548" in pfam and "PF02371" in pfam


class TestMechClassV054:
    def test_version(self):
        assert _compat(mc.__version__, "0.5.4", "0.6.0"), mc.__version__

    def test_pfam_whitelist_has_is110_entries(self):
        from mech_class.api import PFAM_WHITELIST  # type: ignore

        assert "PF01548" in PFAM_WHITELIST, "PF01548 (IS110 serine recombinase) missing"
        assert "PF02371" in PFAM_WHITELIST, "PF02371 (IS110 HTH) missing"

    def test_predictor_api_surface(self):
        """Verify Predictor class has required API methods (models need Zenodo deposit)."""
        from mech_class.api import Prediction, Predictor  # type: ignore

        assert callable(getattr(Predictor, "load", None))
        assert callable(getattr(Predictor, "predict_from_sequence", None))
        pred_fields = set(Prediction.model_fields.keys())
        assert "tier_a" in pred_fields
        assert "tier_a_confidence" in pred_fields
        assert "pfam_hits" in pred_fields

    def test_predictor_load_raises_file_not_found_for_missing_models(self):
        from mech_class.api import Predictor  # type: ignore

        with pytest.raises(FileNotFoundError):
            Predictor.load(model_dir="/nonexistent/path", download=False)


class TestPenScoreV013:
    def test_version(self):
        assert _compat(ps.__version__, "0.1.3", "0.2.0"), ps.__version__

    def test_get_editor_metadata_callable(self):
        from pen_score import get_editor_metadata  # type: ignore

        assert callable(get_editor_metadata)

    def test_scorer_instantiates(self):
        from pen_score import Scorer  # type: ignore

        sc = Scorer()
        assert sc is not None

    def test_iscro4_metadata(self):
        from pen_score import get_editor_metadata  # type: ignore

        md = get_editor_metadata("ISCro4")
        assert md.intrinsic_cargo_mechanism is True
        assert md.cell_based_evidence is True
        assert md.canonical_name == "ISCro4"

    def test_is621_cell_based_false(self):
        """The v3.2 keystone: IS621 must have cell_based_evidence=False."""
        from pen_score import get_editor_metadata  # type: ignore

        md = get_editor_metadata("IS621")
        assert md.intrinsic_cargo_mechanism is True
        assert md.cell_based_evidence is False, (
            "IS621 must be False to distinguish it from ISCro4 (TRUE_WRITER vs PROBABLE_WRITER)"
        )

    def test_spcas9_intrinsic_false(self):
        from pen_score import get_editor_metadata  # type: ignore

        md = get_editor_metadata("SpCas9")
        assert md.intrinsic_cargo_mechanism is False

    def test_is622_alias_deprecated(self):
        from pen_score import get_editor_metadata  # type: ignore

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            md = get_editor_metadata("IS622")
        assert md.canonical_name == "ISCro4"
        assert any("deprecated" in str(warning.message).lower() for warning in w)

    def test_iscro4_scorer_pen_score(self):
        """ISCro4 (D2TGM5) PenScore > 0.85 via Scorer.score_editor(accession)."""
        from pen_score import Scorer  # type: ignore

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = Scorer().score_editor("D2TGM5")
        assert result.pen_score is not None and result.pen_score > 0.85, result.pen_score
        # S_Cargo should be computable without mech-class models
        assert result.axes.S_Cargo is not None and result.axes.S_Cargo > 0.9


class TestPenAssembleV052:
    def test_version(self):
        assert _compat(pa.__version__, "0.5.2", "0.6.0"), pa.__version__
