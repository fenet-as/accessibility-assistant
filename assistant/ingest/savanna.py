"""Parser for Savanna concept pages (the ALX static starter), producing cited chunks.

Run `python -m assistant.ingest` to rebuild `assistant/data/chunks.json` from the
bundled concept page.
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

from bs4 import BeautifulSoup

from assistant.infrastructure.chunk_store import Chunk
from assistant.ingest.parsers import INTRO_SECTION

COURSE_NAME = "VA-1: VA Foundations & Professional Identity"
COURSE_SCOPE = "course:va-1"
PAGE_URL = "/pages/concept-with-navigation.html"
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


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _section_keywords(anchor_id: str, section_title: str) -> Tuple[str, str]:
    for fragment, (extra_en, keywords_am) in SECTION_KEYWORDS.items():
        if fragment in anchor_id:
            return f"{section_title.lower()} {extra_en}", keywords_am
    return section_title.lower(), ""


def _chunk(chunk_id: str, title: str, section: str, anchor_id: str, text: str,
           keywords: Tuple[str, str]) -> Chunk:
    anchor = f"#{anchor_id}" if anchor_id else ""
    return {
        "id": chunk_id,
        "course": COURSE_NAME,
        "scope": COURSE_SCOPE,
        "title": title,
        "section": section,
        "anchor": anchor,
        "url": f"{PAGE_URL}{anchor}",
        "language": "en",
        "text": text,
        "keywords_am": keywords[1],
        "keywords_en": keywords[0],
    }


def parse_concept_page(html: str) -> List[Chunk]:
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
        chunks.append(_chunk("va-intro-1", concept_title, INTRO_SECTION, CONTENT_ROOT_ID,
                             " ".join(intro), INTRO_KEYWORDS))

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
            chunks.append(_chunk(f"va-section-{len(chunks) + 1}", concept_title, section_title,
                                 anchor_id, " ".join(texts), _section_keywords(anchor_id, section_title)))
    return chunks


def parse_concept_file(path: Path) -> List[Chunk]:
    if not path.exists():
        raise FileNotFoundError(f"Source file not found: {path}")
    return parse_concept_page(path.read_text(encoding="utf-8"))
