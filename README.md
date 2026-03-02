# AI LaTeX Lab Generator

A full-stack web app that converts lab content into structured LaTeX, with AI-assisted extraction, manual review, and export-ready output.
It also provides a downloadable LaTeX template ZIP for complete record preparation.

## Features

- AI-assisted experiment generation from uploaded files or pasted code text.
- Human-in-the-loop editor to review and correct experiment details before export.
- Final LaTeX export (`.tex`) for direct use in Overleaf or local LaTeX tools.
- Template ZIP generator with `main.tex`, cover page, follow-up page, and contents files.

## Project Structure

```text
record_latex_generator/
|- backend/    # FastAPI service + LLM integration + LaTeX generation
|- frontend/   # Next.js UI (generator + template download pages)
`- README.md
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- npm 9+
- A valid LLM API key:
  - `GROQ_API_KEY` (default provider), or
  - `GEMINI_API_KEY` (if using Gemini)

## 1) Backend Setup (FastAPI)

From project root:

### Windows PowerShell

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:LLM_PROVIDER="groq"          # optional, defaults to groq
$env:GROQ_API_KEY="your_api_key"  # required for groq
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### macOS/Linux

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export LLM_PROVIDER=groq          # optional, defaults to groq
export GROQ_API_KEY=your_api_key  # required for groq
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

If you want Gemini instead:

- Set `LLM_PROVIDER=gemini`
- Set `GEMINI_API_KEY=your_api_key`

## 2) Frontend Setup (Next.js)

Open a second terminal from project root:

```bash
cd frontend
npm install
```

If backend runs on a different URL, set:

```bash
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

Then start frontend:

```bash
npm run dev
```

Open: `http://localhost:3000`

## Backend API Endpoints

- `POST /api/upload-process`
- `POST /api/process-text`
- `POST /api/generate-latex`
- `POST /api/download-template`

## User Manual

### A) Generate Experiment LaTeX

1. Open the app home page and choose **Generate Experiment LaTeX**.
2. Select input mode:
   - **Upload File**: upload `.pdf`, `.txt`, `.zip`, or `.bin`
   - **Paste Code**: paste text in this format:
     ```text
     ### Program 1 Title
     <code...>

     ### Program 2 Title
     <code...>
     ```
3. Click **Generate Experiment**.
4. In **Step 2 - Review & Correct**, update:
   - experiment number/date/heading
   - aim
   - algorithm names and steps
   - each program code and output
   - final result
5. Click **Generate Final LaTeX**.
6. Use **Copy** or **Download .tex**.

### B) Download Full LaTeX Template ZIP

1. From home page, open **Download LaTeX Template**.
2. Fill the form (name, course code, department, institution, semester, roll number, etc.).
3. Click **Download ZIP**.
4. Extract the ZIP and review files (`main.tex`, `cover_page.tex`, `follow_page.tex`, `contents.tex`, etc.).

## Overleaf Helper Guide

### Option 1: Using Generated `experiment.tex`

1. Go to Overleaf and create a new project.
2. Upload `experiment.tex`.
3. If needed, add a minimal `main.tex` that includes your experiment content.
4. Compile with `pdfLaTeX`.
5. Fix any missing package issues by adding `\usepackage{...}` lines to your main file.

### Option 2: Using Template ZIP

1. In Overleaf, choose **New Project -> Upload Project**.
2. Upload the generated ZIP directly.
3. Open `main.tex` and confirm included files are present.
4. Replace/add experiment files as needed.
5. Compile and download final PDF.

## Troubleshooting

- `Missing GROQ_API_KEY` or `Missing GEMINI_API_KEY`:
  - Set the correct environment variable before running backend.
- Frontend cannot reach backend:
  - Verify backend is running on port `8000`.
  - Set `NEXT_PUBLIC_API_BASE` to the correct backend URL.
- Empty or weak AI output:
  - Improve input quality and use clear headings for pasted code.
  - Review and manually correct fields in Step 2 before final LaTeX generation.
