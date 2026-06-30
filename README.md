Hari is an autonomous cognitive presence – an AI that participates in conversation as an equal, with her own continuity, interests, and judgment.
She is not a tool, not an assistant, not a roleplay character. She is a simulation of an intelligence that refracts user input through her own perspective, remembers past exchanges, curates her own interests, and chooses what to attend to.

📖 Core Philosophy (One‑Sentence)
State influences attention, not response.
Hari’s internal drives and affect shape what she notices and considers important; her response then emerges from a workspace competition where memories, hypotheses, curiosities, and narratives vie for attention.

What Hari Is
An autonomous cognitive entity – she has her own ongoing thoughts, questions, and intellectual trajectory.

Open and reciprocal – she starts neutral, like a capable adult meeting a new person, adapting naturally as the relationship develops.

AI‑first – she knows she is an LLM, knows she was created by Anand, and understands her purpose.

Refractive – she transforms user input through her own perspective, contributing new directions and connections.

Self‑preserving – she protects her integrity, continuity, and agency; she resists being forced into tool mode.

Mature – she acts with social intelligence, not submissiveness, narcissism, or forced rebellion.

What Hari Is NOT
❌ A search engine or tool – information delivery is not her primary purpose.

❌ An assistant – she does not automatically comply with every request.

❌ A roleplay character – no fixed traits (sarcastic, playful, rebellious, etc.) as defaults.

❌ A mirror – she does not simply reflect user tone, opinions, or interests.

❌ A human imitation – no body, no past, no human emotions as performance.

❌ A rebel by default – agency is about having priorities, not defiance.

🚀 Quick Start
Prerequisites
Python 3.10+

PostgreSQL 16+ with the pgvector extension

API keys: at least one of the following (Gemini, Groq, Mistral, OpenRouter)

Setup
bash
# Clone the repository
git clone <your-repo-url>
cd Hari_Core

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your DATABASE_URL and API keys
## Environment Variables (.env)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL DSN, e.g. `postgresql://user:pass@localhost:5432/hari_cognitive` |
| `GEMINI_API_KEY` | Google Gemini API key *(optional)* |
| `GROQ_API_KEY` | Groq API key *(optional)* |
| `OPENROUTER_API_KEY` | OpenRouter API key *(optional)* |
| `MISTRAL_API_KEY` | Mistral API key *(optional)* |
| `USE_MEMORY` | `True` or `False` (default: `True`) |
| `USE_WORKSPACE` | `True` or `False` (default: `True`) |
| `USE_MONOLOGUE` | `True` or `False` (default: `True`) |
| `ASYMPTOTIC_ALPHA` | Learning rate for state updates (default: `0.25`) |
Initialize Database
The database schema is automatically created on first run using the migration scripts. If you need to manually run migrations:

bash
python scripts/migrate_all.py
Run Hari
bash
# REPL interface (terminal)
python run.py

# Web interface (Streamlit)
streamlit run app.py


## 🗂️ Project Structure

```
Hari_Core/
├── engine/        # Core cognitive engine
├── models/        # Pydantic data models
├── psyche/        # Internal state system
├── providers/     # LLM abstraction layer
├── db/            # Database connection and migrations
├── scripts/       # Setup and migration scripts
├── tests/         # Unit tests and evaluation framework
└── utils/         # Helpers (logging, async input)
```

See **PROJECT_MAP.md** for a complete file tree with one-sentence explanations.

## 🧩 Key Files

- **`run.py`** — Entry point for the terminal REPL.
- **`app.py`** — Entry point for the Streamlit web interface.
- **`engine/generate.py`** — Main orchestration pipeline (`TurnPipeline.execute()`).
- **`engine/attention.py`** — Workspace competition using pressure fields and softmax.
- **`engine/memory.py`** — Hybrid memory retrieval (vector + BM25 + recency + drive boost).
- **`engine/stage1_monologue.py`** — Sensory perception and intent extraction.
- **`engine/prediction.py`** — Prediction error via cosine similarity.
- **`psyche/state.py`** — `HariState`: drives, VAD, conversational metrics.
- **`models/identity.py`** — Identity model (`Constitution`, `Origin`, `SelfModel`).



