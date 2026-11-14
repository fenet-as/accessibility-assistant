"""Voice/language context: Amharic greetings and conversation history."""

from assistant.domain.messages import detect_social_response
from assistant.domain.models import ChatRequest, ChatStatus, ConversationTurn
from assistant.services.tutor import TutorService


def test_amharic_greeting_replies_in_amharic_not_tigrinya(container):
    social = detect_social_response("ሰላም እንዴት", "auto")
    assert social is not None
    assert social.language == "am"
    assert "ሳቫና" in social.answer or "ትምህርት" in social.answer
    assert "ሓጋዚ" not in social.answer


def test_follow_up_uses_history_context(container):
    tutor: TutorService = container.tutor
    first = tutor.answer(ChatRequest(
        message="What is a virtual assistant?",
        language="en",
        scope="course:va-1",
    ))
    assert first.status == ChatStatus.ANSWERED
    follow = tutor.answer(ChatRequest(
        message="What skills do they need?",
        language="en",
        scope="course:va-1",
        history=[
            ConversationTurn(role="user", content="What is a virtual assistant?"),
            ConversationTurn(role="assistant", content=first.answer),
        ],
    ))
    assert follow.status == ChatStatus.ANSWERED
    assert follow.citations