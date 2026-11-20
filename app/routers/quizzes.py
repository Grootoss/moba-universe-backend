"""Public quizzes and the admin editor that fills them."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import require_admin
from app.models import (
    Quiz,
    QuizOption,
    QuizOptionTranslation,
    QuizQuestion,
    QuizQuestionTranslation,
    QuizResult,
    QuizResultTranslation,
    QuizTranslation,
    User,
)
from app.schemas import (
    QuizAdminCardOut,
    QuizAdminOptionOut,
    QuizAdminOut,
    QuizAdminPageOut,
    QuizAdminQuestionOut,
    QuizAdminResultOut,
    QuizCardOut,
    QuizCopyIn,
    QuizOptionPublicOut,
    QuizOptionReviewOut,
    QuizOptionTextIn,
    QuizPreviewOut,
    QuizPublicOut,
    QuizQuestionPublicOut,
    QuizQuestionReviewOut,
    QuizQuestionTextIn,
    QuizResultTextIn,
    QuizScoreTextOut,
    QuizSubmitIn,
    QuizSubmitOut,
    QuizWriteIn,
)

public_router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])
admin_router = APIRouter(prefix="/api/admin/quizzes", tags=["admin-quizzes"])


def _pick(rows, lang: str, field: str) -> str:
    by_lang = {row.lang: row for row in rows}
    row = by_lang.get(lang) or by_lang.get("ru") or by_lang.get("en")
    if row is None:
        return ""
    return getattr(row, field) or ""


def _lang(value: str | None) -> str:
    return "en" if value == "en" else "ru"


def _load_options():
    return (
        selectinload(Quiz.translations),
        selectinload(Quiz.questions).selectinload(QuizQuestion.translations),
        selectinload(Quiz.questions).selectinload(QuizQuestion.options).selectinload(QuizOption.translations),
        selectinload(Quiz.results).selectinload(QuizResult.translations),
    )


def _get_quiz(db: Session, quiz_id: int) -> Quiz:
    quiz = db.scalar(select(Quiz).where(Quiz.id == quiz_id).options(*_load_options()))
    if quiz is None:
        raise HTTPException(status_code=404, detail="Test not found")
    return quiz


def _published(db: Session, slug: str) -> Quiz:
    quiz = db.scalar(
        select(Quiz)
        .where(Quiz.slug == slug, Quiz.status == "published")
        .options(*_load_options())
    )
    if quiz is None:
        raise HTTPException(status_code=404, detail="Test not found")
    return quiz


def _role_from_slug(slug: str) -> str:
    for role in ("roam", "mid", "jungle", "exp", "gold"):
        if slug == role or slug.startswith(f"{role}-"):
            return role
    return ""


def _apply_place(quiz: Quiz, data: QuizWriteIn) -> None:
    if data.game:
        quiz.game = data.game.strip() or "mlbb"
    elif not quiz.game:
        quiz.game = "mlbb"
    if data.role:
        quiz.role = data.role.strip()
    elif not quiz.role:
        quiz.role = _role_from_slug(quiz.slug)
    if data.cover_image:
        quiz.cover_image = data.cover_image
    elif not quiz.cover_image and quiz.role:
        quiz.cover_image = f"/images/quiz/{quiz.role}-1.svg"


def _replace(quiz: Quiz, data: QuizWriteIn, db: Session) -> None:
    quiz.slug = data.slug
    quiz.status = data.status
    _apply_place(quiz, data)
    quiz.translations.clear()
    quiz.questions.clear()
    quiz.results.clear()
    db.flush()

    for lang, copy in data.translations.items():
        quiz.translations.append(
            QuizTranslation(lang=lang, title=copy.title.strip(), description=copy.description.strip())
        )
    for index, question_in in enumerate(data.questions):
        question = QuizQuestion(sort_order=index, image=question_in.image)
        for lang, text in question_in.translations.items():
            question.translations.append(
                QuizQuestionTranslation(
                    lang=lang,
                    prompt=text.prompt.strip(),
                    explanation=text.explanation.strip(),
                )
            )
        for option_index, option_in in enumerate(question_in.options):
            option = QuizOption(sort_order=option_index, is_correct=option_in.is_correct)
            for lang, label in option_in.translations.items():
                option.translations.append(QuizOptionTranslation(lang=lang, text=label.text.strip()))
            question.options.append(option)
        quiz.questions.append(question)
    for index, band in enumerate(data.results):
        result = QuizResult(
            sort_order=index,
            min_correct=band.min_correct,
            max_correct=band.max_correct,
        )
        for lang, text in band.translations.items():
            result.translations.append(
                QuizResultTranslation(lang=lang, title=text.title.strip(), body=text.body.strip())
            )
        quiz.results.append(result)


def _ensure_slug(db: Session, slug: str, quiz_id: int | None) -> None:
    stmt = select(Quiz.id).where(Quiz.slug == slug)
    if quiz_id is not None:
        stmt = stmt.where(Quiz.id != quiz_id)
    if db.scalar(stmt) is not None:
        raise HTTPException(status_code=409, detail="A test with this slug already exists")


def _admin_out(quiz: Quiz) -> QuizAdminOut:
    return QuizAdminOut(
        id=quiz.id,
        slug=quiz.slug,
        status=quiz.status,
        game=quiz.game or "mlbb",
        role=quiz.role or "",
        cover_image=quiz.cover_image,
        question_count=len(quiz.questions),
        translations={
            row.lang: QuizCopyIn(title=row.title, description=row.description)
            for row in quiz.translations
        },
        questions=[
            QuizAdminQuestionOut(
                image=question.image,
                translations={
                    row.lang: QuizQuestionTextIn(prompt=row.prompt, explanation=row.explanation)
                    for row in question.translations
                },
                options=[
                    QuizAdminOptionOut(
                        is_correct=option.is_correct,
                        translations={
                            row.lang: QuizOptionTextIn(text=row.text) for row in option.translations
                        },
                    )
                    for option in question.options
                ],
            )
            for question in quiz.questions
        ],
        results=[
            QuizAdminResultOut(
                min_correct=band.min_correct,
                max_correct=band.max_correct,
                translations={
                    row.lang: QuizResultTextIn(title=row.title, body=row.body) for row in band.translations
                },
            )
            for band in quiz.results
        ],
    )


def _public_out(quiz: Quiz, lang: str) -> QuizPublicOut:
    questions: list[QuizQuestionPublicOut] = []
    for question in quiz.questions:
        correct_count = sum(1 for option in question.options if option.is_correct)
        questions.append(
            QuizQuestionPublicOut(
                id=question.id,
                image=question.image,
                prompt=_pick(question.translations, lang, "prompt"),
                multiple=correct_count > 1,
                options=[
                    QuizOptionPublicOut(id=option.id, text=_pick(option.translations, lang, "text"))
                    for option in question.options
                ],
            )
        )
    return QuizPublicOut(
        slug=quiz.slug,
        game=quiz.game or "mlbb",
        role=quiz.role or "",
        title=_pick(quiz.translations, lang, "title"),
        description=_pick(quiz.translations, lang, "description"),
        questions=questions,
    )


@public_router.get("", response_model=list[QuizCardOut])
def list_quizzes(
    response: Response,
    lang: str = Query(default="ru"),
    game: str | None = Query(default=None),
    role: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "public, max-age=60"
    language = _lang(lang)
    stmt = select(Quiz).where(Quiz.status == "published")
    if game:
        stmt = stmt.where(Quiz.game == game.strip())
    if role:
        stmt = stmt.where(Quiz.role == role.strip())
    rows = db.scalars(
        stmt.options(selectinload(Quiz.translations), selectinload(Quiz.questions)).order_by(Quiz.id.asc())
    ).all()
    return [
        QuizCardOut(
            slug=quiz.slug,
            game=quiz.game or "mlbb",
            role=quiz.role or "",
            cover_image=quiz.cover_image,
            title=_pick(quiz.translations, language, "title"),
            description=_pick(quiz.translations, language, "description"),
            question_count=len(quiz.questions),
        )
        for quiz in rows
    ]


@public_router.get("/{slug}/preview", response_model=QuizPreviewOut)
def preview_quiz(slug: str, lang: str = Query(default="ru"), db: Session = Depends(get_db)):
    """Indexable start page: title and description, no questions or answers."""
    quiz = _published(db, slug)
    language = _lang(lang)
    return QuizPreviewOut(
        slug=quiz.slug,
        game=quiz.game or "mlbb",
        role=quiz.role or "",
        cover_image=quiz.cover_image,
        title=_pick(quiz.translations, language, "title"),
        description=_pick(quiz.translations, language, "description"),
        question_count=len(quiz.questions),
    )


@public_router.get("/{slug}", response_model=QuizPublicOut)
def get_quiz(slug: str, lang: str = Query(default="ru"), db: Session = Depends(get_db)):
    return _public_out(_published(db, slug), _lang(lang))


@public_router.post("/{slug}/submit", response_model=QuizSubmitOut)
def submit_quiz(slug: str, body: QuizSubmitIn, db: Session = Depends(get_db)):
    quiz = _published(db, slug)
    by_id = {question.id: question for question in quiz.questions}
    seen: set[int] = set()
    selected_by_question: dict[int, set[int]] = {}
    for answer in body.answers:
        if answer.question_id not in by_id:
            raise HTTPException(status_code=400, detail="Unknown question")
        if answer.question_id in seen:
            raise HTTPException(status_code=400, detail="Question answered twice")
        seen.add(answer.question_id)
        question = by_id[answer.question_id]
        allowed = {option.id for option in question.options}
        chosen = set(answer.option_ids)
        if not chosen <= allowed:
            raise HTTPException(status_code=400, detail="Unknown answer")
        selected_by_question[answer.question_id] = chosen

    reviews: list[QuizQuestionReviewOut] = []
    score = 0
    for question in quiz.questions:
        chosen = selected_by_question.get(question.id, set())
        correct_ids = {option.id for option in question.options if option.is_correct}
        correct = chosen == correct_ids and bool(correct_ids)
        if correct:
            score += 1
        reviews.append(
            QuizQuestionReviewOut(
                id=question.id,
                image=question.image,
                prompt=_pick(question.translations, body.lang, "prompt"),
                explanation=_pick(question.translations, body.lang, "explanation"),
                correct=correct,
                options=[
                    QuizOptionReviewOut(
                        id=option.id,
                        text=_pick(option.translations, body.lang, "text"),
                        is_correct=option.is_correct,
                        selected=option.id in chosen,
                    )
                    for option in question.options
                ],
            )
        )

    result = None
    for band in quiz.results:
        if band.min_correct <= score <= band.max_correct:
            result = QuizScoreTextOut(
                title=_pick(band.translations, body.lang, "title"),
                body=_pick(band.translations, body.lang, "body"),
            )
            break
    return QuizSubmitOut(score=score, total=len(quiz.questions), result=result, questions=reviews)


@admin_router.get("", response_model=QuizAdminPageOut)
def admin_list_quizzes(
    _: User = Depends(require_admin),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    total = db.scalar(select(func.count()).select_from(Quiz)) or 0
    quizzes = db.scalars(
        select(Quiz)
        .options(selectinload(Quiz.translations), selectinload(Quiz.questions))
        .order_by(Quiz.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return QuizAdminPageOut(
        items=[
            QuizAdminCardOut(
                id=quiz.id,
                slug=quiz.slug,
                status=quiz.status,
                game=quiz.game or "mlbb",
                role=quiz.role or "",
                title_ru=_pick(quiz.translations, "ru", "title"),
                title_en=_pick(quiz.translations, "en", "title"),
                question_count=len(quiz.questions),
            )
            for quiz in quizzes
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@admin_router.get("/{quiz_id}", response_model=QuizAdminOut)
def admin_get_quiz(quiz_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    return _admin_out(_get_quiz(db, quiz_id))


@admin_router.post("", response_model=QuizAdminOut, status_code=201)
def admin_create_quiz(body: QuizWriteIn, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    _ensure_slug(db, body.slug, None)
    quiz = Quiz(slug=body.slug, status=body.status)
    db.add(quiz)
    db.flush()
    _replace(quiz, body, db)
    db.commit()
    return _admin_out(_get_quiz(db, quiz.id))


@admin_router.put("/{quiz_id}", response_model=QuizAdminOut)
def admin_update_quiz(
    quiz_id: int,
    body: QuizWriteIn,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    quiz = _get_quiz(db, quiz_id)
    _ensure_slug(db, body.slug, quiz.id)
    _replace(quiz, body, db)
    db.commit()
    return _admin_out(_get_quiz(db, quiz.id))


@admin_router.delete("/{quiz_id}", status_code=204)
def admin_delete_quiz(quiz_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise HTTPException(status_code=404, detail="Test not found")
    db.delete(quiz)
    db.commit()
