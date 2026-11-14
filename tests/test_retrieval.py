"""Text analysis, hybrid ranking, filters, confidence tiers and citation traceability."""

import pytest

from assistant.domain.models import ChatRequest, ChatStatus
from assistant.infrastructure.chunk_store import ChunkStore
from assistant.infrastructure.providers import OfflineFAQProvider
from assistant.infrastructure.retrieval import BM25Index
from assistant.infrastructure.text_analysis import analyze, normalize_text, phrase_bigrams, stem, words
from assistant.services.tutor import TutorService


def make_chunk(scope, lesson, section, text, **extra):
    anchor = section.lower().replace(" ", "-")
    return {
        "id": f"{scope}--{lesson}--{anchor}", "scope": scope, "course": scope.upper(), "lesson_id": lesson,
        "title": f"Lesson {lesson}", "section": section, "anchor": f"#{anchor}",
        "url": f"/{lesson}.html#{anchor}", "text": text, **extra,
    }


CORPUS = [
    make_chunk("course:py", "loops", "While Loops",
               "A while loop keeps running as long as its condition is True. Change the condition to stop it."),
    make_chunk("course:py", "loops", "For Loops",
               "A for loop repeats code once for every item in a sequence such as a list or a range."),
    make_chunk("course:py", "types", "Data Types",
               "Integers, floats, strings and booleans are the common data types in Python programs."),
    make_chunk("course:va", "intro", "Artificial Intelligence",
               "AI tools help virtual assistants draft emails, summarize documents and automate tasks.",
               translations={"am": "ሰው ሰራሽ አስተዋይነት ቨርቹዋል ረዳቶችን ኢሜይል በመጻፍ ያግዛል።"}),
]


@pytest.fixture(scope="module")
def index():
    return BM25Index(CORPUS)


@pytest.fixture
def tutor(tmp_path):
    store = ChunkStore(tmp_path / "chunks.json")
    store.save(CORPUS)
    return TutorService(store, OfflineFAQProvider())


# --- text analysis -------------------------------------------------------------------------------

def test_ethiopic_letters_survive_and_punctuation_splits():
    assert words("ሰላም።ዓለም፣ test") == ["ሰላም", "አለም", "test"]


def test_homophone_letters_are_merged():
    assert normalize_text("ሥራ") == normalize_text("ስራ")
    assert normalize_text("ሐበሻ") == normalize_text("ሀበሻ")
    assert normalize_text("ዐይን") == normalize_text("አይን")


def test_amharic_affixes_are_stemmed_without_breaking_words():
    assert stem("ክህሎቶችን") == stem("ክህሎት")
    assert stem("የቨርቹዋል") == stem("ቨርቹዋል")
    assert stem("ወደፊት") == "ወደፊት"


def test_english_plurals_share_a_stem():
    assert stem("assistants") == stem("assistant")
    assert stem("summaries") == stem("summary")


def test_acronyms_expand_both_ways():
    assert {"artificial", "intelligenc"} <= set(analyze("What is AI?"))
    assert "va" in analyze("virtual assistant tips")


def test_phrase_bigrams_keep_meaningful_stop_words():
    assert (stem("while"), stem("loop")) in phrase_bigrams("How does a while loop work?")
    assert not phrase_bigrams("what is this")


# --- ranking and filters -------------------------------------------------------------------------

def test_title_and_phrase_signals_pick_the_concept_section(index):
    assert index.search("How does a while loop work?", scope="course:py")[0].section == "While Loops"
    assert index.search("explain the for loop", scope="course:py")[0].section == "For Loops"


def test_course_filter_is_applied_before_ranking(index):
    result = index.retrieve("How can AI help virtual assistants?", scope="course:py")
    assert all(p.scope == "course:py" for p in result.passages)
    assert result.top_confidence < 0.35


def test_lesson_filter_restricts_candidates(index):
    passages = index.search("common data types", scope="course:py", lesson="loops")
    assert all(p.lesson_id == "loops" for p in passages)
    assert index.search("common data types", scope="course:py", lesson="types")[0].section == "Data Types"


def test_synonyms_match_at_reduced_weight(index):
    exact = index.retrieve("AI help virtual assistants", scope="course:va").top_confidence
    synonym = index.retrieve("AI support virtual assistants", scope="course:va").top_confidence
    assert 0 < synonym < exact


def test_translated_text_is_searchable(index):
    result = index.retrieve("ሰው ሰራሽ አስተዋይነት ረዳቶችን እንዴት ያግዛል?", scope="course:va")
    assert result.passages[0].section == "Artificial Intelligence"
    assert result.top_confidence >= 0.6


# --- confidence tiers ----------------------------------------------------------------------------

def test_high_confidence_answers_with_confidence(tutor):
    res = tutor.answer(ChatRequest(message="How does a while loop work?", scope="course:py"))
    assert res.status == ChatStatus.ANSWERED
    assert res.confidence >= 0.6


def test_low_confidence_returns_not_found_with_human_help(tutor):
    res = tutor.answer(ChatRequest(message="What is the capital of France?", scope="course:py"))
    assert res.status == ChatStatus.NOT_FOUND
    assert res.citations == [] and "get_human_help" in res.actions


def test_vague_question_asks_for_clarification(tutor):
    res = tutor.answer(ChatRequest(message="Can you explain this?", scope="course:py"))
    assert res.status == ChatStatus.NEEDS_CLARIFICATION
    assert res.citations == []
    assert res.suggestions and set(res.suggestions) <= {c["section"] for c in CORPUS}
    assert {"clarify", "get_human_help"} <= set(res.actions)


def test_medium_confidence_widens_to_cover_the_question(tutor):
    res = tutor.answer(ChatRequest(message="while loop and data types", scope="course:py"))
    assert res.status == ChatStatus.ANSWERED
    assert {c.section for c in res.citations} == {"While Loops", "Data Types"}


# --- traceability --------------------------------------------------------------------------------

@pytest.mark.parametrize("question", [
    "How does a while loop work?", "while loop and data types", "What are the common data types?",
])
def test_every_answer_sentence_and_citation_comes_from_retrieved_content(tutor, question):
    res = tutor.answer(ChatRequest(message=question, scope="course:py"))
    assert res.status == ChatStatus.ANSWERED
    cited = [c for c in CORPUS if c["section"] in {x.section for x in res.citations}]
    assert cited, "an answer must cite at least one section"
    source = " ".join(c["text"] for c in cited)
    for sentence in filter(None, (s.strip() for s in res.answer.replace("\n", " ").split(". "))):
        assert sentence.rstrip(".") in source


def test_amharic_answer_uses_the_cited_sections_translation(tutor):
    res = tutor.answer(ChatRequest(message="AI ቨርቹዋል ረዳቶችን እንዴት ያግዛል?", scope="course:va"))
    assert res.status == ChatStatus.ANSWERED and res.language == "am"
    assert res.answer == CORPUS[3]["translations"]["am"]
    assert [c.section for c in res.citations] == ["Artificial Intelligence"]
