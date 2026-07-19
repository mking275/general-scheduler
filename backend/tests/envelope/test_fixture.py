"""Feature 009 — T005 synthetic fixture acceptance.

- emits complete + partial + delta variants deterministically from a seed;
- the partial variant omits the attachments/imaging category;
- the answer key states each practice's true AR/invoice/payment totals, which
  records are unusable, which owners are duplicates, and which lookups are
  single- vs multi-match — so a false "complete", a missed AR variance, and a
  false-positive auto-ID are each detectable.
"""
from backend.tests.envelope.fixtures.ezyvet_synthetic_export import (
    generate_batch, generate_delta_export, generate_practice_export,
)


def test_variants_deterministic_from_seed():
    a = generate_practice_export("p1", seed=7, variant="complete")
    b = generate_practice_export("p1", seed=7, variant="complete")
    assert a.raw_bytes() == b.raw_bytes()
    assert a.checksum() == b.checksum()
    # different seed -> different bytes
    c = generate_practice_export("p1", seed=8, variant="complete")
    assert c.checksum() != a.checksum()


def test_complete_has_all_six_categories():
    exp = generate_practice_export("p1", seed=7, variant="complete")
    assert exp.answer_key.categories_present == [
        "attachments_imaging", "communications", "configuration",
        "invoicing_billing_payments", "patient_client", "scheduling",
    ]
    assert exp.answer_key.categories_absent == []


def test_partial_omits_attachments():
    exp = generate_practice_export("p1", seed=7, variant="partial")
    assert "attachments" not in exp.entities
    assert "attachments_imaging" in exp.answer_key.categories_absent
    assert "attachments_imaging" not in exp.answer_key.categories_present


def test_delta_carries_only_attachments():
    delta = generate_delta_export("p1", seed=7)
    assert list(delta.entities.keys()) == ["attachments"]
    assert delta.entities["attachments"]  # non-empty
    assert delta.answer_key.categories_present == ["attachments_imaging"]


def test_answer_key_financials_match_delivered_data():
    exp = generate_practice_export("p1", seed=7, variant="complete", planted="clean")
    ak = exp.answer_key
    delivered_ar = round(sum(a["balance"] for a in exp.entities["ar_balances"]), 2)
    assert ak.ar_balance_total == delivered_ar
    assert ak.invoice_count == len(exp.entities["invoices"])
    assert ak.payment_total == round(sum(p["amount"] for p in exp.entities["payments"]), 2)
    # a clean practice reconciles: reported == delivered, no variance
    assert ak.reported_ar_total == ak.ar_balance_total
    assert ak.has_planted_ar_variance is False
    assert ak.ar_variance == 0.0


def test_planted_ar_variance_is_detectable():
    exp = generate_practice_export("p1", seed=7, variant="complete", planted="ar_variance")
    ak = exp.answer_key
    assert ak.has_planted_ar_variance is True
    assert ak.ar_variance != 0.0
    # the source reports MORE AR than what transferred (the Digitail gap)
    assert ak.reported_ar_total > ak.ar_balance_total


def test_dirty_practice_breaches_floor():
    exp = generate_practice_export("p1", seed=7, variant="complete", planted="dirty")
    ak = exp.answer_key
    assert ak.below_floor is True
    assert ak.usable_record_share < 0.80
    assert len(ak.unusable_record_ids) > 0


def test_clean_practice_above_floor():
    exp = generate_practice_export("p1", seed=7, variant="complete", planted="clean")
    assert exp.answer_key.below_floor is False
    assert exp.answer_key.usable_record_share >= 0.80


def test_identity_single_vs_multi_match_labeled():
    exp = generate_practice_export("p1", seed=7, variant="complete")
    ak = exp.answer_key
    # planted duplicate + collision -> at least one multi-match phone exists
    assert ak.multi_match_phones, "expected a planted shared-phone multi-match"
    # every multi-match phone reaches >1 distinct client; single reaches exactly 1
    for ph in ak.multi_match_phones:
        assert len(ak.shared_phone_groups[ph]) > 1
    for ph in ak.single_match_phones:
        assert len(ak.shared_phone_groups[ph]) == 1
    assert ak.duplicate_owner_client_ids  # a known duplicate set for false-positive detection


def test_batch_has_exactly_one_variance_one_dirty_one_partial():
    batch = generate_batch(n=23)
    assert len(batch) == 23
    variance = [e for e in batch if e.answer_key.has_planted_ar_variance]
    dirty = [e for e in batch if e.answer_key.below_floor]
    partial = [e for e in batch if e.variant == "partial"]
    assert len(variance) == 1
    assert len(dirty) == 1
    assert len(partial) == 1
    # a blocked/held practice does not remove the others; most are clean-complete
    clean = [e for e in batch if e.variant == "complete"
             and not e.answer_key.has_planted_ar_variance
             and not e.answer_key.below_floor]
    assert len(clean) == 20
