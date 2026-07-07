# Feature 008 — Vera Onboarding: Task List

## Coverage: FR-001 through FR-042 + all sub-requirements

---

## Phase 1 — Setup

- [x] T001 [P1] DB schema — create all 6 onboarding tables via `onboarding_repository.py:init_db()` (`backend/onboarding_repository.py`)
- [x] T002 [P1] Pydantic models — append all onboarding models + enums + constants to `backend/models.py`
- [x] T003 [P1] CSS + directory structure — create `frontend/src/app/onboarding/onboarding.css` with all custom properties, layout classes, animations, and component styles; create `frontend/src/components/onboarding/` directory

---

## Phase 2 — Foundational

- [x] T004 [P1] `OnboardingRepository` — full class with all 15 DB methods in `backend/onboarding_repository.py`
- [x] T005 [P1] Core onboarding routes (session CRUD + magic link) — POST/GET/PATCH session endpoints + POST magic-link in `backend/main.py`
- [x] T006 [P1] `OnboardingAgent` — full class with 9 handler methods + `_log()` + `_get_first_action_targets()` in `backend/agents/onboarding_agent.py`
- [x] T007 [P1] `PracticeBuilderAgent` — `parse_free_text()` + `parse_url()` heuristics in `backend/agents/practice_builder_agent.py`
- [x] T008 [P1] `VeraChat` component — message list, typewriter, skip, input bar, phase-based component rendering in `frontend/src/app/onboarding/page.tsx` (integrated into shell)
- [x] T009 [P1] `LivePanel` component — practice header, schedule grid, room tabs, \"Make it live →\" CTA in `frontend/src/app/onboarding/page.tsx` (integrated into shell)

---

## Phase 3 — US1: Demo to Live (P1 MVP)

- [x] T010 [P1] [US1] Welcome page — typewriter intro at 15ms/char, Skip button, \"Watch the demo →\" button in `frontend/src/app/welcome/page.tsx` (FR-001, FR-002, FR-003)
- [x] T011 [P1] [US1] `RoleSelector` component — 4 option cards with PATCH session on select (FR-007a, FR-007b, FR-007c)
- [x] T012 [P1] [US1] `MagicLinkPrompt` component — email input, send button, skip link (FR-008a, FR-008b, FR-008c, FR-008d)
- [x] T013 [P1] [US1] Free-text practice name parser — extract name + city/state from Q1 input in `OnboardingAgent.handle_practice_name()` (FR-008, FR-009)
- [x] T014 [P1] [US1] Onboarding shell page — phase routing, session init, magic_token param handling, LivePanel + VeraChat layout in `frontend/src/app/onboarding/page.tsx` (FR-004 through FR-007)
- [x] T015 [P1] [US1] Practice name → live panel header update — PATCH session + LivePanel prop update within 1s (FR-008)
- [x] T016 [P1] [US1] Open prompt (Q2) — free-text + file drop + link paste affordances in VeraChat phase routing (FR-010, FR-011, FR-012, FR-013, FR-014, FR-015)
- [x] T017 [P1] [US1] `ReplaceAnimation` — CSS practiceDissolve, 3s animation via `replacing` state + `replace-container replacing` class (FR-028, FR-029, FR-030)
- [x] T018 [P1] [US1] Go-live route + first action targets — POST `/api/onboarding/go-live` handler, Clinic + Resource creation, role-appropriate targets (FR-028 through FR-033)

---

## Phase 4 — US2: Document Intelligence (P1)

