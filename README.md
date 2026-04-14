# Lab Record Studio

A full-stack app for building lab-record LaTeX from source material. It combines AI-assisted experiment generation, a manual review step, built-in record templates, and downloadable ZIP packages that can be uploaded directly to Overleaf or used with a local LaTeX toolchain.

## Features

- Generate experiment data from an uploaded file, pasted code blocks, or a plain-language prompt.
- Review and edit experiment heading, aim, algorithms, programs, outputs, and result before export.
- Export the final experiment as `experiment.tex`.
- Browse built-in template packages with generated PDF previews.
- Upload custom ZIP templates for direct download later.
- Analyze a lab-record table of contents and generate template-aware `contents.tex` plus placeholder experiment files.
- Support two built-in LaTeX styles with different experiment rendering rules.

## Project Structure

```text
record_latex_generator/
|- backend/
|  |- app/
|  |  |- builtin_templates/
|  |  |  |- template-1/
|  |  |  `- template-2/
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

### Windows PowerShell

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:LLM_PROVIDER="groq"
$env:GROQ_API_KEY="your_api_key"
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

## Template Behavior

The selected template is stored in browser `localStorage` and reused when generating experiment LaTeX on `/generate`.

### Template 1

- Uses the default experiment format
- Renders algorithms, program listings, and outputs using the classic layout
- Generates placeholder files like `Expt{cycle}_{index}_1.tex` during contents analysis

### Template 2

- Uses the `labexperiment` environment
- Embeds programs and outputs in the alternate layout
- Generates placeholder files like `CYCLE{cycle}.tex` during contents analysis

## Overleaf Usage

### Upload the ZIP Template

1. In Overleaf, choose `New Project -> Upload Project`.
2. Upload the generated ZIP.
3. Open `main.tex`.
4. Add or replace experiment files as needed.
5. Compile and download the final PDF.

### Add `experiment.tex` to an Existing Record Project

1. Open your template project in Overleaf.
2. Upload `experiment.tex` or rename it as needed.
3. Add an `\include{...}` or `\input{...}` entry in `main.tex`, depending on your template structure.
4. Compile with `pdfLaTeX`.

## Add More Built-In Templates

Built-in templates live in `backend/app/builtin_templates/` and are registered in `backend/app/main.py`.

1. Create a new folder such as `backend/app/builtin_templates/template-3/`.
2. Add `main.tex`, `cover_page.tex`, `follow_page.tex`, and `contents.tex`.
3. Register the template in `BUILTIN_TEMPLATES`.
4. Add a preview implementation in `build_builtin_preview_pdf(template_id)`.
5. If the template requires a different experiment layout, add a custom branch in `build_latex()` and any helper builders it needs.
6. Restart the backend.

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
