"""Parser for Savanna concept pages (the ALX static starter), producing cited chunks.

Run `python -m assistant.ingest` to rebuild `assistant/data/chunks.json` from the
bundled concept page.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup

from assistant.infrastructure.chunk_store import Chunk
from assistant.ingest.parsers import INTRO_SECTION, chunk_id, lesson_id_from_url, prepare_chunks

COURSE_NAME = "VA-1: VA Foundations & Professional Identity"
COURSE_SCOPE = "course:va-1"
PAGE_URL = "/pages/concept-with-navigation.html"
LESSON_ID = lesson_id_from_url(PAGE_URL)
CONTENT_ROOT_ID = "curriculum_navigation_content"
SKIPPED_PREFIXES = ("VA-Content-Banner", "Evon afro")

INTRO_KEYWORDS = (
    "virtual assistant definition remote professional AI assistant difference",
    "ቨርቹዋል ረዳት ምንድን ነው መግቢያ ትርጉም የሰው ረዳት እና የኮምፒውተር ረዳት ልዩነት",
)

# Section anchor fragment -> (extra English keywords, Amharic keywords).
SECTION_KEYWORDS: Dict[str, Tuple[str, str]] = {
    "shaping-the-future": (
        "remote-first flexibility digital operations specialization AI productivity human skills",
        "የቨርቹዋል ረዳት የወደፊት ሁኔታ አዝማሚያዎች የርቀት ሥራ ተለዋዋጭነት ዲጂታል ክህሎቶች የሰው ችሎታ",
    ),
    "artificial-intelligence": (
        "artificial intelligence tools automation drafting summaries human relationship empathy",
        "ሰው ሰራሽ አስተዋይነት AI የኮምፒውተር ቴክኖሎጂ ጥቅሞች እና የሰው ረዳት አስፈላጊነት",
    ),
    "what-clients-are-likely-to-value": (
        "client value AI fluency specialized expertise excellent human service",
        "ደንበኞች የሚፈልጓቸው ክህሎቶች የቴክኖሎጂ ችሎታ ልዩ እውቀት የሰው አገልግሎት",
    ),
    "what-this-means-for-aspiring": (
        "aspiring virtual assistants tips advice learn digital tools communication",
        "ለጀማሪ ቨርቹዋል ረዳቶች ምክር አዳዲስ ቴክኖሎጂዎችን መማር ግንኙነት",
    ),
    "promising": (
        "promising future career workflow partner operations",
        "የቨርቹዋል ረዳት ሥራ ተስፋ አለው ወይ የወደፊት ዕድል",
    ),
}

# Section anchor fragment -> phrases learners use for the same idea.
SECTION_SYNONYMS: Dict[str, List[str]] = {
    "artificial-intelligence": ["machine learning", "chatgpt", "automation tools", "robots replacing jobs"],
    "shaping-the-future": ["trends", "industry changes", "work from home"],
    "what-clients-are-likely-to-value": ["employer expectations", "what customers want", "in-demand skills"],
    "what-this-means-for-aspiring": ["beginners", "getting started", "new virtual assistants"],
    "promising": ["job outlook", "is it worth it", "career prospects"],
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _lookup(table: Dict[str, object], anchor_id: str):
    return next((value for fragment, value in table.items() if fragment in anchor_id), None)


def _section_keywords(anchor_id: str, section_title: str) -> Tuple[str, str]:
    match = _lookup(SECTION_KEYWORDS, anchor_id)
    if match:
        extra_en, keywords_am = match
        return f"{section_title.lower()} {extra_en}", keywords_am
    return section_title.lower(), ""


def load_curated_translations(path: Optional[Path]) -> Dict[str, Dict[str, str]]:
    """All curated offline translations keyed by language, then by anchor fragment."""
    if not path or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {lang: answers for lang, answers in data.items() if not lang.startswith("_")}


def _translations_for_anchor(catalog: Dict[str, Dict[str, str]], anchor_id: str) -> Dict[str, str]:
    if not anchor_id:
        return {}
    found = {}
    for lang, answers in catalog.items():
        match = _lookup(answers, anchor_id)
        if match:
            found[lang] = match
    return found


def _chunk(title: str, section: str, anchor_id: str, text: str, keywords: Tuple[str, str],
           catalog: Dict[str, Dict[str, str]]) -> Chunk:
    anchor = f"#{anchor_id}" if anchor_id else ""
    return {
        "id": chunk_id(COURSE_SCOPE, LESSON_ID, anchor_id or "top"),
        "course": COURSE_NAME,
        "scope": COURSE_SCOPE,
        "lesson_id": LESSON_ID,
        "title": title,
        "section": section,
        "anchor": anchor,
        "url": f"{PAGE_URL}{anchor}",
        "language": "en",
        "text": text,
        "translations": _translations_for_anchor(catalog, anchor_id),
        "keywords_am": keywords[1],
        "keywords_en": keywords[0],
        "synonyms": (_lookup(SECTION_SYNONYMS, anchor_id) or []) if anchor_id else [],
    }


def parse_concept_page(html: str, catalog: Optional[Dict[str, Dict[str, str]]] = None) -> List[Chunk]:
    catalog = catalog or {}
    soup = BeautifulSoup(html, "html.parser")
    root = soup.find(id=CONTENT_ROOT_ID)
    if not root:
        raise ValueError(f"Could not find #{CONTENT_ROOT_ID} in HTML")

    h1 = root.find("h1")
    concept_title = _clean(h1.get_text()) if h1 else "Course Material"
    body = root.find("div", class_="savanna-styles") or root
    chunks: List[Chunk] = []

    intro: List[str] = []
    for element in body.children:
        name = getattr(element, "name", None)
        if name == "h4":
            break
        if name in ("p", "div", "mark"):
            text = _clean(element.get_text())
            if text and not text.startswith(SKIPPED_PREFIXES):
                intro.append(text)
    if intro:
        chunks.append(_chunk(concept_title, INTRO_SECTION, CONTENT_ROOT_ID, " ".join(intro),
                             INTRO_KEYWORDS, catalog))

    for h4 in body.find_all("h4"):
        section_title = _clean(h4.get_text())
        if not section_title:
            continue
        anchor_tag = h4.find("a", class_="anchor")
        anchor_id = anchor_tag.get("id") if anchor_tag else ""

        texts: List[str] = []
        sibling = h4.next_sibling
        while sibling is not None and getattr(sibling, "name", None) != "h4":
            if getattr(sibling, "name", None) in ("p", "div", "ul", "ol", "figure"):
                text = _clean(sibling.get_text())
                if text and not text.startswith(SKIPPED_PREFIXES[0]):
                    texts.append(text)
            sibling = sibling.next_sibling

        if texts:
            chunks.append(_chunk(concept_title, section_title, anchor_id, " ".join(texts),
                                 _section_keywords(anchor_id, section_title), catalog))
    return prepare_chunks(chunks)


def parse_concept_file(path: Path, translations_path: Optional[Path] = None) -> List[Chunk]:
    if not path.exists():
        raise FileNotFoundError(f"Source file not found: {path}")
    return parse_concept_page(path.read_text(encoding="utf-8"), load_curated_translations(translations_path))
