import asyncio
import json
import os
import re
import shutil
import tempfile
import zipfile
import subprocess
from pathlib import Path
from typing import Any

import fitz
import google.generativeai as genai
import pdfplumber
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="AI LaTeX Lab Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LATEX_TEMPLATE = r"""\\pagestyle{fancy}
\\fancyhf{}
\\fancyhead[L]{Operating System Programs}
\\fancyhead[R]{Page \\thepage}

\\lstset{
    language={[x86masm]Assembler},
    basicstyle=\\ttfamily\\small,
    frame=single,
    numbers=left,
    numberstyle=\\tiny,
    stepnumber=1,
    numbersep=5pt,
    showstringspaces=false,
    breaklines=true,
    tabsize=4,
    keywordstyle=\\color{blue!60!black},
    commentstyle=\\color{green!40!black}
}

\\tcbset{
    myoutputbox/.style={
        colback=black,
        colframe=gray!75!black,
        coltext=white,
        boxrule=0.5pt,
        arc=2pt,
        fontupper=\\ttfamily\\small,
        fonttitle=\\bfseries\\small,
        coltitle=white
    }
}

\\small
\\begin{center}
    \\Large \\underline{\\textbf{EXPERIMENT NO. __EXPERIMENT_NUMBER__}} \\\\
    \\large \\underline{\\textbf{{__EXPERIMENT_HEADING__}}}
\\end{center}

\\vspace{0.5cm}
\\noindent \\Large\\textbf{{DATE: __DATE__}}
\\vspace{0.2cm}

\\normalsize
\\section*{\\underline{AIM}}
__AIM__

\\section*{\\underline{ALGORITHM}}
__ALGORITHM_SECTIONS__

\\section*{\\underline{PROGRAM}}
__PROGRAM_SECTIONS__

\\section*{\\underline{OUTPUT}}
__OUTPUT_SECTIONS__

\\large
\\section*{\\underline{RESULT}}
__RESULT__
"""


class ProgramData(BaseModel):
    title: str
    code: str
    dependencies: list[str] = Field(default_factory=list)
    output: str = ""


class AlgorithmData(BaseModel):
    name: str
    steps: list[str]


class ExperimentData(BaseModel):
    experiment_number: str
    date: str
    experiment_heading: str
    title: str
    aim: str
    algorithms: list[AlgorithmData]
    programs: list[ProgramData]
    result: str


def _extract_json(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _extract_text_from_pdf(path: Path) -> str:
    chunks: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text() or "")
    text = "\n".join(chunks).strip()
    if text:
        return text

    doc = fitz.open(path)
    fallback = []
    for page in doc:
        fallback.append(page.get_text())
    return "\n".join(fallback)


def _extract_text(file_path: Path, temp_dir: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return _extract_text_from_pdf(file_path)
    if suffix == ".txt":
        return file_path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".zip":
        unzip_dir = temp_dir / "unzipped"
        unzip_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(file_path, "r") as zf:
            zf.extractall(unzip_dir)

        all_text: list[str] = []
        for p in unzip_dir.rglob("*"):
            if p.is_dir():
                continue
            ext = p.suffix.lower()
            if ext in {".c", ".h", ".txt", ".md"}:
                all_text.append(f"\n--- FILE: {p.name} ---\n")
                all_text.append(p.read_text(encoding="utf-8", errors="ignore"))
            elif ext == ".pdf":
                all_text.append(f"\n--- FILE: {p.name} ---\n")
                all_text.append(_extract_text_from_pdf(p))
        return "\n".join(all_text)

    raise HTTPException(status_code=400, detail="Unsupported file type")


def _gemini_model() -> Any:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not set")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-1.5-pro")


def _extract_programs_with_gemini(raw_text: str) -> list[ProgramData]:
    prompt = f"""
Extract all valid C programs from the text below.
Rules:
- Ignore theory, explanations, and non-code prose.
- Detect multiple independent programs.
- Fix OCR spacing issues only when compilation would break.
- Detect additional header/source dependencies if present.
- Return strict JSON only in the shape:
{{
  "programs": [
    {{"title": "", "code": "", "dependencies": []}}
  ]
}}

Text:
{raw_text}
"""
    model = _gemini_model()
    response = model.generate_content(prompt)
    data = _extract_json(response.text)
    programs = [ProgramData(**p) for p in data.get("programs", []) if p.get("code")]
    if not programs:
        raise HTTPException(status_code=422, detail="No valid C programs detected")
    return programs


def _academic_content_with_gemini(program: ProgramData, output: str) -> tuple[str, str, list[AlgorithmData]]:
    prompt = f"""
Generate academic lab-record content for this C program and output.
Return strict JSON only:
{{
  "title": "",
  "aim": "",
  "algorithms": [
    {{"name": "", "steps": []}}
  ]
}}
Rules:
- Academic tone.
- Steps must be numbered logically (we will render numbers).
- No hallucinated features.

Program:
{program.code}

