# AI LaTeX Lab Generator

## Run backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY=your_key
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend API:

- `POST /api/upload-process` (existing upload flow)
- `POST /api/process-text` (new pasted text flow using `###` headings)
- `POST /api/generate-latex`

## Run frontend

```bash
cd frontend
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_BASE` if backend is not at `http://localhost:8000`.
