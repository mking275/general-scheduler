# Tasks: General Scheduler Prototype

## Implementation Strategy
- **MVP First**: Complete User Story 1 (Backend API) to ensure the core Neuro-Symbolic pipeline works before building the frontend.
- **Incremental Delivery**: Deliver the backend API, then layer the Next.js frontend over it.
- **Parallel Execution**: Data models, interfaces, and discrete AI agents can be developed in parallel.

## Dependencies
- Phase 1 (Setup) blocks all other phases.
- Phase 2 (Foundational) blocks Phase 3.
- Phase 3 (US1 Backend) blocks Phase 4 (US2 Frontend).

## Phase 1: Setup
- [x] T001 Initialize FastAPI backend project structure in `backend/`
- [x] T002 Initialize Next.js frontend project with Tailwind in `frontend/`

## Phase 2: Foundational
- [x] T003 [P] Create Pydantic data models (`Job`, `Resource`, `TimeBlock`) in `backend/models.py`
- [x] T004 [P] Create `BaseSolver` and `BaseRepository` abstract interfaces in `backend/interfaces.py`
- [x] T005 Create `InMemoryRepository` implementation with mock Vet data in `backend/repository.py`

## Phase 3: User Story 1 - Natural Language Scheduling
**Goal**: System parses unstructured text and schedules a TimeBlock.
**Independent Test**: Submitting `POST /api/schedule` directly via HTTP client returns a successful JSON payload matching the contract.
- [x] T006 [P] [US1] Implement Intake Agent (LLM Parser) in `backend/agents/intake.py`
- [x] T007 [P] [US1] Implement Semantic Matcher (Cosine Similarity) in `backend/agents/matcher.py`
- [x] T008 [US1] Implement Heuristic Solver (Rules Engine) in `backend/solver.py`
- [x] T009 [US1] Implement Dispatch Agent in `backend/agents/dispatch.py`
- [x] T010 [US1] Wire the pipeline into `POST /api/schedule` endpoint in `backend/main.py`

## Phase 4: User Story 2 - Verbose Demonstration Mode
**Goal**: Visually showcase the AI's internal thought process to build trust.
**Independent Test**: Submitting a request in the Chat UI populates the Dashboard and Verbose Logs with API responses.
- [x] T011 [P] [US2] Build Mock Login component in `frontend/components/MockLogin.tsx`
- [x] T012 [P] [US2] Build Chat Input component in `frontend/components/ChatInput.tsx`
- [x] T013 [P] [US2] Build Verbose Log Panel component in `frontend/components/VerboseLog.tsx`
- [x] T014 [US2] Build Schedule Dashboard component in `frontend/components/Dashboard.tsx`
- [x] T015 [US2] Assemble main layout and connect to API in `frontend/app/page.tsx`

## Phase 5: Polish & Cross-Cutting
- [x] T016 Apply Framer Motion micro-animations across frontend components
- [x] T017 Final end-to-end integration testing and frontend/backend alignment
- [x] T018 [P] Configure deployment pipelines (Vercel for Next.js, Render/Fly.io for FastAPI)
