"""[SHIM upgrade] Feature 010 — T006 ChannelBinding party-model shim
(contract A1), backed by the real 011 identity resolver (T026).

One phone <-> many household members is a live privacy case, so a binding
resolves to a **candidate-party set + verification level + audience scope** —
NOT ``verified: bool`` + ``user_id``. An unknown number yields an ephemeral
party at ``caller_unverified`` scope.

**T026 upgrade (API unchanged):** ``resolve_binding`` now accepts an optional
011 ``IdentityResolver`` + ``clinic_id``; when supplied it resolves against the
real ``contact_identifier`` candidate sets (``IdentityResolver.resolve``), and
``is_shared_line`` becomes the ``LIMIT 1``-kill primitive (>1 candidate on a
shared number). With no resolver bound the fixture ``_REGISTRY`` default is used
unchanged, so 010's isolated shim tests bind exactly as before — no duplicate
module.

Identity-safe disambiguation (FR-005): the dialog matches an open "name on the
account" answer against the candidate set and soft-confirms exactly one party
**without ever enumerating the candidate names aloud**. An unmatched answer
stays unverified. Extracted to core L1 post-pilot.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

VerificationLevel = Literal["none", "soft_confirmed", "strong"]
AudienceScope = Literal["caller_unverified", "client_verified"]


@dataclass
class PartyRef:
    party_id: str
    display_name: str                    # used for MATCHING only, never spoken aloud
    ephemeral: bool = False


@dataclass
class ChannelBinding:
    channel: str
    channel_address: str                 # E.164 for voice
    candidate_parties: list[PartyRef] = field(default_factory=list)
    verification_level: VerificationLevel = "none"
    audience_scope: AudienceScope = "caller_unverified"
    confirmed_party: Optional[PartyRef] = None

    @property
    def is_shared_line(self) -> bool:
        return len(self.candidate_parties) > 1


# Fixture registry: E.164 -> household member party refs. VP-4a owns this live.
_REGISTRY: dict[str, list[PartyRef]] = {
    # A shared household line (>1 candidate) — the privacy case.
    "+15551110001": [
        PartyRef("party-alvarez-jane", "Jane Alvarez"),
        PartyRef("party-alvarez-tom", "Tom Alvarez"),
        PartyRef("party-alvarez-mia", "Mia Alvarez"),
    ],
    # A single-owner line.
    "+15551110002": [PartyRef("party-okafor-sam", "Sam Okafor")],
}

_EPHEMERAL_SEQ = {"n": 0}


def _ephemeral_party() -> PartyRef:
    _EPHEMERAL_SEQ["n"] += 1
    return PartyRef(party_id=f"ephemeral-{_EPHEMERAL_SEQ['n']}",
                    display_name="", ephemeral=True)


def resolve_binding(channel_address: str, channel: str = "voice", *,
                    resolver: Optional[object] = None,
                    clinic_id: Optional[str] = None) -> ChannelBinding:
    """Resolve an inbound number to a candidate-party set. Unknown numbers get
    an ephemeral party at ``caller_unverified`` scope.

    T026: when ``resolver`` (an 011 ``IdentityResolver``) and ``clinic_id`` are
    supplied, the candidate set comes from the real ``contact_identifier`` index
    — never ``LIMIT 1``; a shared number yields >1 candidate and
    ``is_shared_line`` is True. With no resolver the fixture ``_REGISTRY`` path
    (010's default) runs unchanged. Caller-ID alone never grants a verified
    scope: a fresh binding is always ``none`` / ``caller_unverified`` (R5).
    """
    if resolver is not None and clinic_id is not None:
        candidates = _resolver_candidates(resolver, clinic_id, channel_address, channel)
        return ChannelBinding(
            channel=channel, channel_address=channel_address,
            candidate_parties=candidates or [_ephemeral_party()],
            verification_level="none", audience_scope="caller_unverified",
        )

    candidates = _REGISTRY.get(channel_address)
    if not candidates:
        return ChannelBinding(
            channel=channel,
            channel_address=channel_address,
            candidate_parties=[_ephemeral_party()],
            verification_level="none",
            audience_scope="caller_unverified",
        )
    return ChannelBinding(
        channel=channel,
        channel_address=channel_address,
        candidate_parties=list(candidates),
        verification_level="none",
        audience_scope="caller_unverified",
    )


def _resolver_candidates(resolver: object, clinic_id: str, channel_address: str,
                         channel: str) -> list[PartyRef]:
    """Map the real resolver's full candidate set onto shim ``PartyRef``s. The
    resolver never reduces a multi-match, so the shim's ``is_shared_line`` is
    exactly the resolver's ``is_shared_line`` (the ``LIMIT 1`` kill)."""
    result = resolver.resolve(clinic_id, channel_address, "phone", channel=channel)
    return [PartyRef(party_id=c.party_id, display_name=c.display_name)
            for c in result.candidates]


def _normalize(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum() or ch.isspace()).strip()


def disambiguate(binding: ChannelBinding, spoken_name: str) -> ChannelBinding:
    """Match an OPEN "name on the account" answer against the candidate set and
    soft-confirm exactly one party — **never enumerating candidate names**.

    An answer that matches exactly one candidate -> ``soft_confirmed`` +
    ``client_verified``. Zero or ambiguous (>1) matches -> stays unverified.
    """
    answer = _normalize(spoken_name)
    if not answer:
        return binding

    matches: list[PartyRef] = []
    for p in binding.candidate_parties:
        if p.ephemeral or not p.display_name:
            continue
        cand = _normalize(p.display_name)
        cand_tokens = set(cand.split())
        ans_tokens = set(answer.split())
        # Match on full string OR on a shared given/last-name token.
        if answer == cand or answer in cand or (ans_tokens & cand_tokens):
            matches.append(p)

    if len(matches) == 1:
        binding.confirmed_party = matches[0]
        binding.verification_level = "soft_confirmed"
        binding.audience_scope = "client_verified"
    # 0 or >1 matches -> unchanged (stays unverified); no names ever read back.
    return binding
