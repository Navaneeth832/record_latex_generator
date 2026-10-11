# =========================================================
# ENV LOAD
# =========================================================
import os
from dotenv import load_dotenv
load_dotenv()

import asyncio
import io
import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple

import fitz
import pdfplumber
import google.generativeai as genai
from groq import Groq

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from dotenv import load_dotenv

# This will look for the .env file in the root directory
load_dotenv() 


# =========================================================
# CONFIG
# =========================================================
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")


# =========================================================
# FASTAPI
# =========================================================
app = FastAPI(title="Lab Record Studio")

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
    commands: str = ""


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
    template_id: str = "template-1"
    roll_number: str = "s23a48"
    semester: str = "S7"


class TextProcessRequest(BaseModel):
    text: str = Field(min_length=1)


class QuestionProcessRequest(BaseModel):
    question: str = Field(min_length=1)


class TemplateRequest(BaseModel):
    name: str = "YOUR NAME"
    lab_name: str = "COMPUTER NETWORKS LAB"
    course_code: str = "CSL 332"
    course_name: str = "COMPUTER NETWORKS LAB"
    department: str = "COMPUTER SCIENCE AND ENGINEERING"
    institution: str = "COLLEGE OF ENGINEERING TRIVANDRUM"
    semester: str = "S7"
    academic_year: str = "2025-2026"
    submitted_to: str = "FACULTY IN CHARGE"
    submitted_by: str = "YOUR NAME"
    roll_number: str = "S23XXX"
    section: str = "A"
    experiment_title: str = ""
    date: str = ""
    contents_cycles: List["TemplateCycle"] = Field(default_factory=list)


class TemplateEntry(BaseModel):
    serial_number: int
    title: str


class TemplateCycle(BaseModel):
    cycle_number: int
    title: str
    entries: List[TemplateEntry] = Field(default_factory=list)


class ContentsTextRequest(BaseModel):
    text: str = Field(min_length=1)


class ContentsAnalysisResponse(BaseModel):
    cycles: List[TemplateCycle]
    contents_tex: str
    generated_files: List[str]


TemplateRequest.model_rebuild()


class TemplateSummary(BaseModel):
    id: str
    name: str
    description: str
    source: str
    is_customizable: bool
    preview_url: Optional[str] = None
    download_filename: str


