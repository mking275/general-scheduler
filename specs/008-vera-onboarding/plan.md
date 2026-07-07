# Feature 008 — Vera Onboarding: Implementation Plan

## Technical Context

### Backend Stack
- **Python 3.11** + **FastAPI** (all routes in `backend/main.py`)
- **SQLite** via stdlib `sqlite3` — no ORM, all raw SQL
- **Pydantic v2** models in `backend/models.py`
- **Agents** in `backend/agents/` — pure Python heuristics, no LLM calls
- **Repository pattern** — all DB operations in dedicated repository files

### Frontend Stack
- **Next.js 16** (App Router) — pages in `frontend/src/app/`
- **TypeScript** throughout
- **Vanilla CSS** — no Tailwind; custom properties + media queries
- **Lucide icons** for all iconography

### Streaming
- **FastAPI SSE** via `StreamingResponse` with `media_type="text/event-stream"`
- **EventSource** API on frontend; no external WebSocket library

---

## Performance Goals

| Interaction | Target | Method |
|---|---|---|
| `/welcome` page load | < 1s | Static content, no auth gate |
| Typewriter start | < 100ms from load | requestAnimationFrame loop |
| Streaming first byte | < 2s from upload | SSE + immediate partial yield |
| Replace animation complete | < 3s | CSS keyframe (practiceDissolve) |
| Magic link delivery | < 60s | Console delivery in demo scope |
| Full onboarding end-to-end | < 20 min | Guided flow, minimal friction |

---

## Constitution Check

| Principle | Status | Notes |
|---|---|---|
| Every agent action logged in `VERA (Module): action` format | ✅ Pass | `_log()` method on OnboardingAgent; all returned in `verbose_log` |
| All scheduling decisions through agent pipeline | ✅ Pass | No direct DB writes; all writes via `OnboardingAgent` methods |
| SQLite only, no external services | ✅ Pass | `onboarding_repository.py` uses stdlib sqlite3 |
| Every UI element has clear role owner | ✅ Pass | Onboarding phases gated by persona_role |
| Each feature independently deployable | ✅ Pass | All onboarding routes prefixed `/api/onboarding/`; UI at `/welcome` + `/onboarding` |
| Vera is Chief of Staff — VERA_PROFESSIONAL_BOUNDARIES in all agents | ✅ Pass | Constant defined in `models.py`; imported in all 3 new agents |

### Complexity Deviation — 6 New Tables
**Justification**: The onboarding feature requires session state, magic-link auth, staged document extraction (not committed until confirmed), logo asset management, training signal logging, and entity-level confirmation tracking. These concerns are distinct and non-overlapping; collapsing them into fewer tables would require unsafe JSON blobs for relational data (e.g., per-entity confidence scores). Six tables is the minimum normalized schema.

---

## Project Structure — New Files

```
backend/
├── onboarding_repository.py      # All 6-table DB ops
├── agents/
│   ├── onboarding_agent.py       # Chief of Staff onboarding orchestrator
│   ├── practice_builder_agent.py # Free-text + URL parser (heuristics)
│   └── document_parser_agent.py  # CSV/XLSX/PDF/image extraction
└── uploads/                      # Staging dir for uploaded documents

frontend/src/
├── app/
│   ├── welcome/
│   │   └── page.tsx              # Phase 0 welcome with typewriter
│   └── onboarding/
│       ├── page.tsx              # Main onboarding shell
│       └── onboarding.css        # Full CSS for all onboarding UI
└── components/
    └── onboarding/
        ├── VeraChat.tsx           # Conversation panel
        ├── LivePanel.tsx          # Practice preview panel
        ├── RoleSelector.tsx       # 4-option role identification
        ├── MagicLinkPrompt.tsx    # Email + magic link send
        ├── DocumentDropZone.tsx   # File upload (desktop drag + mobile picker)
        ├── ExtractionStream.tsx   # SSE entity stream client
        ├── LogoConfirmation.tsx   # Logo display + confirm
        └── ReplaceAnimation.tsx   # Dissolve transition component

specs/008-vera-onboarding/
├── plan.md                        # This file
├── research.md
├── data-model.md
├── tasks.md
└── contracts/
    └── onboarding-api.md
```
