"""
Course Content Ingestion and Semantic Chunker
Extracts curriculum sections from Savanna static HTML into structured, cited chunks.
"""

import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
from typing import List, Dict, Any


class CourseChunker:
    def __init__(self, html_path: Path):
        self.html_path = html_path

    def clean_text(self, text: str) -> str:
        """Normalize whitespace and remove unwanted characters."""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def parse(self) -> List[Dict[str, Any]]:
        """Parse HTML into semantic chunks with anchor references."""
        if not self.html_path.exists():
            raise FileNotFoundError(f"Source file not found: {self.html_path}")

        with open(self.html_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")

        # Find the main curriculum content area
        content_div = soup.find(id="curriculum_navigation_content")
        if not content_div:
            raise ValueError("Could not find #curriculum_navigation_content in HTML")

        # Get course and concept titles
        h1 = content_div.find("h1")
        concept_title = self.clean_text(h1.get_text()) if h1 else "Course Material"
        course_name = "VA-1: VA Foundations & Professional Identity"

        chunks: List[Dict[str, Any]] = []
        chunk_idx = 1

        formatted_div = content_div.find("div", class_="savanna-styles")
        if not formatted_div:
            formatted_div = content_div

        # Process intro before the first h4
        intro_texts = []
        for elem in formatted_div.children:
            if getattr(elem, "name", None) == "h4":
                break
            if getattr(elem, "name", None) in ["p", "div", "mark"]:
                t = self.clean_text(elem.get_text())
                if t and not t.startswith("VA-Content-Banner") and not t.startswith("Evon afro"):
                    intro_texts.append(t)

        if intro_texts:
            full_intro = " ".join(intro_texts)
            chunks.append({
                "id": f"va-intro-{chunk_idx}",
                "course": course_name,
                "scope": "course:va-1",
                "title": concept_title,
                "section": "Introduction & Overview",
                "anchor": "#curriculum_navigation_content",
                "url": "/pages/concept-with-navigation.html#curriculum_navigation_content",
                "language": "en",
                "text": full_intro,
                # Bilingual keywords for Amharic keyword match
                "keywords_am": "ቨርቹዋል ረዳት ምንድን ነው መግቢያ ትርጉም የሰው ረዳት እና የኮምፒውተር ረዳት ልዩነት",
                "keywords_en": "virtual assistant definition remote professional AI assistant difference"
            })
            chunk_idx += 1

        # Find all h4 sections
        h4_tags = formatted_div.find_all("h4")
        for h4 in h4_tags:
            anchor_tag = h4.find("a", class_="anchor")
            anchor_id = anchor_tag.get("id") if anchor_tag else ""
            section_title = self.clean_text(h4.get_text())
            if not section_title:
                continue

            # Gather content until next h4 or hr
            section_texts = []
            curr = h4.next_sibling
            while curr:
                if getattr(curr, "name", None) == "h4":
                    break
                if getattr(curr, "name", None) in ["p", "div", "ul", "ol", "figure"]:
                    txt = self.clean_text(curr.get_text())
                    if txt and not txt.startswith("VA-Content-Banner"):
                        section_texts.append(txt)
                curr = curr.next_sibling

            section_body = " ".join(section_texts)
            if not section_body:
                continue

            # Tag specific topics for retrieval precision & bilingual support
            keywords_am = ""
            keywords_en = section_title.lower()

            if "shaping-the-future" in anchor_id:
                keywords_am = "የቨርቹዋል ረዳት የወደፊት ሁኔታ አዝማሚያዎች የርቀት ሥራ ተለዋዋጭነት ዲጂታል ክህሎቶች የሰው ችሎታ"
                keywords_en += " remote-first flexibility digital operations specialization AI productivity human skills"
            elif "artificial-intelligence" in anchor_id:
                keywords_am = "ሰው ሰራሽ አስተዋይነት AI የኮምፒውተር ቴክኖሎጂ ጥቅሞች እና የሰው ረዳት አስፈላጊነት"
                keywords_en += " artificial intelligence tools automation drafting summaries human relationship empathy"
            elif "what-clients-are-likely-to-value" in anchor_id:
                keywords_am = "ደንበኞች የሚፈልጓቸው ክህሎቶች የቴክኖሎጂ ችሎታ ልዩ እውቀት የሰው አገልግሎት"
                keywords_en += " client value AI fluency specialized expertise excellent human service"
            elif "what-this-means-for-aspiring" in anchor_id:
                keywords_am = "ለጀማሪ ቨርቹዋል ረዳቶች ምክር አዳዲስ ቴክኖሎጂዎችን መማር ግንኙነት"
                keywords_en += " aspiring virtual assistants tips advice learn digital tools communication"
            elif "promising" in anchor_id:
                keywords_am = "የቨርቹዋል ረዳት ሥራ ተስፋ አለው ወይ የወደፊት ዕድል"
                keywords_en += " promising future career workflow partner operations"

            chunks.append({
                "id": f"va-section-{chunk_idx}",
                "course": course_name,
                "scope": "course:va-1",
                "title": concept_title,
                "section": section_title,
                "anchor": f"#{anchor_id}" if anchor_id else "",
                "url": f"/pages/concept-with-navigation.html#{anchor_id}" if anchor_id else "/pages/concept-with-navigation.html",
                "language": "en",
                "text": section_body,
                "keywords_am": keywords_am,
                "keywords_en": keywords_en
            })
            chunk_idx += 1

        return chunks


def run_ingestion(source_file: Path, output_file: Path) -> List[Dict[str, Any]]:
    """Main execution function for content ingestion."""
    chunker = CourseChunker(source_file)
    chunks = chunker.parse()

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    return chunks


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent.parent
    source = base_dir / "savanna-static" / "pages" / "concept-with-navigation.html"
    dest = base_dir / "assistant" / "data" / "chunks.json"
    
    result = run_ingestion(source, dest)
    print(f"Ingestion complete: {len(result)} semantic chunks written to {dest}")

