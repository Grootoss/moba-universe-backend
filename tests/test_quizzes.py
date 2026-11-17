from tests.conftest import auth_header


def _quiz_body(**overrides):
    body = {
        "slug": "roam-basics",
        "status": "published",
        "translations": {
            "ru": {"title": "Основы роума", "description": "Короткий тест по роуму"},
            "en": {"title": "Roam basics", "description": "A short roam quiz"},
        },
        "questions": [
            {
                "image": None,
                "translations": {
                    "ru": {"prompt": "Куда идти после лининга?", "explanation": "Роум помогает линии, которой тяжело."},
                    "en": {"prompt": "Where do you rotate after laning?", "explanation": "The roamer helps the lane that is losing."},
                },
                "options": [
                    {
                        "is_correct": False,
                        "translations": {"ru": {"text": "В фонтан"}, "en": {"text": "To the fountain"}},
                    },
                    {
                        "is_correct": True,
                        "translations": {"ru": {"text": "На слабую линию"}, "en": {"text": "To the losing lane"}},
                    },
                ],
            }
        ],
        "results": [
            {
                "min_correct": 1,
                "max_correct": 1,
                "translations": {
                    "ru": {"title": "Готово", "body": "База роума на месте."},
                    "en": {"title": "Ready", "body": "The roam basics are in place."},
                },
            }
        ],
    }
    body.update(overrides)
    return body


def test_public_quiz_hides_answers_until_submit(client, admin_user):
    headers = auth_header(client, "admin@mobauniverse.com", "adminpass")
    created = client.post("/api/admin/quizzes", json=_quiz_body(), headers=headers)
    assert created.status_code == 201, created.text

    listing = client.get("/api/quizzes?lang=ru")
    assert listing.status_code == 200
    assert listing.json()[0]["title"] == "Основы роума"
    assert listing.json()[0]["question_count"] == 1

    preview = client.get("/api/quizzes/roam-basics/preview?lang=en")
    assert preview.status_code == 200
    assert preview.json()["title"] == "Roam basics"
    assert "questions" not in preview.json()

    public = client.get("/api/quizzes/roam-basics?lang=en")
    assert public.status_code == 200
    payload = public.json()
    assert payload["title"] == "Roam basics"
    assert "is_correct" not in payload["questions"][0]
    assert "explanation" not in payload["questions"][0]
    option_id = payload["questions"][0]["options"][1]["id"]
    question_id = payload["questions"][0]["id"]

    submitted = client.post(
        "/api/quizzes/roam-basics/submit",
        json={"lang": "ru", "answers": [{"question_id": question_id, "option_ids": [option_id]}]},
    )
    assert submitted.status_code == 200, submitted.text
    review = submitted.json()
    assert review["score"] == 1
    assert review["result"]["title"] == "Готово"
    assert review["questions"][0]["correct"] is True
    assert "Роум помогает" in review["questions"][0]["explanation"]


def test_draft_is_hidden_and_twenty_one_questions_are_rejected(client, admin_user):
    headers = auth_header(client, "admin@mobauniverse.com", "adminpass")
    draft = client.post("/api/admin/quizzes", json=_quiz_body(status="draft", slug="draft-roam"), headers=headers)
    assert draft.status_code == 201, draft.text
    assert client.get("/api/quizzes/draft-roam").status_code == 404

    questions = []
    for index in range(21):
        questions.append(
            {
                "image": None,
                "translations": {
                    "ru": {"prompt": f"Вопрос {index}", "explanation": "Пояснение"},
                    "en": {"prompt": f"Question {index}", "explanation": "Explanation"},
                },
                "options": [
                    {"is_correct": True, "translations": {"ru": {"text": "Да"}, "en": {"text": "Yes"}}},
                    {"is_correct": False, "translations": {"ru": {"text": "Нет"}, "en": {"text": "No"}}},
                ],
            }
        )
    rejected = client.post(
        "/api/admin/quizzes",
        json=_quiz_body(slug="too-long", questions=questions, results=[]),
        headers=headers,
    )
    assert rejected.status_code == 422