- [x] T019 [P1] [US2] `DocumentParserAgent` — classify, parse_csv, parse_xlsx, parse_pdf, parse_image, assign_confidence in `backend/agents/document_parser_agent.py` (FR-021, FR-022, FR-023, FR-025, FR-026, FR-027)
- [x] T020 [P1] [US2] Upload route — POST `/api/onboarding/upload`, 25MB check, MIME validation, staging storage in `backend/main.py` (FR-021, FR-021a, FR-021b)
- [x] T021 [P1] [US2] SSE extract-stream route — GET `/api/onboarding/extract-stream/{document_id}`, 30s cap, entity streaming in `backend/main.py` (FR-022a, FR-022b, FR-023)
- [x] T022 [P1] [US2] Confirm-entity route — POST `/api/onboarding/confirm-entity/{entity_id}`, correction logging in `backend/main.py` (FR-024, FR-025, FR-026, FR-027)
- [x] T023 [P1] [US2] Entity stream UI — EventSource client, entity list with typewriter reveal, confidence badges, inline confirm/rename buttons in `page.tsx` (FR-022a, FR-023, FR-024, FR-027)
- [x] T024 [P1] [US2] Drag-and-drop drop zone — desktop drag overlay, mobile file picker, 25MB pre-flight, upload + stream mount in `page.tsx` (FR-011, FR-021, FR-021a, FR-021b)

---

## Phase 5 — US3: Logo Scraping (P1)

- [x] T025 [P1] [US3] Logo scraping logic — httpx + BeautifulSoup4 cascade (og:image→favicon→header_img→monogram) in `main.py` + helper functions (FR-016, FR-019)
- [x] T026 [P1] [US3] Scrape-logo + confirm-logo routes — POST `/api/onboarding/scrape-logo` + POST `/api/onboarding/confirm-logo/{logo_asset_id}` in `backend/main.py` (FR-017, FR-018, FR-020)
- [x] T027 [P1] [US3] Logo confirm UI — show scraped logo + monogram, update LivePanel header simultaneously, 3-button confirm UI in `page.tsx` (FR-017, FR-018, FR-019, FR-020)

---

## Phase 6 — US4: Link Intelligence (P2)

- [x] T028 [P2] [US4] URL detection + scraping in `PracticeBuilderAgent.parse_url()` — Google Maps vs website detection, field extraction (FR-012)
- [x] T029 [P2] [US4] Wire URL path into onboarding chat handler — detect URL in open prompt input, route to scrape pipeline, integrate with logo scraping (FR-012, FR-016)

---

## Phase 7 — US5: Session Resume (P2)

- [x] T030 [P2] [US5] Magic link resume flow in frontend — detect `magic_token` URL param on `/onboarding`, call GET `/api/onboarding/resume/{token}`, restore session state + show Vera summary (FR-035, FR-036, FR-036a)

---

## Phase 8 — US6: Professional Boundary Introduction (P2)

- [x] T031 [P2] [US6] Post-Replace boundary statement — `OnboardingAgent.handle_post_replace_intro()` returns boundary statement before first operational message; wired into go-live response (FR-037, FR-038, FR-039, FR-040, FR-041, FR-042)

---

## Phase 9 — Polish

- [x] T032 [P1] Verbose log integration — all onboarding agent actions appear in Verbose Log panel with `VERA (Onboarding): action` format via `VerboseLogPanel.tsx` (FR-006, Constitution Rule 1)
- [x] T033 [P1] Mobile CSS — 768px breakpoint: flex-col layout, tab-bar, tab-btn, tab-content; touch file picker (FR-021b, spec Assumption 7)
- [x] T034 [P1] Activation route — POST `/api/onboarding/activation` records first real booking timestamp (FR-033)
- [x] T035 [P1] `requirements.txt` — add openpyxl, pdfplumber, pytesseract, httpx, beautifulsoup4, python-multipart
- [x] T036 [P1] `uploads/` staging directory — create `backend/uploads/.gitkeep`; ensure directory is created on startup in `onboarding_repository.init_db()`

---

## Implementation Complete

All T001–T036 tasks implemented and verified:
- Python syntax: ✅ all 4 new files clean
- TypeScript: ✅ 0 errors
- Live smoke test: ✅ session created, VERA (Onboarding) log confirmed
- All 12 API routes registered in main.py
- VERA_PROFESSIONAL_BOUNDARIES present in all 3 agent files