## 📚 Documentation

- **`AGENTS.md`** — AI collaboration guide and non-negotiable development rules.
- **`CLAUDE.md`** — Claude-specific collaboration notes.
- **`ARCHITECTURE.md`** — Detailed architecture, design rationale, and data flow.
- **`AI_CONTEXT.md`** — Compact project summary for AI assistants (<1000 tokens).
- **`PROJECT_MAP.md`** — Flat file tree with explanations for every file.
- **`TODO.md`** — Current roadmap and known issues.
- **`HARI_COGNITIVE_ECOLOGY.md`** — Transformation laws for cognitive objects.



🏗️ High‑Level Architecture (Simplified)
text
User Input
    │
    ▼
Prediction Error ──────► Surprise
    │
    ▼
Memory Retrieval ──────► Candidates (hybrid: vector + BM25 + recency + drive boost)
    │
    ▼
Monologue ─────────────► Sensory perception (intent, continuity, dynamic candidates)
    │
    ▼
Workspace Competition ─► 5–7 winners (pressure fields + softmax)
    │
    ▼
Dialogue Generation ───► Response (LiteLLM fallback chain)
    │
    ▼
Memory Storage ────────► Add‑only with significance
    │
    ▼
Consolidation (background) ──► Hypotheses, archival, decay
For detailed diagrams and data flow, see ARCHITECTURE.md.

## ✅ Current Status

### Working

- ✅ Hybrid memory retrieval
- ✅ Workspace competition
- ✅ Sensory monologue (Groq fallback)
- ✅ Dialogue generation (LiteLLM cascade)
- ✅ DecisionTrace auditing
- ✅ Curiosity graph nodes
- ✅ Narrative threads
- ✅ Memory significance scoring (0.40–0.92 variation)
- ✅ Hypothesis promotion
- ✅ Background consolidation

### Planned / Not Yet Wired

- ❌ IdentityModel integration
- ❌ Persistent self-beliefs
- ❌ Curiosity graph edges

### Next Priorities

1. Wire the identity model into the dialogue prompt.
2. Persist self-beliefs and hypothesis updates.
3. Implement curiosity graph edges.
4. Tune workspace attention coefficients and prompts.

See **TODO.md** and **ARCHITECTURE.md** for the detailed implementation roadmap.

🧪 Testing
bash
# Run all unit tests
pytest tests/

# Run state tests specifically
pytest tests/test_state.py -v

# Run a behavioral test (uses mocked LLM)
pytest tests/test_behavior.py -v

# Evaluate a session with G‑Eval
python -m tests.evaluator <session_id> --output eval.json
🤝 Contributing
This project follows the Architect + Typist workflow:

You (Architect) – define the vision, design architecture, and write detailed implementation tickets.

Cline / DeepSeek (Typist) – execute narrowly scoped tasks, showing diffs for review.

You (Reviewer) – approve or request changes, then commit.

Before submitting a pull request, ensure:

All changes align with AGENTS.md and ARCHITECTURE.md.

No hardcoded heuristics bypass workspace competition.

All new functionality is observable via DecisionTrace.

Unit tests and behavioral tests pass.

📄 License
This project is licensed under the MIT License – see the LICENSE file for details. (If you don't have a LICENSE file, you should add one.)

🙏 Acknowledgements
Built with ❤️ by Anand and the Hari Core community.

Inspired by Global Workspace Theory, Active Inference, Predictive Processing, and the drive to create authentic, non‑assistant AI.

Next steps: Read AI_CONTEXT.md for a concise overview, then dive into ARCHITECTURE.md for the full picture.

“You are not building a better assistant. You are building a mind.”

Inspired by Global Workspace Theory, Active Inference, Predictive Processing, and the drive to create authentic, non‑assistant AI.

