"""
Universal Course Ingestion & Chunking Engine.
Supports Markdown and HTML course content with automatic anchor slug generation,
bilingual keyword extraction, and multi-course index management.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup


CHUNKS_FILE = Path(__file__).resolve().parent.parent / "data" / "chunks.json"


def slugify(text: str) -> str:
    """Convert a section title into a URL-safe HTML anchor slug."""
    text = text.lower().strip()
    # Remove characters other than letters, numbers, hyphens, and spaces
    text = re.sub(r"[^\w\s-]", "", text)
    # Replace spaces and multiple hyphens with a single hyphen
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def extract_keywords(text: str, title: str) -> tuple[str, str]:
    """Generate English and Amharic keyword tags for semantic matching."""
    combined = f"{title} {text}".lower()

    # English domain keywords (alphanumeric tokens >= 3 chars)
    en_tokens = [t for t in re.findall(r"[a-zA-Z0-9]+", combined) if len(t) >= 3]
    unique_en = list(dict.fromkeys(en_tokens))[:25]
    keywords_en = " ".join(unique_en)

    # Core concept Amharic mappings
    am_tags = []
    concept_map = [
        (["virtual assistant", "va"], "ቨርቹዋል ረዳት የሰው ረዳት"),
        (["ai", "artificial intelligence"], "ሰው ሰራሽ አስተዋይነት የኮምፒውተር ቴክኖሎጂ"),
        (["remote", "online", "work"], "የርቀት ሥራ በኢንተርኔት"),
        (["skill", "expertise"], "ክህሎት ሙያ ልዩ እውቀት"),
        (["communication", "client"], "ግንኙነት ደንበኛ አገልግሎት"),
        (["python", "programming", "code"], "ፓይዘን ፕሮግራሚንግ ኮድ አሰራር"),
        (["project", "management"], "የፕሮጀክት አስተዳደር ማስተባበር"),
        (["accessibility", "disability"], "ተደራሽነት ለአካል ጉዳተኞች"),
    ]
    for terms, am_tag in concept_map:
        if any(term in combined for term in terms):
            am_tags.append(am_tag)

    keywords_am = " ".join(am_tags)
    return keywords_en, keywords_am


class UniversalChunker:
    """Ingests Markdown or HTML course material and updates chunks.json."""

    def __init__(self, chunks_path: Optional[Path] = None):
        self.chunks_path = chunks_path or CHUNKS_FILE

    def parse_markdown(
        self,
        content: str,
        course_id: str,
        course_title: str,
        lesson_url: str = "/pages/lesson.html"
    ) -> List[Dict[str, Any]]:
        """Parse Markdown formatted lesson text into semantic chunks."""
        clean_url = lesson_url if lesson_url.startswith("/") else f"/{lesson_url}"
        lines = content.strip().split("\n")
        chunks: List[Dict[str, Any]] = []

        current_heading = "Introduction & Overview"
        current_body: List[str] = []
        chunk_idx = 1

        course_prefix = slugify(course_id.replace("course:", "")) or "course"

        for line in lines:
            line_stripped = line.strip()
            # Match Markdown headings (# Title, ## Section, ### Sub)
            heading_match = re.match(r"^#{1,4}\s+(.+)$", line_stripped)
            if heading_match:
                if current_body:
                    body_text = " ".join(current_body).strip()
                    if body_text:
                        anchor_slug = slugify(current_heading)
                        kw_en, kw_am = extract_keywords(body_text, current_heading)
                        chunks.append({
                            "id": f"{course_prefix}-chunk-{chunk_idx}",
                            "course": course_title,
                            "scope": course_id,
                            "title": course_title,
                            "section": current_heading,
                            "anchor": f"#{anchor_slug}",
                            "url": f"{clean_url}#{anchor_slug}",
                            "language": "en",
                            "text": body_text,
                            "keywords_am": kw_am,
                            "keywords_en": kw_en,
                        })
                        chunk_idx += 1
                current_heading = heading_match.group(1).strip()
                current_body = []
            else:
                if line_stripped:
                    current_body.append(line_stripped)

        # Append final section
        if current_body:
            body_text = " ".join(current_body).strip()
            if body_text:
                anchor_slug = slugify(current_heading)
                kw_en, kw_am = extract_keywords(body_text, current_heading)
                chunks.append({
                    "id": f"{course_prefix}-chunk-{chunk_idx}",
                    "course": course_title,
                    "scope": course_id,
                    "title": course_title,
                    "section": current_heading,
                    "anchor": f"#{anchor_slug}",
                    "url": f"{clean_url}#{anchor_slug}",
                    "language": "en",
                    "text": body_text,
                    "keywords_am": kw_am,
                    "keywords_en": kw_en,
                })

        return chunks

    def parse_html(
        self,
        content: str,
        course_id: str,
        course_title: str,
        lesson_url: str = "/pages/lesson.html"
    ) -> List[Dict[str, Any]]:
        """Parse HTML formatted lesson text into semantic chunks."""
        clean_url = lesson_url if lesson_url.startswith("/") else f"/{lesson_url}"
        soup = BeautifulSoup(content, "html.parser")
        chunks: List[Dict[str, Any]] = []

        course_prefix = slugify(course_id.replace("course:", "")) or "course"
        chunk_idx = 1

        headings = soup.find_all(re.compile(r"^h[1-6]$"))
        if not headings:
            # If no headings, treat whole text as single intro chunk
            body_text = " ".join(soup.stripped_strings)
            if body_text:
                kw_en, kw_am = extract_keywords(body_text, course_title)
                chunks.append({
                    "id": f"{course_prefix}-chunk-1",
                    "course": course_title,
                    "scope": course_id,
                    "title": course_title,
                    "section": "Introduction & Overview",
                    "anchor": "#introduction",
                    "url": f"{clean_url}#introduction",
                    "language": "en",
                    "text": body_text,
                    "keywords_am": kw_am,
                    "keywords_en": kw_en,
                })
            return chunks

        for h in headings:
            section_title = h.get_text().strip()
            anchor_slug = h.get("id") or slugify(section_title)

            # Collect following sibling elements until next heading
            texts: List[str] = []
            curr = h.next_sibling
            while curr:
                if getattr(curr, "name", None) in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                    break
                if hasattr(curr, "stripped_strings"):
                    t = " ".join(curr.stripped_strings)
                    if t:
                        texts.append(t)
                curr = curr.next_sibling

            body_text = " ".join(texts).strip()
            if body_text:
                kw_en, kw_am = extract_keywords(body_text, section_title)
                chunks.append({
                    "id": f"{course_prefix}-chunk-{chunk_idx}",
                    "course": course_title,
                    "scope": course_id,
                    "title": course_title,
                    "section": section_title,
                    "anchor": f"#{anchor_slug}",
                    "url": f"{clean_url}#{anchor_slug}",
                    "language": "en",
                    "text": body_text,
                    "keywords_am": kw_am,
                    "keywords_en": kw_en,
                })
                chunk_idx += 1

        return chunks

    def ingest_course(
        self,
        course_id: str,
        course_title: str,
        content: str,
        content_type: str = "markdown",
        lesson_url: str = "/pages/lesson.html"
    ) -> List[Dict[str, Any]]:
        """
        Ingest course material, remove previous version of the course if present,
        and save updated corpus to chunks.json.
        """
        if content_type.lower() == "html":
            new_chunks = self.parse_html(content, course_id, course_title, lesson_url)
        else:
            new_chunks = self.parse_markdown(content, course_id, course_title, lesson_url)

        if not new_chunks:
            raise ValueError("No valid sections or text could be extracted from the content.")

        # Load existing chunks
        existing: List[Dict[str, Any]] = []
        if self.chunks_path.exists():
            with open(self.chunks_path, "r", encoding="utf-8") as f:
                existing = json.load(f)

        # Remove existing chunks for this specific course to allow clean updates
        filtered = [
            c for c in existing
            if c.get("scope") != course_id and c.get("course") != course_title
        ]

        # Append new chunks
        filtered.extend(new_chunks)

        # Write back to disk
        self.chunks_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.chunks_path, "w", encoding="utf-8") as f:
            json.dump(filtered, f, indent=2, ensure_ascii=False)

        return new_chunks

    def list_courses(self) -> List[Dict[str, Any]]:
        """List all indexed courses, chunk counts, and section lists."""
        if not self.chunks_path.exists():
            return []

        with open(self.chunks_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        courses: Dict[str, Dict[str, Any]] = {}
        for c in chunks:
            cid = c.get("scope") or c.get("course", "unknown")
            ctitle = c.get("course") or c.get("title", cid)
            if cid not in courses:
                courses[cid] = {
                    "course_id": cid,
                    "course_title": ctitle,
                    "chunk_count": 0,
                    "sections": [],
                    "sample_url": c.get("url", ""),
                }
            courses[cid]["chunk_count"] += 1
            if c.get("section") and c.get("section") not in courses[cid]["sections"]:
                courses[cid]["sections"].append(c.get("section"))

        return list(courses.values())

    def delete_course(self, course_id: str) -> bool:
        """Remove all chunks associated with a course_id."""
        if not self.chunks_path.exists():
            return False

        with open(self.chunks_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        initial_len = len(chunks)
        filtered = [
            c for c in chunks
            if c.get("scope") != course_id and c.get("course") != course_id
        ]

        if len(filtered) == initial_len:
            return False  # Course not found

        with open(self.chunks_path, "w", encoding="utf-8") as f:
            json.dump(filtered, f, indent=2, ensure_ascii=False)

        return True
