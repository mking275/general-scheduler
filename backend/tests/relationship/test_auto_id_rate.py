"""T036 [US2] — auto-ID + soft-confirm RATE audit (build-time proxy for SC-004).

Measures the auto-identify+soft-confirm rate on matched single-contact numbers
across the synthetic corpus. This is the BUILD-TIME proxy only: by construction
every exact single-contact-match number auto-IDs and every non-single-match
falls back to a neutral prompt with no name spoken. The >=90% figure on *real*
audited pilot data is a Pilot-Activation gate (M2), NOT this build.
"""
from backend.models import ResolutionOutcome
from backend.relationship.identity_resolver import IdentityResolver
from backend.tests.relationship.fixtures.ezyvet_dirty_corpus import build_corpus

CLINIC = "clinic-t036-autoid"


def _measure(repo):
    corpus = build_corpus(clinic_id=CLINIC)
    corpus.seed_into_repo(repo)
    resolver = IdentityResolver(repo)
    ak = corpus.answer_key

    single_total = single_auto_id = 0
    nonsingle_total = nonsingle_named = 0
    for phone, spec in ak["phone_lookups"].items():
        result = resolver.resolve(CLINIC, phone, "phone")
        auto = resolver.auto_id_response(result)
        named = auto["mode"] == "soft_confirm_by_name"
        if spec["match_kind"] == "single":
            single_total += 1
            if named and result.outcome == ResolutionOutcome.RESOLVED_SINGLE:
                single_auto_id += 1
        else:                                     # multi | none
            nonsingle_total += 1
            if named:                             # a name spoken here would be a leak
                nonsingle_named += 1
    rate = single_auto_id / single_total if single_total else 0.0
    return {"single_total": single_total, "single_auto_id": single_auto_id,
            "nonsingle_total": nonsingle_total, "nonsingle_named": nonsingle_named,
            "rate": rate}


def test_t036_every_single_match_auto_ids(repo):
    m = _measure(repo)
    assert m["single_total"] > 0
    assert m["single_auto_id"] == m["single_total"]           # 100% of single matches
    assert m["rate"] == 1.0                                    # build-time proxy


def test_t036_no_name_spoken_on_nonsingle_match(repo):
    m = _measure(repo)
    assert m["nonsingle_total"] > 0
    assert m["nonsingle_named"] == 0                           # neutral fallback, no name


def test_t036_email_single_match_never_auto_ids(repo):
    # even a single email match must NOT auto-ID (only exact phone can, R1)
    build_corpus(clinic_id=CLINIC).seed_into_repo(repo)
    resolver = IdentityResolver(repo)
    result = resolver.resolve(CLINIC, "jane.alvarez@example.com", "email")
    auto = resolver.auto_id_response(result)
    assert auto["mode"] == "neutral_prompt"
    assert result.outcome != ResolutionOutcome.RESOLVED_SINGLE