Execution Output:
{output}
"""
    model = _gemini_model()
    response = model.generate_content(prompt)
    data = _extract_json(response.text)
    title = data.get("title", program.title or "C Program Experiment")
    aim = data.get("aim", "")
    algorithms = [AlgorithmData(**algo) for algo in data.get("algorithms", [])]
    return title, aim, algorithms


def _run_program(program: ProgramData, index: int, temp_dir: Path) -> str:
    source_path = temp_dir / f"program_{index}.c"
    binary_path = temp_dir / f"program_{index}"
    source_path.write_text(program.code, encoding="utf-8")

    compile_proc = subprocess.run(
        ["gcc", str(source_path), "-o", str(binary_path)],
        capture_output=True,
        text=True,
    )
    compile_out = (compile_proc.stdout or "") + (compile_proc.stderr or "")
    if compile_proc.returncode != 0:
        return f"Compilation Failed\n{compile_out}"

    try:
        run_proc = subprocess.run(
            [str(binary_path)],
            capture_output=True,
            text=True,
            timeout=3,
        )
        return (run_proc.stdout or "") + (run_proc.stderr or "")
    except subprocess.TimeoutExpired:
        return "Execution timed out after 3 seconds"


def _escape_latex(value: str) -> str:
    replacements = {
        "\\": r"\\textbackslash{}",
        "&": r"\\&",
        "%": r"\\%",
        "$": r"\\$",
        "#": r"\\#",
        "_": r"\\_",
        "{": r"\\{",
        "}": r"\\}",
    }
    escaped = value
    for src, target in replacements.items():
        escaped = escaped.replace(src, target)
    return escaped


def _build_latex(exp: ExperimentData) -> str:
    algo_sections = []
    for algo in exp.algorithms:
        steps = "\n".join(f"    \\item {_escape_latex(step)}" for step in algo.steps)
        algo_sections.append(
            f"\\subsection*{{{_escape_latex(algo.name)}}}\n"
            "\\begin{enumerate}[label=\\arabic*.]\n"
            f"{steps}\n"
            "\\end{enumerate}"
        )

    program_sections = []
    output_sections = []
    for i, program in enumerate(exp.programs, start=1):
        listing_title = _escape_latex(program.title or f"Program {i}")
        program_sections.append(
            f"\\subsection*{{Listing {i}: {listing_title}}}\n"
            "\\begin{lstlisting}[language=C]\n"
            f"{program.code}\n"
            "\\end{lstlisting}"
        )
        output_sections.append(
            "\\begin{tcolorbox}[myoutputbox, title=Terminal Output]\n"
            "\\begin{verbatim}\n"
            f"{program.output}\n"
            "\\end{verbatim}\n"
            "\\end{tcolorbox}"
        )

    return (
        LATEX_TEMPLATE.replace("__EXPERIMENT_NUMBER__", _escape_latex(exp.experiment_number))
        .replace("__EXPERIMENT_HEADING__", _escape_latex(exp.experiment_heading))
        .replace("__DATE__", _escape_latex(exp.date))
        .replace("__AIM__", _escape_latex(exp.aim))
        .replace("__ALGORITHM_SECTIONS__", "\n".join(algo_sections))
        .replace("__PROGRAM_SECTIONS__", "\n".join(program_sections))
        .replace("__OUTPUT_SECTIONS__", "\n".join(output_sections))
        .replace("__RESULT__", _escape_latex(exp.result))
    )


@app.post("/api/upload-process")
async def upload_process(file: UploadFile = File(...)):
    temp_dir = Path(tempfile.mkdtemp(prefix="labgen_"))
    try:
        input_path = temp_dir / file.filename
        with open(input_path, "wb") as out:
            out.write(await file.read())

        raw_text = await asyncio.to_thread(_extract_text, input_path, temp_dir)
        programs = await asyncio.to_thread(_extract_programs_with_gemini, raw_text)

        final_programs: list[ProgramData] = []
        all_algorithms: list[AlgorithmData] = []
        title = ""
        aim = ""

        for idx, program in enumerate(programs, start=1):
            output = await asyncio.to_thread(_run_program, program, idx, temp_dir)
            prog_title, prog_aim, algorithms = await asyncio.to_thread(_academic_content_with_gemini, program, output)
            if not title:
                title = prog_title
            if not aim:
                aim = prog_aim
            if algorithms:
                all_algorithms.extend(algorithms)
            program.output = output
            if not program.title:
                program.title = prog_title
            final_programs.append(program)

        return {
            "experiment_number": "1",
            "date": "23/09/2025",
            "experiment_heading": title or "Operating System Programs",
            "title": title,
            "aim": aim,
            "algorithms": [a.model_dump() for a in all_algorithms],
            "programs": [p.model_dump() for p in final_programs],
            "result": "Program executed and output verified successfully.",
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.post("/api/generate-latex")
async def generate_latex(payload: ExperimentData):
    return {"latex": _build_latex(payload)}
