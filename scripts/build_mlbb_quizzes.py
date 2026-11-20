"""Rebuild app/data/mlbb_quizzes.json from the markdown tests.

Usage:
  python scripts/build_mlbb_quizzes.py C:\\Projects\\moba-universe-docs\\tests
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\Projects\moba-universe-docs\tests")


def load_parser():
    path = ROOT / "app" / "quiz_import.py"
    spec = importlib.util.spec_from_file_location("quiz_import", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def main() -> None:
    quizzes = load_parser().load_mlbb_folder(SOURCE)
    questions = sum(len(quiz["questions"]) for quiz in quizzes)
    destination = ROOT / "app" / "data" / "mlbb_quizzes.json"
    destination.write_text(json.dumps(quizzes, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(quizzes)} tests, {questions} questions -> {destination}")


if __name__ == "__main__":
    main()
