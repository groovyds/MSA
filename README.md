# Marketing Strategist AI (archived)

> **Status: archived, unfinished.** This was a 2025 learning project: a RAG prototype for a marketing
> strategist who wanted to search and chat across their PowerPoint decks (about 150 per client).
> It was never deployed and does not run end to end. Kept for reference only.

## The idea

Upload `.pptx`/`.pdf` decks → extract the text → split it into chunks → embed them (OpenAI
`text-embedding-3-small`) → store them in Postgres with pgvector → answer questions with the most
similar chunks as context.

## What exists

- `backend/app/utils/text_processor.py`: text extraction and sentence-based chunking with overlap
- `backend/app/services/embedding_service.py`: embeddings and cosine-distance search in pgvector
- `backend/app/services/chat_service.py`: a retrieval-augmented prompt
- FastAPI routes for uploads (including chunked uploads) and chat, plus a Next.js UI shell

## Known gaps

- The backend's database setup doesn't import cleanly, so the server doesn't start as-is.
- The chat route doesn't pass a database session to retrieval.
- The Next.js chat calls the model directly and never reaches the backend, so answers don't use the decks.
- The upload calls aren't wired to the backend routes.
- The agents in `backend/app/agents/` are stubs; there's no authentication; the Terraform/EC2 files were never used.

## What I'd do differently

Start with a single script (extract, chunk, embed, search) and a small set of real questions with
expected answers to measure retrieval quality, before adding a web UI, agents or infrastructure.

## License

MIT
