import asyncio
import json
import os
import re
import shutil
import tempfile
import zipfile
import subprocess
from pathlib import Path
from typing import Any, List

import fitz
import pdfplumber
import google.generativeai as genai

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# =========================================================
# FASTAPI SETUP
# =========================================================

app = FastAPI(title="AI LaTeX Lab Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# DATA MODELS
# =========================================================

class ProgramData(BaseModel):
    title: str = ""
    code: str
    output: str = ""


class AlgorithmData(BaseModel):
    name: str
    steps: List[str]


class ExperimentData(BaseModel):
    experiment_number: str
    date: str
    experiment_heading: str
    aim: str
    algorithms: List[AlgorithmData]
    programs: List[ProgramData]
    result: str


# =========================================================
# STRICT LATEX TEMPLATE (FIXED FORMAT)
# =========================================================

LATEX_TEMPLATE = r"""
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{Operating System Programs}
\fancyhead[R]{Page \thepage}

\lstset{
language=C,
basicstyle=\ttfamily\small,
frame=single,
numbers=left,
numberstyle=\tiny,
breaklines=true
}

\tcbset{
myoutputbox/.style={
colback=black,
colframe=gray!75!black,
coltext=white,
fontupper=\ttfamily\small
}
}

\small
\begin{center}
\Large \underline{\textbf{EXPERIMENT NO. __NO__}} \\
\large \underline{\textbf{__HEADING__}}
\end{center}

\vspace{0.5cm}
\noindent \Large\textbf{DATE: __DATE__}

\normalsize
\section*{\underline{AIM}}
__AIM__

\section*{\underline{ALGORITHM}}

__ALGORITHMS__

\section*{\underline{PROGRAM}}

__PROGRAMS__

\section*{\underline{OUTPUT}}

__OUTPUTS__

\large
\section*{\underline{RESULT}}
__RESULT__
"""


# =========================================================
# GEMINI MODEL
# =========================================================

def gemini():
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise HTTPException(500, "Missing GEMINI_API_KEY")

    genai.configure(api_key=key)
    return genai.GenerativeModel("gemini-3-flash-preview")


# =========================================================
# JSON EXTRACTION
# =========================================================

def extract_json(text: str):
    try:
        return json.loads(text)
    except:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise HTTPException(422, "Invalid AI JSON")
        return json.loads(match.group())


# =========================================================
# FILE TEXT EXTRACTION
# =========================================================

def extract_pdf(path: Path):
    text = []

    with pdfplumber.open(path) as pdf:
        for p in pdf.pages:
            text.append(p.extract_text() or "")

    result = "\n".join(text)
    if result.strip():
        return result

    doc = fitz.open(path)
    return "\n".join(p.get_text() for p in doc)


def extract_text(path: Path, temp: Path):

    suffix = path.suffix.lower()

    # =============================
    # HANDLE FILES WITHOUT EXTENSION
    # =============================
    if suffix == "" or suffix not in [
        ".pdf", ".txt", ".zip", ".bin"
    ]:
        try:
            # try reading as text
            return path.read_text(errors="ignore")
        except:
            return path.read_bytes().decode(errors="ignore")
    # =============================
    # DIRECT FILE SUPPORT
    # =============================

    if suffix == ".pdf":
        return extract_pdf(path)

    if suffix == ".txt":
        return path.read_text(errors="ignore")

    if suffix == ".bin":
        # safely decode binary content
        return path.read_bytes().decode(errors="ignore")

    # =============================
    # ZIP SUPPORT
    # =============================

    if suffix == ".zip":

        unzip = temp / "unzipped"
        unzip.mkdir(exist_ok=True)

        zipfile.ZipFile(path).extractall(unzip)

        data = []

        for f in unzip.rglob("*"):

            if f.is_dir():
                continue

            ext = f.suffix.lower()

            # -------- TEXT BASED --------
            if ext in [".c", ".txt"]:
                data.append(
                    f"\n--- FILE: {f.name} ---\n"
                )
                data.append(
                    f.read_text(errors="ignore")
                )

            # -------- PDF INSIDE ZIP --------
            elif ext == ".pdf":
                data.append(
                    f"\n--- FILE: {f.name} ---\n"
                )
                data.append(
                    extract_pdf(f)
                )

            # -------- BIN INSIDE ZIP --------
            elif ext == ".bin":
                data.append(
                    f"\n--- FILE: {f.name} ---\n"
                )
                data.append(
                    f.read_bytes().decode(errors="ignore")
                )

        return "\n".join(data)

    raise HTTPException(400, "Unsupported file")


# =========================================================
# PROGRAM EXTRACTION
# =========================================================

def extract_programs(raw_text):

    prompt = f"""
Extract ALL C programs.

Return STRICT JSON:

{{
"programs":[
{{"title":"","code":""}}
]
}}

TEXT:
{raw_text}
"""

    res = gemini().generate_content(prompt)
    data = extract_json(res.text)

    return [ProgramData(**p) for p in data["programs"]]


# =========================================================
# ACADEMIC CONTENT
# =========================================================

def generate_academic(program, output):

    prompt = f"""
Generate AIM and ALGORITHMS.

Return JSON:

{{
"aim":"",
"algorithms":[
{{"name":"","steps":[]}}
]
}}

Program:
{program.code}
"""

    res = gemini().generate_content(prompt)
    data = extract_json(res.text)

    algos = [AlgorithmData(**a) for a in data["algorithms"]]

    return data["aim"], algos


# =========================================================
# RUN C PROGRAM
# =========================================================

def run_program(program, i, temp):

    src = temp / f"p{i}.c"
    exe = temp / f"p{i}"

    src.write_text(program.code)

    compile = subprocess.run(
        ["gcc", src, "-o", exe],
        capture_output=True,
        text=True,
    )

    if compile.returncode != 0:
        return compile.stderr

    run = subprocess.run(
        [exe],
        capture_output=True,
        text=True,
        timeout=3,
    )

    return run.stdout


# =========================================================
# LATEX BUILDER (DETERMINISTIC)
# =========================================================

ORDER = ["FCFS", "SJF", "Round Robin", "Priority"]


def build_algorithms(algorithms):

    ordered = []

    for name in ORDER:
        for a in algorithms:
            if name.lower() in a.name.lower():
                ordered.append(a)

    blocks = []

    for algo in ordered:

        steps = "\n".join(
            f"    \\item {s}" for s in algo.steps
        )

        blocks.append(
f"""\\subsection*{{{algo.name}}}
\\begin{{enumerate}}[label=\\arabic*.]
{steps}
\\end{{enumerate}}"""
        )

    return "\n".join(blocks)


def build_programs(programs):

    sections = []

    for i, p in enumerate(programs, 1):

        sections.append(
f"""\\subsection*{{Listing {i}: {p.title}}}
\\begin{{lstlisting}}[language=C]
{p.code}
\\end{{lstlisting}}"""
        )

    return "\n".join(sections)


def build_outputs(programs):

    out = []

    for p in programs:
        out.append(
f"""\\begin{{tcolorbox}}[myoutputbox,title=Terminal Output]
\\begin{{verbatim}}
{p.output}
\\end{{verbatim}}
\\end{{tcolorbox}}"""
        )

    return "\n".join(out)


def build_latex(exp: ExperimentData):

    latex = LATEX_TEMPLATE

    latex = latex.replace("__NO__", exp.experiment_number)
    latex = latex.replace("__HEADING__", exp.experiment_heading)
    latex = latex.replace("__DATE__", exp.date)
    latex = latex.replace("__AIM__", exp.aim)
    latex = latex.replace("__RESULT__", exp.result)

    latex = latex.replace(
        "__ALGORITHMS__",
        build_algorithms(exp.algorithms)
    )

    latex = latex.replace(
        "__PROGRAMS__",
        build_programs(exp.programs)
    )

    latex = latex.replace(
        "__OUTPUTS__",
        build_outputs(exp.programs)
    )

    return latex


# =========================================================
# API ENDPOINTS
# =========================================================

@app.post("/api/upload-process")
async def upload_process(file: UploadFile = File(...)):

    temp = Path(tempfile.mkdtemp())

    try:
        path = temp / file.filename
        path.write_bytes(await file.read())

        raw = await asyncio.to_thread(
            extract_text, path, temp
        )

        programs = extract_programs(raw)

        algorithms = []
        aim = ""

        for i, p in enumerate(programs, 1):

            output = run_program(p, i, temp)
            p.output = output

            prog_aim, algos = generate_academic(p, output)

            if not aim:
                aim = prog_aim

            algorithms.extend(algos)

        return {
            "experiment_number": "1",
            "date": "23/09/2025",
            "experiment_heading": "CPU SCHEDULING ALGORITHMS",
            "aim": aim,
            "algorithms": [a.model_dump() for a in algorithms],
            "programs": [p.model_dump() for p in programs],
            "result":
            "CPU scheduling algorithms are implemented and outputs verified successfully."
        }

    finally:
        shutil.rmtree(temp, ignore_errors=True)


@app.post("/api/generate-latex")
async def generate_latex(exp: ExperimentData):

    return {"latex": build_latex(exp)}