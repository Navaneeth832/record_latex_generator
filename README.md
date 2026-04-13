# Lab Record Studio

A full-stack web app that converts lab content into structured LaTeX, with AI-assisted extraction, manual review, and export-ready output.
It also provides a built-in template library plus downloadable LaTeX template ZIP packages for complete record preparation.

## Features

- AI-assisted experiment generation from uploaded files or pasted code text.
- Human-in-the-loop editor to review and correct experiment details before export.
- Final LaTeX export (`.tex`) for direct use in Overleaf or local LaTeX tools.
- Built-in template library with admin-controlled preview PDFs.
- Template ZIP generator with `main.tex`, `cover_page.tex`, `follow_page.tex`, and `contents.tex`.
- Manual ZIP template upload for one-off template downloads.

## Project Structure

```text
record_latex_generator/
|- backend/    # FastAPI service + LLM integration + LaTeX generation
|- frontend/   # Next.js UI (generator + template workspace)
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
export LLM_PROVIDER=groq
export GROQ_API_KEY=your_api_key
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
- `GET /api/templates`
- `GET /api/templates/{template_id}/preview`
- `POST /api/templates/{template_id}/download`
- `POST /api/templates/upload`

## User Manual

### Step 1) Choose a Record Template and Download ZIP

1. From the home page, select one of the built-in templates.
2. Review its preview PDF.
3. Fill the form with your record details.
4. Click **Download Selected Template**.
5. Extract the ZIP and review files such as `main.tex`, `cover_page.tex`, `follow_page.tex`, and `contents.tex`.
6. Upload the project to Overleaf or use it locally as the base record template.

### Step 1B) Manual Template Upload

1. Use the `+ Add Template ZIP` action on the home page.
2. Upload a ZIP file.
3. Select that uploaded template and download it when needed.
4. Uploaded templates are downloaded as-is and do not use the built-in preview system.

### Step 2) Generate Individual Experiment LaTeX

1. From the home page, choose **Generate Experiment LaTeX**.
2. Select an input mode:
   - **Upload File**: upload `.pdf`, `.txt`, `.zip`, or `.bin`
   - **Paste Code**: paste text in this format:
     ```text
     ### Program 1 Title
     <code...>

     ### Program 2 Title
     <code...>
     ```
   - **Ask AI**: describe the C program you want generated
3. Click **Generate Experiment**.
4. In **Step 2 - Review & Correct**, update the experiment details, aim, algorithms, programs, output, and result.
5. Click **Generate Final LaTeX**.
6. Use **Copy** or **Download .tex**.
7. Upload the generated `.tex` into the record template project and compile it in Overleaf or your local LaTeX editor.

## Overleaf Helper Guide

### 1) Using Template ZIP

1. In Overleaf, choose **New Project -> Upload Project**.
2. Upload the generated ZIP directly.
3. Open `main.tex` and confirm the included files are present.
4. Replace or add experiment files as needed.
5. Compile and download the final PDF.

### 2) Using Generated `experiment.tex`

1. Open the record template project in Overleaf.
2. Upload `experiment.tex` or a renamed experiment file.
3. Add an `\include{...}` entry in `main.tex`.
4. Compile with `pdfLaTeX`.
5. Fix any missing package issues by adding `\usepackage{...}` lines to the main file if needed.

## Troubleshooting

- `Missing GROQ_API_KEY` or `Missing GEMINI_API_KEY`:
  Set the correct environment variable before running the backend.
- Frontend cannot reach backend:
  Verify the backend is running on port `8000` and set `NEXT_PUBLIC_API_BASE` correctly.
- Empty or weak AI output:
  Improve input quality and review the generated content in Step 2 before exporting the final LaTeX.

## Admin: Add More Built-In Templates

Built-in templates are stored under `backend/app/builtin_templates/` and registered in `backend/app/main.py`.

1. Add a new LaTeX file set.
   Create a new folder such as `backend/app/builtin_templates/template-3/` and add:
   `main.tex`, `cover_page.tex`, `follow_page.tex`, and `contents.tex`.
2. Register the template inside `BUILTIN_TEMPLATES`.
   Give it a new ID such as `"template-3"` plus `name`, `description`, `download_filename`, and a `files` map loaded with `read_template_file(...)`.
3. Add its preview design in `build_builtin_preview_pdf(template_id)`.
   That returned PDF is the exact built-in preview users will see on the home page.
4. Restart the backend.

Example:

```python
BUILTIN_TEMPLATES["template-3"] = {
    "name": "Template 3 - Minimal Record",
    "description": "Short description shown on the home page.",
    "download_filename": "template-3-minimal-record.zip",
    "files": {
        "main.tex": read_template_file("template-3", "main.tex"),
        "cover_page.tex": read_template_file("template-3", "cover_page.tex"),
        "follow_page.tex": read_template_file("template-3", "follow_page.tex"),
        "contents.tex": read_template_file("template-3", "contents.tex"),
    },
}
```
