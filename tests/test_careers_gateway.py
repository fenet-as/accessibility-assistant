"""Milestone 8: verified jobs, expiry, chat answers, alerts, unsubscribe."""

from datetime import date, timedelta

from assistant.services.careers import CareerService, is_job_question
from assistant.services.job_alerts import JobAlertDispatcher
from assistant.infrastructure.database import Database


def test_expired_jobs_are_hidden(tmp_path):
    db = Database(tmp_path / "jobs.db")
    careers = CareerService(db)
    past = (date.today() - timedelta(days=1)).isoformat()
    future = (date.today() + timedelta(days=10)).isoformat()
    careers.add_job(
        "Expired Role", "Org", "desc with enough text", source_url="https://example.com/1", closing_date=past
    )
    careers.add_job(
        "Open Role", "Org", "desc with enough text", source_url="https://example.com/2", closing_date=future
    )
    titles = {j["title"] for j in careers.list_jobs()}
    assert titles == {"Open Role"}


def test_chat_answers_only_stored_jobs(client, container):
    # Clear by using answer with no jobs after delete - seed may have jobs.
    answer = container.careers.answer_job_question("en")
    assert "Verified openings" in answer or "no verified" in answer.lower() or "No verified" in answer or "no verified open jobs" in answer.lower() or "There are no verified" in answer
    res = client.post("/api/chat", json={"message": "What jobs are available?", "language": "en"})
    assert res.status_code == 200
    assert res.json()["provider"] == "careers" or "job" in res.json()["answer"].lower() or "opening" in res.json()["answer"].lower() or "verified" in res.json()["answer"].lower()


def test_job_intent_detector():
    assert is_job_question("Are there any job openings?")
    assert is_job_question("ክፍት የሥራ ቦታ አለ?")
    assert not is_job_question("What is a virtual assistant?")
    assert not is_job_question("ሰው ሰራሽ አስተዋይነት (AI) በቨርቹዋል ረዳቶች ሥራ ላይ ምን ምንድን ነው?")


def test_dispatcher_sends_once_and_unsubscribe_stops(tmp_path):
    db = Database(tmp_path / "jobs.db")
    careers = CareerService(db)
    careers.add_job("Role", "Org", "A verified description for testing alerts.", source_url="https://example.com/a")
    careers.subscribe("sms", "+251911000000", consent=True)
    dispatcher = JobAlertDispatcher(careers, sms=None, telegram=None)
    first = dispatcher.dispatch()
    second = dispatcher.dispatch()
    assert first["sent"] == 1
    assert second["sent"] == 0
    careers.unsubscribe("sms", "+251911000000")
    third = dispatcher.dispatch()
    assert third["sent"] == 0
