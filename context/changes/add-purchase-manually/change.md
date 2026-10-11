---
change_id: add-purchase-manually
title: Add purchase manually
status: implementing
created: 2026-10-11
updated: 2026-10-11
archived_at: null
---

## Notes

### External research: Polish consumer protections

- A commercial guarantee is voluntary and its period is set by the guarantor. If no period is specified, UOKiK and the European Consumer Centre state that it is presumed to last two years from delivery.
- The seller's statutory responsibility for non-conformity is a separate protection, generally lasting two years from delivery. It should not be conflated with a product's commercial guarantee.
- Product implication: capture the commercial guarantee terms or end date from the user or supporting document; do not present statutory seller responsibility as the guarantee end date. The required-fields decision remains open.

Sources:
- UOKiK, [Gwarancja](https://prawakonsumenta.uokik.gov.pl/reklamacja/gwarancja/)
- Europejskie Centrum Konsumenckie, [Niezgodność towaru z umową a gwarancja](https://konsument.gov.pl/niezgodnosc-towaru-z-umowa-a-gwarancja-reklamacje/)

### S-01 implementation check

- **Verdict:** The PDF flow is correct for S-01's planned scope. The warranty end date is optional and user-entered; preview does not infer a guarantee period, and save persists the supplied date without calculating a default. The original PDF remains available as supporting documentation.
- **Boundary:** This does not implement a complete warranty-status calculation. UOKiK notes that qualifying replacement or significant repair can restart the guarantee period, while other covered service cases can extend it. Keep those rules for a later warranty-logic slice; do not interpret statutory seller responsibility as the commercial guarantee date.
- **Verification:** `uv run pytest tests/test_pdf_purchase_flow.py` — 11 passed.

Source: UOKiK, [Gwarancja](https://prawakonsumenta.uokik.gov.pl/reklamacja/gwarancja/).
