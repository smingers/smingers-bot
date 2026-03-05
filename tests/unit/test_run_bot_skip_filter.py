import pytest

from run_bot import should_skip_question
from src.utils.metaculus_api import MetaculusQuestion


def make_question(title: str) -> MetaculusQuestion:
    return MetaculusQuestion(
        id=1,
        question_id=1,
        title=title,
        description="",
        resolution_criteria="",
        fine_print="",
        background_info="",
        question_type="binary",
        created_at="",
        open_time=None,
        scheduled_close_time=None,
        scheduled_resolve_time=None,
        status="open",
    )


@pytest.mark.parametrize(
    "title,expected",
    [
        (
            "Will the community prediction be higher than X by Y?",
            True,
        ),
        (
            "will the community prediction be higher by more than 5%?",
            True,
        ),
        (
            "   Will the community prediction be higher by more than 5%?",
            True,
        ),
        (
            "Will the community prediction be higher",
            True,
        ),
        (
            "What will the community prediction be by the close date?",
            False,
        ),
        (
            "Community prediction question about something else",
            False,
        ),
    ],
)
def test_should_skip_question_prefix(title: str, expected: bool) -> None:
    q = make_question(title)
    assert should_skip_question(q) is expected
