"""
Offline FAQ and Rule-Based AI Provider.
Generates grounded answers strictly from course passages with 100% offline reliability.
"""

from typing import List
from assistant.core.models import AIProvider, ChatResponse, ChatStatus, Citation, Passage


class OfflineFAQProvider:
    name: str = "offline_faq"

    def generate(
        self,
        question: str,
        passages: List[Passage],
        language: str,
        simple: bool = False
    ) -> ChatResponse:
        if not passages:
            if language == "am":
                msg = "ይቅርታ፣ ይህ ጥያቄ በተሰጠው የትምህርት ይዘት ውስጥ አልተገኘም። ከቀጥታ ረዳት ጋር መገናኘት ይፈልጋሉ?"
            else:
                msg = "I'm sorry, but this question cannot be answered from the available course material. Would you like to connect with a human tutor?"
            return ChatResponse(
                status=ChatStatus.NOT_FOUND,
                language=language,
                answer=msg,
                citations=[],
                actions=["get_human_help"]
            )

        top_passage = passages[0]

        # Extract sentences from top passage
        text = top_passage.text
        sentences = [s.strip() for s in text.split(". ") if len(s.strip()) > 10]

        # Build grounded summary
        if simple:
            # Simple Mode: 1-2 short key sentences
            selected = sentences[:2]
            summary_en = ". ".join(selected) + "."
        else:
            selected = sentences[:4]
            summary_en = ". ".join(selected) + "."

        if language == "am":
            # Grounded bilingual response based on section
            if "shaping-the-future" in top_passage.anchor:
                answer = (
                    "የቨርቹዋል ረዳት (VA) ሥራ እየሰፋና እየተቀየረ ነው። "
                    "ዋና ዋና ለውጦች፡ የርቀት ሥራ መስፋፋት፣ ተለዋዋጭነት ፍላጎት መጨመር፣ "
                    "የዲጂታል አሠራሮች ማደግ፣ የልዩ ችሎታዎች ፍላጎት፣ እንዲሁም የሰው ሰራሽ አስተዋይነት (AI) አጠቃቀም ናቸው።"
                )
            elif "artificial-intelligence" in top_passage.anchor:
                answer = (
                    "ሰው ሰራሽ አስተዋይነት (AI) በቨርቹዋል ረዳቶች ሥራ ውስጥ ትልቅ ሚና ይጫወታል። "
                    "AI እንደ ኢሜይል መጻፍ፣ ጽሑፎችን ማጠቃለልና መረጃ መፈለግ ያሉ ስራዎችን ያግዛል። "
                    "ነገር ግን የሰው ቨርቹዋል ረዳቶች የደንበኛ ግንኙነትን በመምራትና በስሜት ብስለት እጅግ አስፈላጊ ሆነው ይቀጥላሉ።"
                )
            elif "what-clients-are-likely-to-value" in top_passage.anchor:
                answer = (
                    "ደንበኞች ወደፊት ይበልጥ ዋጋ የሚሰጧቸው ክህሎቶች፡ "
                    "የAI ቴክኖሎጂን በአግባቡ የመጠቀም ችሎታ፣ በተመረጡ ዘርፎች ልዩ እውቀት ማዳበር፣ "
                    "እና ጥራት ያለው የሰው አገልግሎት (ታማኝነት፣ ግልጽ ግንኙነት) ናቸው።"
                )
            elif "what-this-means-for-aspiring" in top_passage.anchor:
                answer = (
                    "ለጀማሪ ቨርቹዋል ረዳቶች፡ አዳዲስ ዲጂታል መሣሪያዎችን ለመማር ዝግጁ መሆን፣ "
                    "AIን እንደ አጋዥ መጠቀም፣ ጠንካራ የግንኙነት ክህሎት ማዳበር፣ "
                    "እና በጊዜ ሂደት የተለየ ሙያዊ ዘርፍ ላይ ማተኮር ይመረጣል።"
                )
            elif "promising" in top_passage.anchor:
                answer = (
                    "አዎ፣ የቨርቹዋል ረዳት ሙያ ተስፋ አለው። ተለዋዋጭ፣ ቴክኖሎጂን የሚረዱ እና "
                    "የተደራጁ የሰው ባለሙያዎች በገበያው ውስጥ ከፍተኛ ዋጋ አላቸው።"
                )
            else:
                answer = f"እንደ ትምህርቱ ይዘት፡ {top_passage.section} - {summary_en}"
        else:
            answer = summary_en

        citations = [
            Citation(
                title=p.title,
                section=p.section,
                url=p.url
            )
            for p in passages[:2]
        ]

        return ChatResponse(
            status=ChatStatus.ANSWERED,
            language=language,
            answer=answer,
            citations=citations,
            actions=["get_human_help"]
        )
