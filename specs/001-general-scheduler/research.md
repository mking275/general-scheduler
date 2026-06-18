# Research: General Scheduler Prototype

## Decisions
- **Decision:** Use Pure Python Heuristics for Constraint Solving (V1).
  - **Rationale:** Fastest time to a working prototype. Easier to demonstrate the "Agentic" flow without combinatorial math overhead in the demo.
  - **Alternatives considered:** Google OR-Tools (CP-SAT), NetworkX Graph Traversal.
- **Decision:** Use Next.js with Tailwind and Framer Motion for Frontend.
  - **Rationale:** Required to deliver a "wow" factor with glassmorphism and micro-animations to clinic owners.
  - **Alternatives considered:** Streamlit (Python) - rejected due to basic UI.
- **Decision:** Mock Login with Single Generic Role.
  - **Rationale:** Focuses the demo strictly on the scheduling value proposition; keeps cognitive load low for the viewer.
  - **Alternatives considered:** Full RBAC (Admin vs Front Desk) - rejected for V1 demo scope to keep it simple.
