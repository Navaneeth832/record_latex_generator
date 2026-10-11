# Lab Record Studio

A full-stack app for building lab-record LaTeX from source material. It combines AI-assisted experiment generation, a manual review step, built-in record templates, and downloadable ZIP packages that can be uploaded directly to Overleaf or used with a local LaTeX toolchain.
  - Deployment link: [https://record-latex-generator.onrender.com/](https://record-latex-generator.vercel.app/)

## Features

- Generate experiment data from an uploaded file, pasted code blocks, or a plain-language prompt.
- Review and edit experiment heading, aim, algorithms, programs, outputs, and result before export.
- Export the final experiment as `experiment.tex`.
- Preview the official Navaneeth record template with live PDF preview.
- Analyze a lab-record table of contents and generate template-aware `contents.tex` plus placeholder experiment files.
- Download complete ready-to-compile LaTeX ZIP packages.

## Project Structure

```text
record_latex_generator/
|- backend/
|  |- app/
|  |  |- builtin_templates/
|  |  |  `- template-1/
|  |  |- figures/
|  |  `- main.py
|  `- requirements.txt
|- frontend/
|  |- src/
|  |  |- app/
|  |  |  |- generate/
|  |  |  |- template/
|  |  |  |- globals.css
|  |  |  |- layout.tsx
|  |  |  `- page.tsx
|  |  |- components/
|  |  |  `- MonacoField.tsx
|  |  `- lib/
|  |     |- parsePrograms.ts
|  |     |- types.ts
|  |     `- useCopyToClipboard.ts
|  |- package.json
|  |- tailwind.config.ts
|  `- tsconfig.json
|- .env
`- README.md
```

## Architecture

### Backend

- Framework: FastAPI
- Main entrypoint: `backend/app/main.py`
- Responsibilities:
  - Extract text from uploaded `.pdf`, `.txt`, `.zip`, and `.bin` files
  - Call the configured LLM provider
  - Convert parsed content into experiment JSON
  - Generate final LaTeX for the selected template
  - Build downloadable template ZIP files
  - Generate built-in preview PDFs
  - Analyze contents pages and create template-specific placeholder files

### Frontend

- Framework: Next.js 14 with the App Router
- Main routes:
  - `/`: template workspace
  - `/generate`: experiment generation and LaTeX export flow
  - `/template`: redirects to `/`
- Responsibilities:
  - Template selection and preview
  - Template form editing
  - Template ZIP upload and download
  - Contents analyzer UI for built-in templates
  - Experiment generation, review, and final LaTeX export

## Prerequisites

- Python 3.10+
- Node.js 18+
- npm 9+
- One LLM API key:
  - `GROQ_API_KEY` for Groq, or
  - `GEMINI_API_KEY` for Gemini

Optional environment variables:

- `LLM_PROVIDER=groq` or `LLM_PROVIDER=gemini`
- `NEXT_PUBLIC_API_BASE=http://localhost:8000` if the frontend should call a non-default backend URL

## Backend Setup

From the project root:

### Windows cmd

```cmd
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
set LLM_PROVIDER=groq
set GROQ_API_KEY=your_api_key
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

To switch providers:

- Set `LLM_PROVIDER=gemini`
- Set `GEMINI_API_KEY=your_api_key`

## Frontend Setup

Open a second terminal from the project root:

```bash
cd frontend
npm install
npm run dev
```

If the backend is not running on `http://localhost:8000`, set:

```bash
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

The frontend runs at `http://localhost:3000`.

## API Endpoints

### Experiment Generation

- `POST /api/upload-process`
- `POST /api/process-text`
- `POST /api/process-question`
- `POST /api/generate-latex`

### Template Library

- `GET /api/templates`
- `GET /api/templates/{template_id}/preview`
- `POST /api/templates/{template_id}/download`
- `POST /api/templates/upload`
- `POST /api/download-template`

### Contents Analysis

- `POST /api/templates/{template_id}/analyze-contents-text`
- `POST /api/templates/{template_id}/analyze-contents-upload`

## User Flows

### 1. Download a Record Template ZIP

1. Open the home page.
2. Select a built-in template or upload a custom ZIP template.
3. For built-in templates, review the generated preview PDF.
4. Fill in the record details form.
5. Click `Download Selected Template`.
6. Extract the ZIP and open it in Overleaf or your local LaTeX editor.

Built-in templates are rendered with the form values before download. Uploaded ZIP templates are returned as-is.

### 2. Analyze a Contents Page

This flow is available only for built-in templates.

1. Select a built-in template on the home page.
2. Paste the lab-record contents text or upload a contents PDF.
3. Click `Analyze Contents`.
4. Review the detected cycles and experiment counts.
5. Download the template ZIP.

The backend will generate:

- a template-specific `contents.tex`
- placeholder experiment files
- an updated `main.tex` that includes those generated files

### 3. Generate Experiment LaTeX

1. Open `/generate`.
2. Choose one input mode:
   - `Upload File`: upload `.pdf`, `.txt`, `.zip`, or `.bin`
   - `Paste Code`: paste code blocks using `### Title` headings
   - `Ask AI`: describe the C program you want
3. Click `Generate Experiment`.
4. Review and edit the generated experiment details.
5. Click `Generate Final LaTeX`.
6. Copy the LaTeX or download `experiment.tex`.

## Paste Code Format

Use this format on the generator page:

```text
### Program 1 Title
<code here>

### Program 2 Title
<code here>
```

## Template Format

### Navaneeth Lab Record Template

- Uses structured output boxes and standard lab record formatting
- Renders algorithms, program listings, and terminal outputs cleanly
- Generates placeholder files like `Expt{cycle}_{index}_1.tex` during table of contents analysis

## Troubleshooting

- `Missing GROQ_API_KEY` or `Missing GEMINI_API_KEY`
  Set the correct environment variable before starting the backend.
- Frontend cannot reach the backend
  Verify the backend is running on port `8000` and set `NEXT_PUBLIC_API_BASE` if needed.
- No programs detected from pasted or uploaded content
  Make sure pasted code uses `### Title` headings, or that the uploaded file contains extractable text.
- Contents analysis fails for uploaded images
  Image OCR is not implemented in the current backend. Paste text directly or upload a PDF instead.
- Generated AI output is weak or incomplete
  Improve the input prompt or source material, then correct the result in the review step before exporting LaTeX.
