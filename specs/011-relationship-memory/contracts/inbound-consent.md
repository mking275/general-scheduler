# 011 Contract — Inbound Webhook Seam & Consent/Opt-Out Registry

Formalizes 010's `shims/consent_shim.py` (T008) into a real registry, and builds the **net-new inbound intake path** the opt-out story depends on (`sms_gateway.py` is outbound-only today). Sim-mode like everything else in 010.

---

## I1 — Inbound webhook seam (greenfield)

```python
@dataclass
class InboundMessage:
    channel: Literal["sms","voice_dtmf","email","portal"]
    from_identifier: str          # raw; normalized on ingest, feeds the resolver
    body: str
    received_at: datetime

@dataclass
class InboundResult:
    matched_keyword: Optional[Literal["STOP","START","HELP"]]
    action_taken: Literal["opt_out_recorded","opt_in_recorded","routed_to_staff","none"]

async def handle_inbound(msg: InboundMessage) -> InboundResult: ...
```

- The webhook endpoint is the prerequisite for a revocation to be *received* (discover surprise #4). In sim-mode a test harness posts `InboundMessage`s; a live Twilio inbound webhook slots in behind the same seam.
- Keyword table is config (`config/relationship/inbound_keywords.<locale>.yaml`, TCPA STOP/START/HELP).
- A message that is **neither STOP nor a recognized keyword** → `routed_to_staff`, **never auto-actioned** (edge case).
- Every inbound persists an `inbound_message` row (append-only); the `received_at`→staff-visible clock is SC-006 (≤60 s in ≥99%).

## I2 — Consent registry (upgrades the T008 shim)

```python
@dataclass
class ConsentDecision:                # shape preserved from consent_shim.py (T008)
    allowed: bool
    reason: str
    party_id: str
    channel: str
    purpose: str = ""

async def consent_check(party_id: str, channel: str, purpose: str = "") -> ConsentDecision:
    """Consulted by ChannelRouter.route_message()/deliver() BEFORE any Vera-initiated outbound
       (C3 condition 3). DENY if the (contact, channel) opt-out is on record."""

def record_opt_out(party_id: str, channel: str, *, source: str,
                   keyword: str | None = None, inbound_message_id: str | None = None) -> None: ...
def record_opt_in(party_id: str, channel: str, *, source: str) -> None: ...
```

- Writes `contact_consent` (current state, one row per `(party_id, channel)`) **and** an append-only `consent_event` (revocable + reversible audit trail, FR-021).
- **Opt-out suppresses Vera-initiated outbound only** on the covered channel(s), honored across every channel it covers (FR-022, SC-002). It does **not** gate inbound service.
- **Opted-out client who initiates contact is still served**, subject to the standard AI + recording disclosure (FR-023, clarification) — consent governs contact, not service on request. The disclosure is **emitted/persisted via 010's existing `consent_record` path** (010 T033 — disclosure text + timestamp), wired by T025 and verified by T035; it is not a bare assertion (M6).
- Current state is staff-visible (FR-024); the `consent_event` trail backs the audit surface.

## I3 — Flow: inbound STOP → suppression (SC-002/006)

```
Twilio/sim inbound → handle_inbound()               # I1
  → resolve from_identifier to party_id           # identity-resolution R1
  → matched_keyword == "STOP"
    → record_opt_out(party_id, channel, source="inbound_stop", keyword="STOP", inbound_message_id=…)
    → confirm to sender + reflect in staff consent state   # ≤60 s (SC-006)
Later: any Vera-initiated outbound → consent_check() returns DENY → send suppressed  # (SC-002)
Later: same contact calls/messages IN → served with disclosure                        # (FR-023)
```

If the STOP arrives from a number that resolves to **multiple** contacts (shared line), the opt-out is recorded against the resolved-or-disambiguated contact; an unresolved multi-match routes to staff rather than opting out the wrong party (privacy-safe default).
