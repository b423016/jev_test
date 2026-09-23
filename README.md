# Before you sign

One page. Upload a PDF or paste text. Lit paragraphs are the ones that change what you give up.

## Keys

Put these in `.env` (see `.env.example`).

| Name | Required | What it is |
|---|---|---|
| `TYPESAFE_API_KEY` | Yes | TypeSafe key for Jev |
| `OPENAI_API_KEY` | Yes | OpenAI key for the short explanation of lit paragraphs |
| `OPENAI_MODEL` | Yes | Model id, for example the small model you want to pay for |
| `DATABASE_URL` | No | Neon connection string. Playbook cards are stored there. Without it, the same cards are read from `app/catalog.json`. |
| `REDIS_URL` | No | Redis URL. Caches the Jev scores for 7 days under the document hash. Without it, every upload calls Jev. |
| `TYPESAFE_MODEL` | No | Defaults to `jev-latest` |
| `BITE_THRESHOLD` | No | Defaults to `0.55` |

The page hashes the file with SHA-256 before the upload. The server hashes the same bytes and rejects the request on a mismatch. That catches a body that changed on the way. It does not hide the bytes. The calls to Jev and OpenAI go out over HTTPS with certificate checks. Run the app on this machine.

User documents are not written to Neon. Neon only holds the clause cards. Redis stores scores, not the file.

## Run

```text
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
py -3 -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765`.
