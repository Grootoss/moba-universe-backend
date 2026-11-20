"""Insert the bundled MLBB quizzes. Existing slugs are left untouched."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection

DATA_PATH = Path(__file__).resolve().parent / "data" / "mlbb_quizzes.json"


def seed_mlbb_quizzes(connection: Connection) -> int:
    quizzes = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    inserted = 0
    for quiz in quizzes:
        exists = connection.execute(
            text("SELECT id FROM quizzes WHERE slug = :slug"),
            {"slug": quiz["slug"]},
        ).scalar()
        if exists:
            continue
        quiz_id = connection.execute(
            text(
                """
                INSERT INTO quizzes (slug, status, game, role, cover_image)
                VALUES (:slug, :status, :game, :role, :cover)
                RETURNING id
                """
            ),
            {
                "slug": quiz["slug"],
                "status": quiz["status"],
                "game": quiz["game"],
                "role": quiz["role"],
                "cover": quiz["cover_image"],
            },
        ).scalar_one()
        for lang, copy in quiz["translations"].items():
            connection.execute(
                text(
                    """
                    INSERT INTO quiz_translations (quiz_id, lang, title, description)
                    VALUES (:quiz_id, :lang, :title, :description)
                    """
                ),
                {
                    "quiz_id": quiz_id,
                    "lang": lang,
                    "title": copy["title"],
                    "description": copy["description"],
                },
            )
        for question_index, question in enumerate(quiz["questions"]):
            question_id = connection.execute(
                text(
                    """
                    INSERT INTO quiz_questions (quiz_id, sort_order, image)
                    VALUES (:quiz_id, :sort_order, :image)
                    RETURNING id
                    """
                ),
                {"quiz_id": quiz_id, "sort_order": question_index, "image": question["image"]},
            ).scalar_one()
            for lang, copy in question["translations"].items():
                connection.execute(
                    text(
                        """
                        INSERT INTO quiz_question_translations
                            (question_id, lang, prompt, explanation)
                        VALUES (:question_id, :lang, :prompt, :explanation)
                        """
                    ),
                    {
                        "question_id": question_id,
                        "lang": lang,
                        "prompt": copy["prompt"],
                        "explanation": copy["explanation"],
                    },
                )
            for option_index, option in enumerate(question["options"]):
                option_id = connection.execute(
                    text(
                        """
                        INSERT INTO quiz_options (question_id, sort_order, is_correct)
                        VALUES (:question_id, :sort_order, :is_correct)
                        RETURNING id
                        """
                    ),
                    {
                        "question_id": question_id,
                        "sort_order": option_index,
                        "is_correct": option["is_correct"],
                    },
                ).scalar_one()
                for lang, copy in option["translations"].items():
                    connection.execute(
                        text(
                            """
                            INSERT INTO quiz_option_translations (option_id, lang, text)
                            VALUES (:option_id, :lang, :text)
                            """
                        ),
                        {"option_id": option_id, "lang": lang, "text": copy["text"]},
                    )
        for result_index, result in enumerate(quiz["results"]):
            result_id = connection.execute(
                text(
                    """
                    INSERT INTO quiz_results (quiz_id, sort_order, min_correct, max_correct)
                    VALUES (:quiz_id, :sort_order, :min_correct, :max_correct)
                    RETURNING id
                    """
                ),
                {
                    "quiz_id": quiz_id,
                    "sort_order": result_index,
                    "min_correct": result["min_correct"],
                    "max_correct": result["max_correct"],
                },
            ).scalar_one()
            for lang, copy in result["translations"].items():
                connection.execute(
                    text(
                        """
                        INSERT INTO quiz_result_translations (result_id, lang, title, body)
                        VALUES (:result_id, :lang, :title, :body)
                        """
                    ),
                    {
                        "result_id": result_id,
                        "lang": lang,
                        "title": copy["title"],
                        "body": copy["body"],
                    },
                )
        inserted += 1
    return inserted
