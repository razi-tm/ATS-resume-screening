# Architecture

```mermaid
flowchart LR
  Recruiter --> Web[Next.js Web]
  Web --> API[FastAPI API]
  API --> DB[(PostgreSQL + pgvector)]
  API --> Redis[(Redis)]
  API --> Worker[Background Worker]
  Worker --> Parser[Resume Parser]
  Worker --> AI[Embedding/LLM Providers]
  Worker --> Scoring[Scoring Strategies]
  Scoring --> Reports[Reports]
```

## Decisions

- Keep parser, AI provider interfaces, and scoring engine in reusable packages so Streamlit and FastAPI use the same core logic.
- Use deterministic TF-IDF embeddings by default for reliable local/CI execution; switch `EMBEDDING_PROVIDER=sentence-transformers` for production semantic embeddings.
- Model SaaS entities around organizations, users, jobs, resumes, screenings, and reports to support multi-tenancy from day one.
