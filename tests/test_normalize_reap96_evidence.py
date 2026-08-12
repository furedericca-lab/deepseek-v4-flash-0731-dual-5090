import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "normalize_reap96_evidence.py"
SPEC = importlib.util.spec_from_file_location("normalize_reap96_evidence", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_blivion_normalizer_sorts_original_ids(tmp_path):
    source = tmp_path / "saliency.json"
    source.write_text(json.dumps({str(layer): {"kept_expert_ids": list(range(191, -1, -1))} for layer in range(43)}))
    payload = MODULE.normalize_blivion_k192(source, "a" * 40)
    assert payload["layers"]["0"]["kept_experts"] == list(range(192))


def test_heath_normalizer_preserves_complete_semantic_ranking(tmp_path):
    source = tmp_path / "k216.json"
    source.write_text(json.dumps({"keep_maps": {
        "keep_by_layer": {str(layer): list(range(216)) for layer in range(43)},
        "ranked_by_layer": {str(layer): list(range(255, -1, -1)) for layer in range(43)},
    }}))
    payload = MODULE.normalize_heath_k216(source, "a" * 40)
    assert payload["layers"]["0"]["ranked_experts"] == list(range(255, -1, -1))


def test_true2456_normalizer_excludes_hash_layers(tmp_path):
    source = tmp_path / "reap-plan.json"
    source.write_text(json.dumps({"layers": {str(layer): {"keep": list(range(163))} for layer in range(43)}}))
    payload = MODULE.normalize_true2456_k163(source, "a" * 40)
    assert set(payload["layers"]) == {str(layer) for layer in range(3, 43)}


def test_native_exact_normalizer_preserves_recovered_original_ids(tmp_path):
    source = tmp_path / "k160-exact.json"
    source.write_text(json.dumps({
        "kept_num_routed_experts": 2,
        "base_revision_sha": "a" * 40,
        "pruned_revision_sha": "b" * 40,
        "pruned_repo": "0xSero/example",
        "logical_sha256": "c" * 64,
        "layers": {str(layer): {"kept_experts": [1, 0]} for layer in range(43)},
    }))
    payload = MODULE.normalize_native_exact(source, "b" * 40)
    assert payload["declared_k"] == 2
    assert payload["layers"]["0"]["kept_experts"] == [0, 1]
    assert payload["base_revision_sha"] == "a" * 40


def test_reap25_normalizer_excludes_unpruned_hash_layers(tmp_path):
    source = tmp_path / "keep_map_bexact.json"
    source.write_text(json.dumps({
        "n_experts": 256,
        "kept_per_scored_layer": 192,
        "scored_layers": [3, 42],
        "hash_layers_keep": 256,
        "keep_map": {str(layer): list(range(256 if layer < 3 else 192)) for layer in range(43)},
    }))
    payload = MODULE.normalize_reap25_k192(source, "a" * 40)
    assert set(payload["layers"]) == {str(layer) for layer in range(3, 43)}
    assert payload["layers"]["3"]["kept_experts"] == list(range(192))
