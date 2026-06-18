# Neuro-Symbolic Agentic Scheduler Prototype

This document serves as the detailed design specification for the General Scheduler prototype. It outlines the architecture required to build a hybrid Vector (Neural) and Heuristic (Symbolic) scheduling engine. This document is formatted to be easily ingested by AI coding assistants or Spec Kits for scaffolding.

## Goal Description
Build a "Scheduling API" prototype that implements the generalized data model, contextualized for the **Veterinary Industry**. The system will ingest unstructured natural language requests (e.g., "Need an emergency surgery for a Golden Retriever"), tokenize them into Jobs and Constraints, use vector embeddings for semantic matching (soft constraints), and use a pure Python heuristic solver for validation (hard constraints). The prototype will include a **Streamlit Frontend** for demonstration purposes.

## Proposed Architecture

The prototype will be built as a highly modular Python application.

### 1. Architectural Patterns (Modularity)
To ensure the prototype can easily evolve into a production-grade system, we will strictly enforce separation of concerns using interfaces (Abstract Base Classes in Python):
- **Solver Strategy (`BaseSolver`):** The constraint solving logic will be hidden behind an abstract interface. For V1, we will implement a `PythonHeuristicSolver`. Because of the interface, we can later build an `ORToolsSolver` (Google's CP-SAT) and swap it in with zero changes to the rest of the pipeline.
- **Database Repository (`BaseRepository`):** All data access (reading/writing Vets, Rooms, TimeBlocks) will go through a repository layer. We will build an `InMemoryRepository` (or simple SQLite adapter) for the prototype, making it trivial to swap to a Postgres/SQLAlchemy repository in the future.

### 2. Core Data Models (Pydantic)
- `Request`: Contains the raw natural language string (e.g., client text message) and a `request_id`.
- `Job`: Contains `id`, `required_skills` (e.g., "Surgery"), `estimated_duration` (Int), and `soft_requirements` (e.g., "needs a vet good with anxious large dogs").
- `Resource`:
  - **Vets:** `id`, `name`, `hard_skills` (e.g., "Surgery", "Exotics"), `availability_windows`, `attributes` (e.g., "calm, good with large dogs").
  - **Assets:** `id` (e.g., "Exam Room 1", "Ultrasound Machine"), `status`, `availability_windows`.
- `TimeBlock`: The final output binding a `job_id`, `resource_id`s (Vet + Room), `start_time`, and `end_time`.

### 3. The Agentic Pipeline Components

#### Component A: Intake Agent (Neural)
- **Role:** Parse messy, unstructured input into structured data.
- **Tech:** LLM API (e.g., OpenAI `gpt-4o` or Gemini) using Structured Outputs.
- **Action:** Extracts intent from the `Request` and generates a `Job` object.

#### Component B: Semantic Matcher (Neural/Vector)
- **Role:** Handle fuzzy logic and "soft" constraints.
- **Tech:** In-memory Vector Store (FAISS or simple Cosine Similarity).
- **Action:** Embeds the `Job.soft_requirements` and compares against `Resource.attributes`. Returns ranked "Candidate Vets".

#### Component C: Constraint Solver (Symbolic/Heuristic)
- **Role:** Enforce the laws of physics (time overlaps, strict qualifications).
- **Tech:** **Pure Python Heuristics (implementing `BaseSolver`).**
- **Action:** Iterates through candidate Vets and available Exam Rooms to find the first valid time slot. Validates that the Vet has the exact `required_skills`, is free during the `availability_windows`, and that the needed Asset (Exam Room) is also free.

#### Component D: Dispatch Agent (Neural)
- **Role:** Humanize the system output.
- **Tech:** LLM API.
- **Action:** Takes the mathematically validated `TimeBlock` and generates a natural language confirmation. If no slot is found, it formulates an intelligent exception message suggesting alternatives.

### 4. Frontend UI
- **Tech:** Next.js (React) with Tailwind CSS and Framer Motion (for premium, dynamic micro-animations).
- **Features:** 
  - **Publicly Accessible & Mock Login:** A simulated login flow to demonstrate the user journey, deployable to the public web (e.g., Vercel).
  - **Premium Aesthetics:** A sleek, modern design (e.g., glassmorphism, dynamic interactions) to deliver a massive "wow" factor to the clinic owner.
  - A chat-like input for the "Customer Request".
  - A visually rich dashboard view showing the mocked Vet Clinic schedule (Vets, Rooms, existing appointments).
  - **Verbose Demonstration Mode:** A dedicated real-time log panel exposing the backend "Thought Process" (Intake -> Vector Match -> Constraint Solve -> Dispatch). This is explicitly designed to show potential Vet Clinic owners exactly how the AI makes decisions, building trust in the Neuro-Symbolic engine.

## Verification Plan
### Automated Tests
- **Intake Tests:** Feed varied natural language prompts and assert the `Job` schema is populated.
- **Semantic Tests:** Assert that a `Job` requesting a "patient vet" ranks a `Resource` with "great bedside manner" higher.
- **Constraint Tests:** Submit a Job that intentionally conflicts with an existing TimeBlock and assert rejection/rescheduling.

### Manual Verification
- Run the Streamlit server and submit an end-to-end natural language request. Verify the UI updates with a valid, conflict-free TimeBlock assignment.
