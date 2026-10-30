import pytest

from app.domain.intent import parse_intent


@pytest.mark.parametrize(
    ("text", "clean", "category"),
    [
        ("Buy milk in category Work.", "Buy milk", "Work"),
        ("Buy milk, in category Work", "Buy milk", "Work"),
        ("Buy milk in the category Home.", "Buy milk", "Home"),
        ("Buy milk. Categorize as Shopping.", "Buy milk", "Shopping"),
        ("Buy milk categorise as shopping", "Buy milk", "shopping"),
        ("Categorize this as Work: call the dentist", "call the dentist", "Work"),
        ("In category Work, send the report", "send the report", "Work"),
        ("In category Work. Send the report.", "Send the report.", "Work"),
        ("Call mom IN CATEGORY family", "Call mom", "family"),
        ("Pay rent in category Home Budget.", "Pay rent", "Home Budget"),
        ("Fix bug in category Work and then lunch", "Fix bug and then lunch", "Work"),
    ],
)
def test_category_phrases(text, clean, category):
    assert parse_intent(text) == (clean, category)


@pytest.mark.parametrize(
    "text",
    [
        "Buy milk",
        "",
        "   ",
        "My favorite category is shoes",
        "Remember the category theory book",
        "This is in a different category of problem",
        "We should categorize everything later",
        "Buy milk in category",
        "Buy milk in category.",
    ],
)
def test_no_category(text):
    assert parse_intent(text) == (text.strip(), None)
