"""Runs evaluation/dataset.json against the bundled knowledge base and guards against regressions."""

import pytest

from evaluation.run import evaluate


@pytest.fixture(scope="module")
def results(container):
    return evaluate(container.settings.chunks_path)


def test_improved_ranking_is_never_worse_than_the_previous_engine(results):
    base, new = results["baseline"].metrics, results["improved"].metrics
    for metric in ("top1_accuracy", "recall_at_3", "mrr", "decision_accuracy"):
        assert new[metric] >= base[metric], metric
    assert new["false_answer_rate"] <= base["false_answer_rate"]


def test_quality_thresholds(results):
    metrics = results["improved"].metrics
    assert metrics["top1_accuracy"] >= 0.9
    assert metrics["recall_at_3"] >= 0.95
    assert metrics["decision_accuracy"] >= 0.9
    assert metrics["false_answer_rate"] == 0
    assert metrics["wrong_section_answers"] == 0


def test_no_content_leaks_across_courses_or_lessons(results):
    assert results["improved"].metrics["isolation_violations"] == 0
