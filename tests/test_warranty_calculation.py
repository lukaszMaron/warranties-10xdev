from datetime import date

import pytest

from warranties_10xdev import purchases
from warranties_10xdev.purchases import (
    PurchaseInput,
    WarrantyCalculation,
    calculate_warranty,
)


def _purchase(**overrides: object) -> PurchaseInput:
    values: dict[str, object] = {
        "product_name": "Cordless drill",
        "purchase_date": date(2025, 4, 3),
        "purchase_type": "private",
    }
    values.update(overrides)
    return PurchaseInput(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("purchase_date", "purchase_type", "expected_end_date"),
    [
        (date(2024, 4, 3), "private", date(2026, 4, 3)),
        (date(2025, 4, 3), "business", date(2026, 4, 3)),
    ],
)
def test_estimates_end_date_by_purchase_type(
    purchase_date: date,
    purchase_type: str,
    expected_end_date: date,
) -> None:
    result = calculate_warranty(
        _purchase(purchase_date=purchase_date, purchase_type=purchase_type),
        today=date(2026, 1, 1),
    )

    assert result == WarrantyCalculation(expected_end_date, "estimate", "active")


def test_user_end_date_overrides_estimate_without_changing_stored_value() -> None:
    purchase = _purchase(warranty_end_date=date(2028, 6, 30))

    result = calculate_warranty(purchase, today=date(2027, 1, 1))

    assert result == WarrantyCalculation(date(2028, 6, 30), "user", "active")
    assert purchase.warranty_end_date == date(2028, 6, 30)


def test_february_29_estimate_clamps_to_february_28() -> None:
    result = calculate_warranty(
        _purchase(purchase_date=date(2024, 2, 29)),
        today=date(2026, 2, 28),
    )

    assert result == WarrantyCalculation(date(2026, 2, 28), "estimate", "active")


@pytest.mark.parametrize(
    ("today", "expected_status"),
    [(date(2027, 4, 3), "active"), (date(2027, 4, 4), "expired")],
)
def test_end_date_is_inclusive(
    today: date,
    expected_status: str,
) -> None:
    result = calculate_warranty(
        _purchase(warranty_end_date=date(2027, 4, 3)), today=today
    )

    assert result.effective_end_date == date(2027, 4, 3)
    assert result.date_basis == "user"
    assert result.status == expected_status


def test_missing_purchase_has_unknown_warranty_status() -> None:
    assert calculate_warranty(None, today=date(2026, 1, 1)) == WarrantyCalculation(
        None, "unknown", "unknown"
    )


@pytest.mark.parametrize(
    ("purchase_date", "purchase_type", "end_date", "expected_message"),
    [
        (date(2026, 3, 10), "private", None, None),
        (date(2026, 3, 10), "private", date(2027, 6, 1), None),
        (
            date(2026, 3, 10), "business", date(2027, 6, 1),
            "Warranty end date is later than the estimated 1-year business warranty (2027-03-10).",
        ),
        (date(2026, 3, 10), "private", date(2028, 3, 10), None),
        (date(2026, 3, 10), "business", date(2027, 3, 10), None),
        (
            date(2026, 3, 10), "private", date(2028, 3, 11),
            "Warranty end date is later than the estimated 2-year private warranty (2028-03-10).",
        ),
        (
            date(2026, 3, 10), "private", date(2026, 3, 9),
            "Warranty end date is earlier than the purchase date.",
        ),
        (date(2026, 3, 10), "private", date(2026, 3, 10), None),
        (date(2024, 2, 29), "business", date(2025, 2, 28), None),
        (
            date(2024, 2, 29), "business", date(2025, 3, 1),
            "Warranty end date is later than the estimated 1-year business warranty (2025-02-28).",
        ),
    ],
)
def test_manual_warranty_warnings_follow_purchase_type_estimate(
    purchase_date: date,
    purchase_type: str,
    end_date: date | None,
    expected_message: str | None,
) -> None:
    # Research decision 3: unusual dates warn; the threshold follows the purchase type.
    purchase = _purchase(
        purchase_date=purchase_date,
        purchase_type=purchase_type,
        warranty_end_date=end_date,
    )

    warnings = purchases.warranty_end_date_warnings(purchase)

    assert warnings == (
        {"warranty_end_date": expected_message} if expected_message is not None else {}
    )
    assert purchase.warranty_end_date == end_date