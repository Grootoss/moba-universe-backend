"""The bundled MLBB catalog: 100 tests, grouped by role."""

from sqlalchemy import func, select

from app.models import Quiz, QuizQuestion
from app.quiz_seed import seed_mlbb_quizzes
from tests.conftest import auth_header


def test_mlbb_catalog_loads_and_plays(client, db_session, admin_user):
    seed_mlbb_quizzes(db_session.connection())
    db_session.commit()

    total = db_session.scalar(select(func.count()).select_from(Quiz).where(Quiz.game == "mlbb"))
    questions = db_session.scalar(
        select(func.count())
        .select_from(QuizQuestion)
        .join(Quiz, Quiz.id == QuizQuestion.quiz_id)
        .where(Quiz.game == "mlbb")
    )
    assert total == 100
    assert questions == 802

    roam = client.get("/api/quizzes?game=mlbb&role=roam&lang=ru")
    assert roam.status_code == 200
    roam_rows = roam.json()
    assert len(roam_rows) == 20
    assert roam_rows[0]["slug"] == "roam-basics"
    assert roam_rows[0]["question_count"] == 10
    assert roam_rows[0]["cover_image"].endswith(".svg")

    for role, count in (("mid", 20), ("jungle", 20), ("exp", 20), ("gold", 20)):
        body = client.get(f"/api/quizzes?game=mlbb&role={role}&lang=en").json()
        assert len(body) == count
        assert {row["role"] for row in body} == {role}

    preview = client.get("/api/quizzes/roam-basics/preview?lang=ru")
    assert preview.status_code == 200
    assert preview.json()["question_count"] == 10
    assert "questions" not in preview.json()

    quiz = client.get("/api/quizzes/mid-basics?lang=en").json()
    assert quiz["game"] == "mlbb"
    assert len(quiz["questions"]) == 8
    assert "is_correct" not in quiz["questions"][0]["options"][0]

    answers = []
    stored = db_session.scalar(select(Quiz).where(Quiz.slug == "mid-basics"))
    for question in stored.questions:
        correct = [option.id for option in question.options if option.is_correct]
        answers.append({"question_id": question.id, "option_ids": correct})
    submitted = client.post("/api/quizzes/mid-basics/submit", json={"lang": "ru", "answers": answers})
    assert submitted.status_code == 200
    result = submitted.json()
    assert result["score"] == result["total"] == 8
    assert result["result"]["title"]

    headers = auth_header(client, admin_user.email, "adminpass")
    page = client.get("/api/admin/quizzes?page=1&page_size=20", headers=headers)
    assert page.status_code == 200
    payload = page.json()
    assert payload["total"] == 100
    assert len(payload["items"]) == 20
    assert payload["page"] == 1

    again = seed_mlbb_quizzes(db_session.connection())
    db_session.commit()
    assert again == 0
