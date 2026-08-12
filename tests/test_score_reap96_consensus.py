import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "score_reap96_consensus.py"
SPEC = importlib.util.spec_from_file_location("score_reap96_consensus", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def mask(kept, *, layer="0"):
    return {"layers": {layer: {"kept_experts": kept}}}


def ranked_mask(kept, ranking=None, *, layer="0"):
    return {"layers": {layer: {
        "kept_experts": kept,
        "ranked_experts": list(range(256)) if ranking is None else ranking,
    }}}


def test_strong_0xsero_tier_outranks_independent_votes():
    universe = list(range(132))
    masks = {
        "0xsero-k160": mask([0]),
        "heath0xff-k216": ranked_mask([0, 1]),
        "blivion-k192": mask([1]),
        "reap25-k192": mask([1]),
        "true2456-k163": mask([1]),
        "puwaer-k178": mask(universe),
    }
    result = MODULE.score_layer(universe, "0", masks)
    ranked = result["ranked_experts"]
    assert ranked[0]["expert_id"] == 1
    assert ranked[0]["score"] == 4
    assert ranked[1]["expert_id"] == 0
    assert ranked[1]["score"] == 2
    assert len(result["selected_experts"]) == 96


def test_tie_break_is_stable_then_original_id():
    universe = list(range(132))
    masks = {
        "0xsero-k160": mask([]),
        "heath0xff-k216": ranked_mask([]),
        "blivion-k192": mask([]),
        "reap25-k192": mask([]),
        "true2456-k163": mask([]),
        "puwaer-k178": mask(universe),
    }
    result = MODULE.score_layer(universe, "0", masks)
    assert result["selected_experts"] == list(range(96))
    assert result["boundary"]["tie_crosses_boundary"] is True


def test_rejects_failed_puwaer_nesting():
    universe = list(range(132))
    masks = {
        "0xsero-k160": mask([]), "heath0xff-k216": ranked_mask([]),
        "blivion-k192": mask([]), "reap25-k192": mask([]),
        "true2456-k163": mask([]), "puwaer-k178": mask(universe[:-1]),
    }
    try:
        MODULE.score_layer(universe, "0", masks)
    except ValueError as error:
        assert "K132 is not a K178 subset" in str(error)
    else:
        raise AssertionError("expected nesting failure")


def test_k216_semantic_rank_resolves_identical_evidence_vectors():
    universe = list(range(132))
    ranking = [100, 99] + [expert for expert in range(256) if expert not in {99, 100}]
    masks = {
        "0xsero-k160": mask([]), "heath0xff-k216": ranked_mask([], ranking),
        "blivion-k192": mask([]), "reap25-k192": mask([]),
        "true2456-k163": mask([]), "puwaer-k178": mask(universe),
    }
    result = MODULE.score_layer(universe, "0", masks)
    assert result["ranked_experts"][0]["expert_id"] == 100
    assert result["ranked_experts"][1]["expert_id"] == 99
