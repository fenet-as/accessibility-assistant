"""Turn lesson content (Markdown or generic HTML) into cited chunks, one per heading.

Chunk ids are deterministic (`<course>--<lesson>--<anchor>`), so re-ingesting a lesson
updates the same records instead of piling up duplicates.
"""

import re
from pathlib import PurePosixPath
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup

from assistant.domain.knowledge import content_hash, slugify
from assistant.infrastructure.chunk_store import Chunk

INTRO_SECTION = "Introduction & Overview"
HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")
MAX_EN_KEYWORDS = 25

# English concept -> Amharic tags, so Amharic questions can match English lessons.
AMHARIC_CONCEPTS: List[Tuple[Tuple[str, ...], str]] = [
    (("virtual assistant", "va"), "ቨርቹዋል ረዳት የሰው ረዳት"),
    (("ai", "artificial intelligence"), "ሰው ሰራሽ አስተዋይነት የኮምፒውተር ቴክኖሎጂ"),
    (("remote", "online", "work"), "የርቀት ሥራ በኢንተርኔት"),
    (("skill", "expertise"), "ክህሎት ሙያ ልዩ እውቀት"),
    (("communication", "client"), "ግንኙነት ደንበኛ አገልግሎት"),
    (("python", "programming", "code"), "ፓይዘን ፕሮግራሚንግ ኮድ አሰራር"),
    (("project", "management"), "የፕሮጀክት አስተዳደር ማስተባበር"),
    (("accessibility", "disability"), "ተደራሽነት ለአካል ጉዳተኞች"),
]


def extract_keywords(text: str, title: str) -> Tuple[str, str]:
    """Return (English keywords, Amharic concept tags) for retrieval."""
    combined = f"{title} {text}".lower()
    en_tokens = [t for t in re.findall(r"[a-zA-Z0-9]+", combined) if len(t) >= 3]
    keywords_en = " ".join(list(dict.fromkeys(en_tokens))[:MAX_EN_KEYWORDS])
    keywords_am = " ".join(tag for terms, tag in AMHARIC_CONCEPTS if any(t in combined for t in terms))
    return keywords_en, keywords_am


def normalize_url(lesson_url: str) -> str:
    return lesson_url if lesson_url.startswith(("/", "http://", "https://")) else f"/{lesson_url}"


def lesson_id_from_url(lesson_url: str) -> str:
    stem = PurePosixPath(lesson_url.split("#")[0].split("?")[0]).stem
    return slugify(stem) or "lesson"


def course_slug(course_id: str) -> str:
    return slugify(course_id.replace("course:", "")) or "course"


def chunk_id(course_id: str, lesson_id: str, anchor: str) -> str:
    return f"{course_slug(course_id)}--{lesson_id}--{anchor.lstrip('#') or 'top'}"


def build_chunk(
    course_id: str,
    course_title: str,
    lesson_id: str,
    lesson_title: str,
    section: str,
    body: str,
    lesson_url: str,
    anchor: Optional[str] = None,
    keyword_title: Optional[str] = None,
    translations: Optional[Dict[str, str]] = None,
) -> Chunk:
    anchor = anchor or slugify(section)
    keywords_en, keywords_am = extract_keywords(body, keyword_title or section)
    return {
        "id": chunk_id(course_id, lesson_id, anchor),
        "course": course_title,
        "scope": course_id,
        "lesson_id": lesson_id,
        "title": lesson_title,
        "section": section,
        "anchor": f"#{anchor}",
        "url": f"{normalize_url(lesson_url)}#{anchor}",
        "language": "en",
        "text": body,
        "translations": translations or {},
        "keywords_am": keywords_am,
        "keywords_en": keywords_en,
        "synonyms": [],
    }


def prepare_chunks(chunks: List[Chunk]) -> List[Chunk]:
    """Drop sections whose body repeats an earlier one (even under another heading) and keep anchors unique."""
    seen_bodies, seen_anchors, prepared = set(), {}, []
    for chunk in chunks:
        body = content_hash("", chunk["text"], chunk.get("translations", {}))
        if body in seen_bodies:
            continue
        seen_bodies.add(body)
        digest = content_hash(chunk["section"], chunk["text"], chunk.get("translations", {}))

        anchor = chunk["anchor"]
        if anchor:
            count = seen_anchors.get(anchor, 0) + 1
            seen_anchors[anchor] = count
            if count > 1:
                anchor = f"{anchor}-{count}"
                chunk = {**chunk, "anchor": anchor, "url": f"{chunk['url'].split('#')[0]}{anchor}",
                         "id": chunk_id(chunk["scope"], chunk["lesson_id"], anchor)}
        prepared.append({**chunk, "content_hash": digest})
    return prepared


def parse_markdown(
    content: str,
    course_id: str,
    course_title: str,
    lesson_url: str = "/pages/lesson.html",
    lesson_id: Optional[str] = None,
    lesson_title: Optional[str] = None,
) -> List[Chunk]:
    lesson_id = lesson_id or lesson_id_from_url(lesson_url)
    sections: List[Tuple[str, List[str]]] = [(INTRO_SECTION, [])]
    for line in content.strip().splitlines():
        line = line.strip()
        heading = re.match(r"^#{1,4}\s+(.+)$", line)
        if heading:
            sections.append((heading.group(1).strip(), []))
        elif line:
            sections[-1][1].append(line)

    chunks = [
        build_chunk(course_id, course_title, lesson_id, lesson_title or course_title, section,
                    " ".join(lines).strip(), lesson_url)
        for section, lines in sections if " ".join(lines).strip()
    ]
    return prepare_chunks(chunks)


def parse_html(
    content: str,
    course_id: str,
    course_title: str,
    lesson_url: str = "/pages/lesson.html",
    lesson_id: Optional[str] = None,
    lesson_title: Optional[str] = None,
) -> List[Chunk]:
    lesson_id = lesson_id or lesson_id_from_url(lesson_url)
    lesson_title = lesson_title or course_title
    soup = BeautifulSoup(content, "html.parser")
    headings = soup.find_all(HEADING_TAGS)

    if not headings:
        body = " ".join(soup.stripped_strings)
        if not body:
            return []
        return prepare_chunks([build_chunk(course_id, course_title, lesson_id, lesson_title, INTRO_SECTION,
                                           body, lesson_url, anchor="introduction", keyword_title=course_title)])

    chunks: List[Chunk] = []
    for heading in headings:
        texts: List[str] = []
        sibling = heading.next_sibling
        while sibling is not None and getattr(sibling, "name", None) not in HEADING_TAGS:
            if hasattr(sibling, "stripped_strings"):
                text = " ".join(sibling.stripped_strings)
                if text:
                    texts.append(text)
            sibling = sibling.next_sibling

        body = " ".join(texts).strip()
        if body:
            section = heading.get_text().strip()
            chunks.append(build_chunk(course_id, course_title, lesson_id, lesson_title, section, body,
                                      lesson_url, anchor=heading.get("id") or slugify(section)))
    return prepare_chunks(chunks)
