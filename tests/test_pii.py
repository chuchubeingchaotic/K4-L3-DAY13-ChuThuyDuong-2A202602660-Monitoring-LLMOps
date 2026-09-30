from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_cccd() -> None:
    cccd_number = "001234567890"
    out = scrub_text(f"Citizen ID: {cccd_number}")
    assert cccd_number not in out
    assert "REDACTED_CCCD" in out


def test_scrub_credit_card() -> None:
    cards = (
        "4111 2222 3333 4444",
        "4111-2222-3333-4444",
        "4111222233334444",
    )
    for card in cards:
        out = scrub_text(f"Payment card: {card}")
        assert card not in out
        assert "REDACTED_CREDIT_CARD" in out


def test_scrub_passport() -> None:
    passport = "B1234567"
    out = scrub_text(f"Passport number: {passport}")
    assert passport not in out
    assert "REDACTED_PASSPORT" in out