# =========================================================
# LATEX TEMPLATE (UNCHANGED FORMAT)
# =========================================================
LATEX_TEMPLATE = r"""
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{Cycle <nombor> Programs}
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
# LLM ABSTRACTION
# =========================================================
def llm_generate(prompt: str) -> str:

    if LLM_PROVIDER == "gemini":

        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise HTTPException(500, "Missing GEMINI_API_KEY")

        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-3-flash-preview")

        res = model.generate_content(prompt)
        return res.text.strip()

    elif LLM_PROVIDER == "groq":

        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise HTTPException(500, "Missing GROQ_API_KEY")

        client = Groq(api_key=key)

        res = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        return res.choices[0].message.content.strip()

    raise HTTPException(500, "Invalid provider")


# =========================================================
# JSON SAFE EXTRACTION
# =========================================================
def extract_json(text: str):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise HTTPException(422, "Invalid AI JSON")
    return json.loads(match.group())


# =========================================================
# FILE EXTRACTION
# =========================================================
def extract_pdf(path: Path):

    text = []
    with pdfplumber.open(path) as pdf:
        for p in pdf.pages:
            text.append(p.extract_text() or "")

    joined = "\n".join(text)

    if joined.strip():
        return joined

    doc = fitz.open(path)
    return "\n".join(p.get_text() for p in doc)


def extract_text(path: Path, temp: Path):

    ext = path.suffix.lower()

    if ext == ".pdf":
        return extract_pdf(path)

    if ext in [".txt", ".bin"]:
        return path.read_bytes().decode(errors="ignore")

    if ext == ".zip":

        unzip = temp / "unzipped"
        unzip.mkdir(exist_ok=True)

        zipfile.ZipFile(path).extractall(unzip)

        data = []

        for f in unzip.rglob("*"):
            if f.is_dir():
                continue

            if f.suffix.lower() == ".pdf":
                data.append(extract_pdf(f))
            else:
                data.append(
                    f.read_bytes().decode(errors="ignore")
                )

        return "\n".join(data)

    return path.read_bytes().decode(errors="ignore")


# =========================================================
# PROGRAM PARSER
# =========================================================
def parse_programs_from_text(raw: str):

    programs = []
    title = ""
    buffer = []

    for line in raw.splitlines():

        if line.strip().startswith("###"):
            if buffer:
                programs.append(
                    ProgramData(
                        title=title,
                        code="\n".join(buffer)
                    )
                )
            title = line[3:].strip()
            buffer = []
            continue

        buffer.append(line)

    if buffer:
        programs.append(
            ProgramData(
                title=title or "Program",
                code="\n".join(buffer)
            )
        )

    if not programs:
        raise HTTPException(422, "No programs detected")

    return programs


# =========================================================
# AI GENERATION
# =========================================================
def generate_academic(program):

    prompt = f"""
        Act as a precise code-to-JSON parser. Analyze the source code provided and return ONLY a raw JSON object. The algorithm should be detailed and perfect.
        DO NOT include markdown formatting, DO NOT include ```json tags, and DO NOT include any introductory or concluding text.

        ### SCHEMA:
        {{
        "aim": "High-level goal of the program",
        "algorithms": [
            {{
            "name": "Component name",
            "steps": ["Step 1", "Step 2"]
            }}
        ],
        "commands": "Compile and run commands appropriate for this type of program (e.g. gcc program.c\\n./a.out or python3 script.py)
        if the type of program is found in the below instruction strictly follow the compilation method.
        1. Pure C Programs
        gcc filename.c (Note: You should name the program file)
        ./a.out
        2. LEX Programs
        lex filename.l (Note: You should name the program file)
        gcc lex.yy.c
        ./a.out
        3. LEX & YACC Programs
        yacc -d filename.y (Note: You should name the program file)
        lex filename.l (Note: You should name the program file)
        gcc y.tab.c lex.yy.c
        ./a.out",
        "output": "Simulated terminal output including mock inputs"
        }}

        ### CODE:
        {program.code}
        """

    data = extract_json(llm_generate(prompt))

    algos = [
        AlgorithmData(**a)
        for a in data.get("algorithms", [])
    ]

    cmds = data.get("commands", "")
    if isinstance(cmds, list):
        cmds = "\n".join(cmds)

    return data.get("aim", ""), algos, data.get("output", ""), str(cmds)


def generate_metadata(aim):
    prompt="generate a concise experiment heading based on this AIM only include text dont include other symbols like * or something else:\n\n" + aim
    res = llm_generate(prompt)
    heading = res.strip().splitlines()[0] if res else ""
    if not heading:
        heading = "Program Implementation"

    return heading, "The execution is complete, and the results have been successfully validated."


def generate_programs_from_question(question: str):
    prompt = f"""
        You are generating C lab programs from a user question.
        Return ONLY a raw JSON object, no markdown and no explanations.

        SCHEMA:
        {{
          "programs": [
            {{
              "title": "Short descriptive title",
              "code": "Complete C program source code"
            }}
          ]
        }}

        Rules:
        - Generate at least one valid C program.
        - Use clear variable names and include required headers.
        - Keep code runnable.
        - Do not include output text in this response.

        User question:
        {question}
    """

    data = extract_json(llm_generate(prompt))
    raw_programs = data.get("programs", [])

    if not isinstance(raw_programs, list) or not raw_programs:
        raise HTTPException(422, "AI did not return any programs for this question")

    programs = []
    for i, item in enumerate(raw_programs, 1):
        title = str(item.get("title", "")).strip() or f"Program {i}"
        code = str(item.get("code", "")).strip()
        if not code:
            raise HTTPException(422, f"Generated program {i} has empty code")
        programs.append(ProgramData(title=title, code=code))

    return programs


def parse_contents_structure(raw_text: str):
    prompt = f"""
        Convert the following lab-record table-of-contents text into ONLY a raw JSON object.
        Do not use markdown.

        Schema:
        {{
          "cycles": [
            {{
              "cycle_number": 1,
              "title": "Cycle title without the leading cycle number if possible",
              "entries": [
                {{
                  "serial_number": 1,
                  "title": "Experiment title"
                }}
              ]
            }}
          ]
        }}

        Rules:
        - Preserve experiment order exactly.
        - Group experiments under the correct cycle.
        - Omit empty rows.
        - Keep titles concise but faithful to the source.
        - If the source says "CYCLE 2 --- SOCKET PROGRAMMING", set cycle_number to 2 and title to "SOCKET PROGRAMMING".

        Source text:
        {raw_text}
    """

    data = extract_json(llm_generate(prompt))
    raw_cycles = data.get("cycles", [])
    if not isinstance(raw_cycles, list) or not raw_cycles:
        raise HTTPException(422, "Could not detect any cycle information from the table of contents.")

    cycles = [TemplateCycle(**cycle) for cycle in raw_cycles]
    valid_cycles = [cycle for cycle in cycles if cycle.entries]
    if not valid_cycles:
        raise HTTPException(422, "The table of contents did not include any experiment rows.")

    return valid_cycles


# =========================================================
# LATEX HELPERS
# =========================================================
def clean_step(s):
    return re.sub(r'^\s*\d+[\).\-\s]+', '', s)


def latex_escape(text):
    rep = {
        "_": r"\_",
        "&": r"\&",
        "%": r"\%",
        "#": r"\#",
        "{": r"\{",
        "}": r"\}",
    }
    for k, v in rep.items():
        text = text.replace(k, v)
    return text


def render_zip_template(template: str, values: dict):
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"__{key.upper()}__", latex_escape(str(value or "")))
    return rendered

BASE_DIR = Path(__file__).resolve().parent
BUILTIN_TEMPLATE_DIR = BASE_DIR / "builtin_templates"


def read_template_file(*parts: str):
    path = BUILTIN_TEMPLATE_DIR.joinpath(*parts)
    return path.read_text(encoding="utf-8")


def format_cycle_heading(cycle: TemplateCycle):
    title = cycle.title.strip()
    if re.match(r"^CYCLE\s+\d+", title, re.IGNORECASE):
        return title.upper()
    return f"CYCLE {cycle.cycle_number} --- {title.upper()}"


def build_template1_file_name(cycle_number: int, entry_index: int):
    return f"Expt{cycle_number}_{entry_index}_1.tex"


def build_template1_contents_tex(cycles: List[TemplateCycle]):
    lines = [
        r"\begin{center}",
        r"\vspace*{1cm}",
        r"{\LARGE \textbf{INDEX}}",
        r"\vspace{0.5cm}",
        r"\end{center}",
        r"\setlength{\LTleft}{\fill}",
        r"\setlength{\LTright}{\fill}",
        "",
        r"\begin{longtable}{|c|p{7cm}|p{1cm}|c|c|}",
        r"\hline",
        r"\textbf{SL NO.} & \centering\textbf{EXPERIMENT NAME} & \textbf{PAGE NO.} & \textbf{DATE} & \textbf{SIGNATURE} \tabularnewline",
        r"\hline",
        r"\endfirsthead",
        "",
        r"\hline",
        r"\textbf{SL NO.} & \centering\textbf{EXPERIMENT NAME} & \textbf{PAGE NO.} & \textbf{DATE} & \textbf{SIGNATURE} \tabularnewline",
        r"\hline",
        r"\endhead",
        "",
    ]

    for cycle in cycles:
        lines.append(rf"\multicolumn{{5}}{{|c|}}{{\textbf{{{latex_escape(format_cycle_heading(cycle))}}}}} \tabularnewline")
        lines.append(r"\hline")
        for entry in cycle.entries:
            lines.append(
                rf"{entry.serial_number} & {latex_escape(entry.title.upper())} &  &  & \tabularnewline \hline"
            )
        lines.append("")

    lines.append(r"\end{longtable}")
    return "\n".join(lines)


def build_template1_experiment_files(cycles: List[TemplateCycle]):
    files = {}
    include_lines = []

    for cycle in cycles:
        for entry_index, entry in enumerate(cycle.entries, 1):
            filename = build_template1_file_name(cycle.cycle_number, entry_index)
            include_lines.append(rf"\include{{{Path(filename).stem}}}")
            files[filename] = (
                f"% Auto-generated placeholder for {format_cycle_heading(cycle)}\n"
                f"% Experiment {entry.serial_number}: {entry.title}\n\n"
                f"\\section*{{{latex_escape(entry.title.upper())}}}\n"
                "% Add experiment content here.\n"
            )

    return files, include_lines


def inject_template1_main(main_template: str, include_lines: List[str]):
    cleaned = re.sub(r"^\s*\\include\{Expt[^}]+\}\s*\n?", "", main_template, flags=re.MULTILINE)
    marker = r"\include{contents}"
    if marker not in cleaned:
        raise HTTPException(500, "Template 1 main.tex is missing the contents include marker.")
    return cleaned.replace(marker, marker + "\n" + "\n".join(include_lines), 1)


def build_template_assets(template_id: str, cycles: List[TemplateCycle], base_files: dict):
    files = dict(base_files)

    if template_id == "template-1":
        experiment_files, include_lines = build_template1_experiment_files(cycles)
        files["contents.tex"] = build_template1_contents_tex(cycles)
        files["main.tex"] = inject_template1_main(files["main.tex"], include_lines)
        files.update(experiment_files)
        generated_files = ["contents.tex", "main.tex", *experiment_files.keys()]
    else:
        raise HTTPException(404, "Built-in template not found")

    return files, generated_files

BUILTIN_TEMPLATES = {
    "template-1": {
        "name": "Lab Record",
        "description": "Well-designed lab record with output boxes.",
        "download_filename": "record-template.zip",
        "files": {
            "main.tex": read_template_file("template-1", "main.tex"),
            "cover_page.tex": read_template_file("template-1", "cover_page.tex"),
            "follow_page.tex": read_template_file("template-1", "follow_page.tex"),
            "contents.tex": read_template_file("template-1", "contents.tex"),
        },
    },
}


def build_builtin_template_summary(template_id: str):
    template = BUILTIN_TEMPLATES[template_id]
    return TemplateSummary(
        id=template_id,
        name=template["name"],
        description=template["description"],
        source="builtin",
        is_customizable=True,
        preview_url=f"/api/templates/{template_id}/preview",
        download_filename=template["download_filename"],
    )


def list_template_summaries():
    return [build_builtin_template_summary("template-1")]


def build_builtin_preview_pdf(template_id: str):
    if template_id == "template-1":
        preview_path = BASE_DIR / "builtin_templates" / "Navaneeth_modern_record.pdf"
    else:
        raise HTTPException(404, "Template not found")
    
    if not preview_path.exists():
        raise HTTPException(404, f"Preview PDF not found for {template_id}")
    
    return preview_path.read_bytes()


def get_builtin_template_files(template_id: str):
    if template_id not in BUILTIN_TEMPLATES:
        raise HTTPException(404, "Built-in template not found")
    return {
        "main.tex": read_template_file(template_id, "main.tex"),
        "cover_page.tex": read_template_file(template_id, "cover_page.tex"),
        "follow_page.tex": read_template_file(template_id, "follow_page.tex"),
        "contents.tex": read_template_file(template_id, "contents.tex"),
    }


def analyze_contents_for_template(template_id: str, raw_text: str):
    cycles = parse_contents_structure(raw_text)
    base_files = get_builtin_template_files(template_id)
    rendered_files, generated_files = build_template_assets(template_id, cycles, base_files)
    return ContentsAnalysisResponse(
        cycles=cycles,
        contents_tex=rendered_files["contents.tex"],
        generated_files=generated_files,
    )


def build_template_zip(payload: TemplateRequest, template_id: str = "template-1", template_files: Optional[dict] = None):
    values = payload.model_dump()
    files = dict(template_files or get_builtin_template_files(template_id))

    if payload.contents_cycles:
        files, _ = build_template_assets(template_id, payload.contents_cycles, files)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_name, template in files.items():
            zf.writestr(file_name, render_zip_template(template, values))

        logo_path = BASE_DIR / "figures" / "cet_logo.jpeg"
        
        if logo_path.exists():
            zf.write(logo_path, arcname="figures/cet_logo.jpeg")
        else:
            print(f"Lowkey error: Logo not found at {logo_path} ðŸ’€")

    buffer.seek(0)
    return buffer


# =========================================================
# LATEX BUILDERS
# =========================================================
def build_algorithms(algorithms):

    blocks = []

    for algo in algorithms:

        steps = "\n".join(
            f"    \\item {latex_escape(clean_step(s))}"
            for s in algo.steps
        )

        blocks.append(
f"""\\subsection*{{{latex_escape(algo.name)}}}
\\begin{{enumerate}}[label=\\arabic*.]
{steps}
\\end{{enumerate}}"""
        )

    return "\n".join(blocks)


def build_programs(programs):

    out = []

    for i, p in enumerate(programs, 1):
        out.append(
f"""\\subsection*{{Listing {i}: {p.title}}}
\\begin{{lstlisting}}[language=C]
{p.code}
\\end{{lstlisting}}"""
        )

    return "\n".join(out)


def format_roll_no(roll_str: Optional[str]) -> str:
    if not roll_str or not str(roll_str).strip():
        return "s23a48"
    s = str(roll_str).strip().lower().split('@')[0]
    return s if s else "s23a48"


def format_sem_dir(sem_str: Optional[str]) -> str:
    if not sem_str or not str(sem_str).strip():
        return "s7"
    s = str(sem_str).strip().lower()
    match = re.search(r'\d+', s)
    if match:
        return f"s{match.group(0)}"
    return s if s else "s7"


def build_outputs(programs, exp_number, roll_number="s23a48", semester="s7"):
    user_str = format_roll_no(roll_number)
    sem_str = format_sem_dir(semester)
    prompt_prefix = f"{user_str}@Server-2:~/{sem_str}$"

    out = []

    for i, p in enumerate(programs, 1):
        raw_cmds = (p.commands or "").strip()
        if not raw_cmds:
            exp_num = exp_number or "1"
            raw_cmds = f"gcc {exp_num}.c\n./a.out"

        cmd_lines = [c.strip() for c in raw_cmds.splitlines() if c.strip()]
        terminal_lines = [f"{prompt_prefix} {cmd}" for cmd in cmd_lines]

        output_content = (p.output or "").strip()
        if output_content:
            terminal_lines.append(output_content)

        full_terminal = "\n".join(terminal_lines)

        out.append(
f"""\\begin{{tcolorbox}}[myoutputbox,title=Terminal Output]
\\begin{{verbatim}}
{full_terminal}
\\end{{verbatim}}
\\end{{tcolorbox}}"""
        )

    return "\n".join(out)


def build_latex(exp: ExperimentData):
    # Template 1 (Navaneeth record)
    latex = LATEX_TEMPLATE
    latex = latex.replace("<nombor>", exp.experiment_number[0] if exp.experiment_number else "1")
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
        build_outputs(exp.programs, str(exp.experiment_number), exp.roll_number, exp.semester)
    )

    return latex


# =========================================================
# PIPELINE
# =========================================================
def process_programs(programs):

    algorithms = []
    aim = ""

    for p in programs:

        prog_aim, algos, output, commands = generate_academic(p)

        p.output = output
        p.commands = commands

        if not aim:
            aim = prog_aim

        algorithms.extend(algos)

    heading, result = generate_metadata(aim)

    return {
        "experiment_number": "1",
        "date": "16/02/2026",
        "experiment_heading": heading,
        "aim": aim,
        "algorithms": [a.model_dump() for a in algorithms],
        "programs": [p.model_dump() for p in programs],
        "result": result,
    }


# =========================================================
# API ENDPOINTS
# =========================================================
@app.post("/api/process-text")
async def process_text(payload: TextProcessRequest):
    programs = parse_programs_from_text(payload.text)
    return process_programs(programs)


@app.post("/api/process-question")
async def process_question(payload: QuestionProcessRequest):
    programs = generate_programs_from_question(payload.question)
    return process_programs(programs)


@app.post("/api/upload-process")
async def upload_process(file: UploadFile = File(...)):

    temp = Path(tempfile.mkdtemp())

    try:
        path = temp / file.filename
        path.write_bytes(await file.read())

        raw = await asyncio.to_thread(
            extract_text, path, temp
        )

        programs = parse_programs_from_text(raw)

        return process_programs(programs)

    finally:
        shutil.rmtree(temp, ignore_errors=True)


@app.post("/api/generate-latex")
async def generate_latex(exp: ExperimentData):
    return {"latex": build_latex(exp)}


@app.get("/api/templates", response_model=List[TemplateSummary])
async def get_templates():
    return list_template_summaries()


@app.post("/api/templates/{template_id}/analyze-contents-text", response_model=ContentsAnalysisResponse)
async def analyze_template_contents_text(template_id: str, payload: ContentsTextRequest):
    if template_id not in BUILTIN_TEMPLATES:
        raise HTTPException(400, "Contents analysis is only available for built-in templates.")
    return analyze_contents_for_template(template_id, payload.text)


@app.post("/api/templates/{template_id}/analyze-contents-upload", response_model=ContentsAnalysisResponse)
async def analyze_template_contents_upload(template_id: str, file: UploadFile = File(...)):
    if template_id not in BUILTIN_TEMPLATES:
        raise HTTPException(400, "Contents analysis is only available for built-in templates.")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(400, "Image OCR is not available in the current backend. Paste the contents text or upload a PDF.")

    temp = Path(tempfile.mkdtemp())
    try:
        path = temp / (file.filename or "contents-upload")
        path.write_bytes(await file.read())
        raw_text = await asyncio.to_thread(extract_text, path, temp)
        return analyze_contents_for_template(template_id, raw_text)
    finally:
        shutil.rmtree(temp, ignore_errors=True)


@app.get("/api/templates/{template_id}/preview")
async def get_template_preview(template_id: str):
    if template_id not in BUILTIN_TEMPLATES:
        raise HTTPException(404, "Preview is only available for built-in templates.")

    preview_bytes = build_builtin_preview_pdf(template_id)

    headers = {"Content-Disposition": f'inline; filename="{template_id}-preview.pdf"'}
    return StreamingResponse(io.BytesIO(preview_bytes), media_type="application/pdf", headers=headers)


@app.post("/api/templates/{template_id}/download")
async def download_selected_template(template_id: str, payload: TemplateRequest):
    if template_id not in BUILTIN_TEMPLATES:
        raise HTTPException(404, "Template not found")

    zip_buffer = build_template_zip(payload, template_id, get_builtin_template_files(template_id))
    filename = build_builtin_template_summary(template_id).download_filename

    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(zip_buffer, media_type="application/zip", headers=headers)


@app.post("/api/download-template")
async def download_template(payload: TemplateRequest):
    zip_buffer = build_template_zip(payload, "template-1")
    headers = {"Content-Disposition": 'attachment; filename="latex_template.zip"'}
    return StreamingResponse(zip_buffer, media_type="application/zip", headers=headers)

@app.get("/health")
def health():
    return {"status":"healthy"}
    

