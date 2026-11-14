"""Turn lesson content (Markdown or generic HTML) into cited chunks, one per heading."""

import re
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup

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


def slugify(text: str) -> str:
    """Convert a section title into a URL-safe HTML anchor slug."""
    text = re.sub(r"[^\w\s-]", "", text.lower().strip())
    return re.sub(r"[\s_-]+", "-", text).strip("-")


def extract_keywords(text: str, title: str) -> Tuple[str, str]:
    """Return (English keywords, Amharic concept tags) for retrieval."""
    combined = f"{title} {text}".lower()
    en_tokens = [t for t in re.findall(r"[a-zA-Z0-9]+", combined) if len(t) >= 3]
    keywords_en = " ".join(list(dict.fromkeys(en_tokens))[:MAX_EN_KEYWORDS])
    keywords_am = " ".join(tag for terms, tag in AMHARIC_CONCEPTS if any(t in combined for t in terms))
    return keywords_en, keywords_am


def _normalize_url(lesson_url: str) -> str:
    return lesson_url if lesson_url.startswith("/") else f"/{lesson_url}"


def _course_prefix(course_id: str) -> str:
    return slugify(course_id.replace("course:", "")) or "course"


def build_chunk(
    index: int,
    course_id: str,
    course_title: str,
    section: str,
    body: str,
    lesson_url: str,
    anchor: Optional[str] = None,
    keyword_title: Optional[str] = None,
) -> Chunk:
    anchor = anchor or slugify(section)
    keywords_en, keywords_am = extract_keywords(body, keyword_title or section)
    return {
        "id": f"{_course_prefix(course_id)}-chunk-{index}",
        "course": course_title,
        "scope": course_id,
        "title": course_title,
        "section": section,
        "anchor": f"#{anchor}",
        "url": f"{_normalize_url(lesson_url)}#{anchor}",
        "language": "en",
        "text": body,
        "keywords_am": keywords_am,
        "keywords_en": keywords_en,
    }


def parse_markdown(
    content: str,
    course_id: str,
    course_title: str,
    lesson_url: str = "/pages/lesson.html",
) -> List[Chunk]:
    sections: List[Tuple[str, List[str]]] = [(INTRO_SECTION, [])]
    for line in content.strip().splitlines():
        line = line.strip()
        heading = re.match(r"^#{1,4}\s+(.+)$", line)
        if heading:
            sections.append((heading.group(1).strip(), []))
        elif line:
            sections[-1][1].append(line)

    chunks: List[Chunk] = []
    for section, lines in sections:
        body = " ".join(lines).strip()
        if body:
            chunks.append(build_chunk(len(chunks) + 1, course_id, course_title, section, body, lesson_url))
    return chunks


def parse_html(
    content: str,
    course_id: str,
    course_title: str,
    lesson_url: str = "/pages/lesson.html",
) -> List[Chunk]:
    soup = BeautifulSoup(content, "html.parser")
    headings = soup.find_all(HEADING_TAGS)

    if not headings:
        body = " ".join(soup.stripped_strings)
        if not body:
            return []
        return [build_chunk(1, course_id, course_title, INTRO_SECTION, body, lesson_url,
                            anchor="introduction", keyword_title=course_title)]

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
            chunks.append(build_chunk(
                len(chunks) + 1, course_id, course_title, section, body, lesson_url,
                anchor=heading.get("id") or slugify(section),
            ))
    return chunks
