"""Compare the pre-Milestone-1 retrieval (baseline) with the current engine on `dataset.json`.

Baseline = frozen BM25 + section boost, old chunk file, old rule "answer if top score >= 0.35".
Improved = the production TutorService (hybrid ranking, confidence tiers) over the current chunk file.
Both see the same extra fixture course, so course isolation is measured the same way.

Usage: python -m evaluation.run   (writes evaluation/REPORT.md)
"""

import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from assistant.config import DATA_DIR
from assistant.domain.models import ChatRequest, ChatStatus
from assistant.infrastructure.chunk_store import ChunkStore
from assistant.infrastructure.providers.faq import OfflineFAQProvider
from assistant.ingest.parsers import parse_markdown
from assistant.services.tutor import TutorService
from evaluation.baseline_retrieval import BaselineBM25

EVAL_DIR = Path(__file__).resolve().parent
DATASET_PATH = EVAL_DIR / "dataset.json"
BASELINE_CHUNKS = EVAL_DIR / "baseline_chunks.json"
REPORT_PATH = EVAL_DIR / "REPORT.md"
TOP_K = 3

DECISIONS = {ChatStatus.ANSWERED: "answer", ChatStatus.NEEDS_CLARIFICATION: "clarify",
             ChatStatus.NOT_FOUND: "not_found", ChatStatus.NEEDS_HUMAN: "not_found"}


@dataclass
class Outcome:
    ranking: List[str]
    scores: List[float]
    decision: str
    violations: int = 0


@dataclass
class SystemResult:
    name: str
    outcomes: Dict[str, Outcome] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)


def load_dataset() -> Dict[str, Any]:
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))


def fixture_chunks(dataset: Dict[str, Any]) -> List[Dict[str, Any]]:
    chunks = []
    for scope, course in dataset["courses"].items():
        for lesson in course.get("lessons", []):
            content = (EVAL_DIR / lesson["file"]).read_text(encoding="utf-8")
            chunks += parse_markdown(content, scope, course["title"], lesson["url"],
                                     lesson["lesson_id"], lesson["lesson_title"])
    return chunks


def _violations(chunks: List[Dict[str, Any]], item: Dict[str, Any]) -> int:
    lesson = item.get("lesson")
    return sum(1 for c in chunks if c.get("scope") != item["scope"] or (lesson and c.get("lesson_id") != lesson))


def run_baseline(dataset: Dict[str, Any]) -> SystemResult:
    legacy = json.loads(BASELINE_CHUNKS.read_text(encoding="utf-8"))
    index = BaselineBM25(legacy + fixture_chunks(dataset))
    result = SystemResult("baseline")
    for item in dataset["items"]:
        ranked = index.search(item["query"], TOP_K, item["scope"])
        decision, _ = index.decide(item["query"], item["scope"])
        chunks = [c for c, _ in ranked]
        result.outcomes[item["id"]] = Outcome([c["section"] for c in chunks], [round(s, 3) for _, s in ranked],
                                              decision, _violations(chunks, item))
    return result


def run_improved(dataset: Dict[str, Any], chunks_path: Optional[Path] = None) -> SystemResult:
    source = ChunkStore(chunks_path or DATA_DIR / "chunks.json").load()
    with tempfile.TemporaryDirectory() as tmp:
        store = ChunkStore(Path(tmp) / "chunks.json")
        store.save(source + fixture_chunks(dataset))
        tutor = TutorService(store, OfflineFAQProvider())
        result = SystemResult("improved")
        for item in dataset["items"]:
            retrieved = tutor.index.retrieve(item["query"], TOP_K, item["scope"], item.get("lesson"))
            response = tutor.answer(ChatRequest(message=item["query"], scope=item["scope"], lesson=item.get("lesson")))
            passages = retrieved.passages
            result.outcomes[item["id"]] = Outcome(
                [p.section for p in passages], [p.confidence for p in passages], DECISIONS[response.status],
                _violations([{"scope": p.scope, "lesson_id": p.lesson_id} for p in passages], item),
            )
    return result


def score(result: SystemResult, items: List[Dict[str, Any]]) -> SystemResult:
    ranked_items = [i for i in items if i["expected_section"]]
    must_not_answer = [i for i in items if "answer" not in i["accept"]]
    top1 = recall = mrr = 0.0
    for item in ranked_items:
        ranking = result.outcomes[item["id"]].ranking
        if ranking[:1] == [item["expected_section"]]:
            top1 += 1
        if item["expected_section"] in ranking:
            recall += 1
            mrr += 1 / (ranking.index(item["expected_section"]) + 1)
    decisions = sum(result.outcomes[i["id"]].decision in i["accept"] for i in items)
    false_answers = sum(result.outcomes[i["id"]].decision == "answer" for i in must_not_answer)
    wrong_section_answers = sum(
        1 for i in ranked_items
        if result.outcomes[i["id"]].decision == "answer" and result.outcomes[i["id"]].ranking[:1] != [i["expected_section"]]
    )
    n = len(ranked_items) or 1
    result.metrics = {
        "top1_accuracy": round(top1 / n, 3),
        "recall_at_3": round(recall / n, 3),
        "mrr": round(mrr / n, 3),
        "decision_accuracy": round(decisions / len(items), 3),
        "false_answer_rate": round(false_answers / (len(must_not_answer) or 1), 3),
        "wrong_section_answers": wrong_section_answers,
        "isolation_violations": sum(o.violations for o in result.outcomes.values()),
    }
    return result


def evaluate(chunks_path: Optional[Path] = None) -> Dict[str, Any]:
    dataset = load_dataset()
    items = dataset["items"]
    return {
        "items": items,
        "baseline": score(run_baseline(dataset), items),
        "improved": score(run_improved(dataset, chunks_path), items),
    }


METRIC_LABELS = [
    ("top1_accuracy", "Top-1 accuracy (expected section ranked first)", True),
    ("recall_at_3", "Recall@3 (expected section in top 3)", True),
    ("mrr", "Mean reciprocal rank", True),
    ("decision_accuracy", "Decision accuracy (answer / clarify / not_found)", True),
    ("false_answer_rate", "False-answer rate on questions that must not be answered", False),
    ("wrong_section_answers", "Answers given from the wrong section", False),
    ("isolation_violations", "Passages returned from another course/lesson", False),
]


def _cell(outcome: Outcome) -> str:
    if not outcome.ranking:
        return "(nothing)"
    return f"{outcome.ranking[0]} ({outcome.scores[0]})"


def render_report(results: Dict[str, Any]) -> str:
    base, new, items = results["baseline"], results["improved"], results["items"]
    lines = [
        "# Retrieval evaluation: previous vs improved ranking",
        "",
        "Generated by `python -m evaluation.run` from `evaluation/dataset.json` "
        f"({len(items)} questions: English, concept-specific, synonyms, Amharic, out-of-scope, "
        "course/lesson isolation, ambiguous). A second fixture course (PY-101, two lessons) is indexed "
        "next to VA-1 in both systems.",
        "",
        "- **Previous**: BM25 + section-title boost, old `chunks.json`, rule *answer if top BM25 score >= 0.35*. "
        "Scores in the table are raw BM25.",
        "- **Improved**: BM25 + coverage + title + keyword/synonym + phrase signals, course/lesson filters before "
        "ranking, Ethiopic-safe normalization and light stemming, confidence tiers (answer >= 0.6, "
        "clarify 0.35-0.6 after widening, not_found < 0.35). Scores in the table are confidence (0-1).",
        "",
        "## Summary",
        "",
        "| Metric | Previous | Improved | Better is |",
        "|---|---|---|---|",
    ]
    for key, label, higher in METRIC_LABELS:
        lines.append(f"| {label} | {base.metrics[key]} | {new.metrics[key]} | {'higher' if higher else 'lower'} |")

    lines += [
        "",
        "Limitations: the dataset is small and the stop words, synonyms and Amharic translations were tuned "
        "while looking at it, so treat the improved numbers as an upper bound. Add new learner questions "
        "(for example the `not_found` list in the analytics dashboard) before trusting them on new content.",
    ]
    categories = list(dict.fromkeys(i["category"] for i in items))
    lines += ["", "## Decision accuracy by category (decision only; wrong-section answers are counted above)", "",
              "| Category | Questions | Previous | Improved |",
              "|---|---|---|---|"]
    for category in categories:
        group = [i for i in items if i["category"] == category]
        b = sum(base.outcomes[i["id"]].decision in i["accept"] for i in group)
        n = sum(new.outcomes[i["id"]].decision in i["accept"] for i in group)
        lines.append(f"| {category} | {len(group)} | {b}/{len(group)} | {n}/{len(group)} |")

    lines += ["", "## Per-question ranking", "",
              "| ID | Question | Expected | Previous top-1 (score) → decision | Improved top-1 (confidence) → decision |",
              "|---|---|---|---|---|"]
    for item in items:
        b, n = base.outcomes[item["id"]], new.outcomes[item["id"]]
        mark = lambda o: "ok" if o.decision in item["accept"] and (
            not item["expected_section"] or o.decision != "answer" or o.ranking[:1] == [item["expected_section"]]
        ) else "**wrong**"
        scope = item["scope"] + (f" / lesson {item['lesson']}" if item.get("lesson") else "")
        lines.append(
            f"| {item['id']} | {item['query']} <br><sub>{scope}</sub> | {item['expected_section'] or '— (must not answer)'} "
            f"| {_cell(b)} → {b.decision} ({mark(b)}) | {_cell(n)} → {n.decision} ({mark(n)}) |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    results = evaluate()
    REPORT_PATH.write_text(render_report(results), encoding="utf-8")
    for key, label, _ in METRIC_LABELS:
        print(f"{label:62} previous={results['baseline'].metrics[key]!s:6} improved={results['improved'].metrics[key]}")
    print(f"Report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
