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


class TextProcessRequest(BaseModel):
    text: str = Field(min_length=1)


class QuestionProcessRequest(BaseModel):
    question: str = Field(min_length=1)


class TemplateRequest(BaseModel):
    name: str = ""
    lab_name: str = ""
    course_code: str = ""
    course_name: str = ""
    department: str = ""
    institution: str = ""
    semester: str = ""
    academic_year: str = ""
    submitted_to: str = ""
    submitted_by: str = ""
    roll_number: str = ""
    section: str = ""
    experiment_title: str = ""
    date: str = ""


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

ZIP_MAIN_TEMPLATE = r"""
\documentclass[12pt,a4paper]{report}
\usepackage{listings}
\usepackage{xcolor}
\usepackage[utf8]{inputenc}

% --- C code listing style ---
\lstdefinestyle{cstyle}{
    language=C,
    basicstyle=\ttfamily\footnotesize,
    backgroundcolor=\color{gray!5},
    numbers=left,
    numberstyle=\tiny\color{gray},
    stepnumber=1,
    numbersep=8pt,
    frame=single,
    rulecolor=\color{gray!50},
    showstringspaces=false,
    breaklines=true,
    keywordstyle=\color{blue!80!black}\bfseries,
    commentstyle=\color{green!40!black}\itshape,
    stringstyle=\color{orange!70!black},
    tabsize=4,
    captionpos=b,
    xleftmargin=10pt,
    xrightmargin=5pt
}

\usepackage[most]{tcolorbox}

\tcbuselibrary{listings,skins,breakable}
\usepackage{graphicx}
\usepackage{adjustbox}
\usepackage{amsmath}
\usepackage{pdflscape}
\usepackage{fancyhdr}
\usepackage{cite}
\usepackage{calc}
\usepackage{framed}
\usepackage{a4wide}
\usepackage{float}
\usepackage{epsfig}
\usepackage{longtable}
\usepackage{enumerate}
\usepackage{afterpage}
\usepackage{xcolor}
\usepackage{multirow}
\usepackage{ragged2e}
\usepackage{gensymb}
\usepackage{amsfonts} 
\usepackage[left=3.5cm,top=1.5cm,right=3cm,bottom=2cm]{geometry}
\usepackage{setspace}           
\usepackage{float}
\usepackage{txfonts}
\usepackage{lipsum}
\usepackage{tikz}
\usetikzlibrary{positioning,arrows,calc,shapes}
\usepackage{listings}
\usepackage{csvsimple}
\usepackage{booktabs}
\usepackage[most]{tcolorbox}
\usepackage{amsmath}
\usepackage{graphicx}
\usepackage{listings}
\usepackage{geometry}
\usepackage{enumitem}
\usepackage{fancyhdr}

\tcbset{
    myoutputbox/.style={
        colback=blue!3!white,      % Softer background
        colframe=blue!60!black,    % Slightly lighter border
        boxrule=0.6pt,             % Thinner border
        arc=3pt,                   % Gentle rounded corners
        left=4pt,                  % Reduced padding
        right=4pt,
        top=4pt,
        bottom=4pt,
        fonttitle=\bfseries\small, % Slightly smaller title
        fontupper=\small,          % Make text inside smaller
        coltitle=black,            % Title text color
    }
}
\usepackage{tcolorbox}
\tcbuselibrary{listings, breakable}

\tcbset{
    terminalstyle/.style={
        enhanced,
        breakable,
        colback=black,
        coltext=white,
        colframe=black,
        boxrule=0.4pt,
        sharp corners,
        fontupper=\ttfamily\footnotesize,
        left=6pt,
        right=6pt,
        top=4pt,
        bottom=4pt,
        width=\linewidth,
        arc=2pt,
        before skip=6pt,
        after skip=6pt,
        listing only,
        listing options={
            basicstyle=\ttfamily\footnotesize,
            breaklines=true,
            breakatwhitespace=false,
            showstringspaces=false,
        }
    }
}




% --- Define SQL style ---
\lstdefinestyle{customsql}{
  language=SQL,
  keywordstyle=\color{magenta}\bfseries,
  commentstyle=\color{green!60!black}\itshape,
  stringstyle=\color{blue},
  basicstyle=\ttfamily\small,
  breaklines=true,
  showstringspaces=false,
  columns=fullflexible
}

\lstdefinestyle{psql}{
    basicstyle=\ttfamily\small,   % monospace, smaller font
    columns=fullflexible,         % keeps monospace alignment
    keepspaces=true,       
    xleftmargin=0pt, % preserve spaces
    showstringspaces=false,
    breaklines=false,             % don’t wrap lines
    aboveskip=0pt,
    belowskip=0pt,
    lineskip=-1pt                 % reduce vertical space between rows
}

\csvstyle{escapeunderscores}{%
    table head=\toprule, 
    table foot=\bottomrule,
    filter string replace={_}{\_}
}
% Function to draw attributes around a central node
\tikzset{
  entity/.style={draw, rectangle, minimum width=2cm, minimum height=1cm},
  attribute/.style={draw, ellipse, minimum width=1.5cm, minimum height=0.2cm},
  relation/.style={draw, diamond, minimum width=2.5cm, minimum height=1.2cm},
  line/.style={-},
}
\newcommand{\drawattributes}[5]{
  % #1 = central node name
  % #2 = comma-separated list of attributes
  % #3 = total number of attributes
  % #4 = How many first attributes are Primary Keys
  % #5 = manual positions: 0 for auto, 1 for manual (then define positions separately)
  
  % Set the total number of attributes from parameter
  \pgfmathsetmacro{\totalattrs}{#3}
  \pgfmathsetmacro{\pkcount}{#4}
  
  \foreach \attr [count=\i] in {#2} {
    % Create attribute node name
    \edef\attrname{#1_attr\i}
    
    % Check if manual positioning is requested for this attribute
    \def\usemanual{0}
    \ifnum\i=1
      \ifnum#5=1 \def\usemanual{1}\fi
    \fi
    \ifnum\i=2
      \ifnum#5=2 \def\usemanual{1}\fi
    \fi
    \ifnum\i=3
      \ifnum#5=3 \def\usemanual{1}\fi
    \fi
    \ifnum\i=4
      \ifnum#5=4 \def\usemanual{1}\fi
    \fi
    \ifnum\i=5
      \ifnum#5=5 \def\usemanual{1}\fi
    \fi
    
    % Position attributes
    \ifnum\usemanual=1
      % Use manual positioning - check if coordinates are defined
      \@ifundefined{#1attr\i x}{
        % Manual requested but no coordinates defined, use auto
        \pgfmathtruncatemacro{\currentpos}{\i}
        \ifnum\currentpos=1
            \coordinate (\attrname-pos) at ($(#1) + (-1.2cm,2.5cm)$);
            
        \else\ifnum\currentpos=2
            \coordinate (\attrname-pos) at ($(#1) + (1.2cm,2.5cm)$);
            
        \else\ifnum\currentpos=3
            \coordinate (\attrname-pos) at ($(#1) + (-2.2cm,1.75cm)$);

        \else
          \coordinate (\attrname-pos) at ($(#1) + (0cm,-2.5cm)$);
        \fi\fi\fi
      }{
        % Use the defined manual coordinates
        \coordinate (\attrname-pos) at ($(#1) + (\csname #1attr\i x\endcsname,\csname #1attr\i y\endcsname)$);
      }
    \else
      % Use automatic positioning (original logic)
      \pgfmathtruncatemacro{\currentpos}{\i}
      
      % Define positions for first 8 attributes in structured layout
      \ifnum\currentpos=1
        \coordinate (\attrname-pos) at ($(#1) + (-1.2cm,2.5cm)$);
      \else\ifnum\currentpos=2
        \coordinate (\attrname-pos) at ($(#1) + (1.2cm,2.5cm)$);
      \else\ifnum\currentpos=3
          \ifnum\totalattrs = 3
              \coordinate (\attrname-pos) at ($(#1) + (0cm,+2.5cm)$);
          \else
              \coordinate (\attrname-pos) at ($(#1) + (-2.2cm,1.75cm)$);
          \fi
        
      \else\ifnum\currentpos=4
        \coordinate (\attrname-pos) at ($(#1) + (2.2cm,1.75cm)$);
      \else\ifnum\currentpos=5
        \coordinate (\attrname-pos) at ($(#1) + (-3.5cm,-1.2cm)$);
      \else\ifnum\currentpos=6
        \coordinate (\attrname-pos) at ($(#1) + (3.5cm,-1.2cm)$);
      \else\ifnum\currentpos=7
          \ifnum\totalattrs = 7
              \coordinate (\attrname-pos) at ($(#1) + (0cm,-2.5cm)$);
          \else
              \coordinate (\attrname-pos) at ($(#1) + (-1.8cm,-2.5cm)$);
          \fi
      \else\ifnum\currentpos=8
        \coordinate (\attrname-pos) at ($(#1) + (1.8cm,-2.5cm)$);
      \else
        % For 9+ attributes, place in outer ring avoiding cardinal directions
        \pgfmathtruncatemacro{\extrapos}{\currentpos-8}
        \pgfmathtruncatemacro{\extraangle}{30 + (\extrapos-1)*45}
        \coordinate (\attrname-pos) at ($(#1) + (\extraangle:4.5cm)$);
      \fi\fi\fi\fi\fi\fi\fi\fi
    \fi
    
    % Check if attribute is a Primary Key (underline it if yes)
    \ifnum\i>\pkcount
      \node[attribute] (\attrname) at (\attrname-pos) {\attr};
    \else
      \node[attribute] (\attrname) at (\attrname-pos) {\underline{\attr}};
    \fi
    
    % Draw line from central node to attribute
    \draw[line] (#1) -- (\attrname);
  }
}

% Helper command to set manual position
\newcommand{\setmanualpos}[4]{
  % #1 = entity name
  % #2 = attribute number (1,2,3,...)
  % #3 = x coordinate
  % #4 = y coordinate
  \expandafter\def\csname #1attr#2x\endcsname{#3}
  \expandafter\def\csname #1attr#2y\endcsname{#4}
}

\newcommand{\Usefont}[1]{\fontfamily{#1}\selectfont}

\usepackage{lscape} % for landscape tables
\renewcommand{\baselinestretch}{1.7} 

\usepackage{blindtext}
\usepackage{xpatch}
\usepackage{url}
\usepackage{leqno}
\usepackage{subcaption}
\linespread{1.5}
\usepackage[intoc, english]{nomencl}
\hyphenpenalty=5000
\tolerance=1000
\usepackage[nottoc]{tocbibind}

% ******* References config *********
\bibliographystyle{IEEEtran}   % On some TeX systems this works
%\bibliographystyle{ieeetr}      % While on others this works
							% Uncomment and test if your references don't cite
							% correctly
\renewcommand{\bibname}{References}

\begin{document}

\gdef \sem{__SEMESTER__ Semester}
\gdef \courseCode{__COURSE_CODE__} %Course Code
\gdef \courseName{__COURSE_NAME__} %Course Code



\gdef \deptName{__DEPARTMENT__} %Department

\gdef \studentname{__NAME__}	 %student name
\gdef \ktuid{__ROLL_NUMBER__}%KTU Reg No
\gdef \class {S6 CSE}
\gdef \batch {__SECTION__}

\gdef \collegeName{__INSTITUTION__}
\gdef \collegePlace{Thiruvananthapuram - 695016}
\gdef \year{__ACADEMIC_YEAR__}


\include {cover_page}
\include{follow_page}
\include{contents}
\include{Expt2_1_1}
\include{Expt2_1_2}
\include{Expt2_2_1}
\include{Expt2_2_2}
\include{Expt3_1}
\include{Expt3_2}
\include{Expt3_3}
\include{Expt3_4}
\vspace{2cm}
% \gdef \month{December}
\end{document}
"""

ZIP_COVER_TEMPLATE = r"""
\thispagestyle{empty}
\begin{center}

% College Name
{\Large \textbf{\MakeUppercase{\collegeName}}}\\
\vspace{10pt}
{\large \textbf{\MakeUppercase{\collegePlace}}}\\[1cm]

% Logo
\includegraphics[width=0.5\textwidth]{figures/cet_logo.jpeg}\\[1cm]

% Department
{\Large \textbf{DEPARTMENT OF}}\\
\vspace{10pt}
{\Large \textbf{\MakeUppercase{\deptName}}}\\[1cm]

% Course details
{\Large \textbf{\sem}}\\
\vspace{10pt}
{\Large \textbf{\courseCode  : \courseName}}


% Name and KTU ID
\vspace{75pt}



\noindent
\hspace*{0.05\textwidth}
\begin{minipage}{0.5\textwidth}
\noindent
\Large \makebox[\textwidth][l]{\textbf{Name} : \textcolor{black}{\fontseries{sb}\selectfont \MakeUppercase{\studentname}}}


\Large \textbf{KTU ID} : \textcolor{black}{\fontseries{sb}\selectfont \MakeUppercase{\ktuid}}


\end{minipage}

\vspace*{\fill}
\begin{center}
\resizebox{\textwidth}{!}{\Large\textbf{APJ ABDUL KALAM TECHNOLOGICAL UNIVERSITY}}\\
{\Large\textbf{\year}}
\end{center}

\end{center}
"""

ZIP_FOLLOW_TEMPLATE = r"""
\thispagestyle{empty}
\begin{center}

% College Name
{\Large \textbf{COLLEGE OF ENGINEERING TRIVANDRUM}}\\
\vspace{10pt}
{\large \textbf{THIRUVANANTHAPURAM-695016}}\\[1cm]

% Logo
\includegraphics[width=0.25\textwidth]{figures/cet_logo.jpeg}\\[1cm]

% Department
{\Large \textbf{DEPARTMENT OF}}\\
\vspace{10pt}
{\Large \textbf{\MakeUppercase{\deptName}}}\\[1cm]

% Course details
{\Large \textbf{\sem}}\\
\vspace{10pt}
{\Large \textbf{\courseCode : \courseName}}\\[2cm]

% Certification Text
\raggedright
Certified that this is a bonafide record of the work done
by \textcolor{black}{\fontseries{sb}\selectfont \MakeUppercase{\studentname \\ (\ktuid)}} of \textbf{\class (\batch)} class in the \textbf{\courseName} during the year \year.

\noindent\rule{\textwidth}{0.4pt}\\
\vspace*{\fill}
\textbf{External Examiner}
\vspace{3cm}
\hfill \textbf{Faculty in Charge}\\

\vspace*{\fill}

\end{center}

"""

ZIP_CONTENTS_TEMPLATE = r"""
\begin{center}
\vspace*{1cm}
{\LARGE \textbf{INDEX}}
\vspace{0.5cm}
\end{center}
\setlength{\LTleft}{\fill}
\setlength{\LTright}{\fill}

\begin{longtable}{|c|p{7cm}|p{1cm}|c|c|}
\hline
\textbf{SL NO.} & \centering\textbf{EXPERIMENT NAME} & \textbf{PAGE NO.} & \textbf{DATE} & \textbf{SIGNATURE} \tabularnewline
\hline
\endfirsthead

\hline
\textbf{SL NO.} & \centering\textbf{EXPERIMENT NAME} & \textbf{PAGE NO.} & \textbf{DATE} & \textbf{SIGNATURE} \tabularnewline
\hline
\endhead

\multicolumn{5}{|c|}{\textbf{CYCLE I}} \tabularnewline
\hline
1 & NETWORK CONFIGURATION AND LINUX COMMANDS & 1 &  & \tabularnewline \hline
2 & NETWORK PROGRAMMING SYSTEM CALLS IN LINUX &  &  & \tabularnewline \hline

\multicolumn{5}{|c|}{\textbf{CYCLE II}} \tabularnewline
\hline
3 & TCP CLIENT-SERVER SOCKET PROGRAMMING &  &  & \tabularnewline \hline
4 & TCP MULTI-USER CHAT SERVER &  &  & \tabularnewline \hline
5 & UDP CLIENT-SERVER SOCKET PROGRAMMING &  &  & \tabularnewline \hline
6 & UDP CONCURRENT TIME SERVER &  &  & \tabularnewline \hline
7 & FILE TRANSFER PROTOCOL IMPLEMENTATION &  &  & \tabularnewline \hline

\multicolumn{5}{|c|}{\textbf{CYCLE III}} \tabularnewline
\hline
8 & STOP-AND-WAIT PROTOCOL &  &  & \tabularnewline \hline
9 & STOP-AND-WAIT ARQ &  &  & \tabularnewline \hline
10 & GO-BACK-N ARQ &  &  & \tabularnewline \hline
11 & SELECTIVE REPEAT ARQ &  &  & \tabularnewline \hline

\multicolumn{5}{|c|}{\textbf{CYCLE IV}} \tabularnewline
\hline
12 & DISTANCE VECTOR ROUTING &  &  & \tabularnewline \hline
13 & LINK STATE ROUTING &  &  & \tabularnewline \hline

\multicolumn{5}{|c|}{\textbf{CYCLE V}} \tabularnewline
\hline
14 & LEAKY BUCKET CONGESTION CONTROL &  &  & \tabularnewline \hline

\multicolumn{5}{|c|}{\textbf{CYCLE VI}} \tabularnewline
\hline
15 & WIRESHARK PACKET ANALYSIS &  &  & \tabularnewline \hline
16 & TCP THREE-WAY HANDSHAKE &  &  & \tabularnewline \hline
17 & WIRESHARK TOOL FEATURES &  &  & \tabularnewline \hline

\multicolumn{5}{|c|}{\textbf{CYCLE VII}} \tabularnewline
\hline
18 & NETWORK SERVICES STUDY &  &  & \tabularnewline \hline

\multicolumn{5}{|c|}{\textbf{CYCLE VIII}} \tabularnewline
\hline
19 & NS2 SIMULATOR STUDY &  &  & \tabularnewline \hline

\end{longtable}
"""

ZIP_MAIN_TEMPLATE_ALT = r"""
\documentclass[12pt,a4paper]{report}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{xcolor}
\usepackage{graphicx}
\usepackage{geometry}
\usepackage{titlesec}
\usepackage{fancyhdr}
\usepackage{listings}
\usepackage[most]{tcolorbox}
\usepackage{enumitem}
\usepackage{longtable}
\usepackage{booktabs}
\usepackage{tikz}
\usepackage{setspace}
\geometry{left=3cm,right=2.6cm,top=1.8cm,bottom=2.2cm}
\linespread{1.35}

\definecolor{brandnavy}{HTML}{0E2A47}
\definecolor{brandteal}{HTML}{0E7490}
\definecolor{softpanel}{HTML}{F4F8FB}

\titleformat{\chapter}[display]
  {\normalfont\bfseries\color{brandnavy}}
  {\filleft\Large LAB RECORD}
  {0.4em}
  {\titlerule\vspace{0.8ex}\Huge}

\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\textcolor{brandnavy}{\courseCode}}
\fancyhead[R]{\textcolor{brandnavy}{\studentname}}
\fancyfoot[C]{\thepage}

\lstdefinestyle{recordstyle}{
    language=C,
    basicstyle=\ttfamily\footnotesize,
    backgroundcolor=\color{softpanel},
    numbers=left,
    numberstyle=\tiny\color{gray},
    frame=single,
    rulecolor=\color{brandteal},
    breaklines=true,
    showstringspaces=false,
    keywordstyle=\color{brandnavy}\bfseries,
    commentstyle=\color{brandteal},
    stringstyle=\color{orange!70!black}
}
\lstset{style=recordstyle}

\tcbset{
  modernoutput/.style={
    enhanced,
    breakable,
    colback=brandnavy,
    colframe=brandteal,
    coltext=white,
    boxrule=0.6pt,
    arc=2pt,
    left=5pt,right=5pt,top=5pt,bottom=5pt,
    fontupper=\ttfamily\footnotesize
  }
}

\begin{document}

\gdef \sem{__SEMESTER__ Semester}
\gdef \courseCode{__COURSE_CODE__}
\gdef \courseName{__COURSE_NAME__}
\gdef \deptName{__DEPARTMENT__}
\gdef \studentname{__NAME__}
\gdef \ktuid{__ROLL_NUMBER__}
\gdef \class {S6 CSE}
\gdef \batch {__SECTION__}
\gdef \collegeName{__INSTITUTION__}
\gdef \collegePlace{Thiruvananthapuram - 695016}
\gdef \year{__ACADEMIC_YEAR__}

\include{cover_page}
\include{follow_page}
\include{contents}
\include{Expt2_1_1}
\include{Expt2_1_2}
\include{Expt2_2_1}
\include{Expt2_2_2}
\include{Expt3_1}
\include{Expt3_2}
\include{Expt3_3}
\include{Expt3_4}

\end{document}
"""

ZIP_COVER_TEMPLATE_ALT = r"""
\thispagestyle{empty}
\begin{center}
\vspace*{0.6cm}
{\fontsize{22}{26}\selectfont \textbf{\MakeUppercase{\collegeName}}}\\[0.25cm]
{\large \textbf{\MakeUppercase{\collegePlace}}}\\[1.1cm]

\begin{tikzpicture}
\fill[cyan!8] (0,0) circle (2.2cm);
\draw[line width=1pt,color=cyan!40!black] (0,0) circle (2.2cm);
\node at (0,0) {\includegraphics[width=2.5cm]{figures/cet_logo.jpeg}};
\end{tikzpicture}\\[1cm]

{\Large\textbf{LAB RECORD}}\\[0.25cm]
{\large\textbf{\courseCode\ : \courseName}}\\[0.6cm]
\rule{0.72\textwidth}{0.8pt}\\[0.5cm]
{\Large\textbf{DEPARTMENT OF \MakeUppercase{\deptName}}}\\[0.35cm]
{\large\textbf{\sem}}\\[1.1cm]

\begin{tcolorbox}[colback=cyan!4,colframe=cyan!45!black,width=0.88\textwidth,arc=3pt]
\large \textbf{Student Name:} \MakeUppercase{\studentname}\\[0.35cm]
\large \textbf{KTU ID:} \MakeUppercase{\ktuid}\\[0.35cm]
\large \textbf{Batch / Section:} \batch\\[0.35cm]
\large \textbf{Academic Year:} \year
\end{tcolorbox}

\vfill
{\large \textbf{APJ ABDUL KALAM TECHNOLOGICAL UNIVERSITY}}\\[0.2cm]
{\large \textbf{\year}}
\end{center}
"""

ZIP_FOLLOW_TEMPLATE_ALT = r"""
\thispagestyle{empty}
\begin{center}
{\Large \textbf{\MakeUppercase{\collegeName}}}\\
\vspace{6pt}
{\large \textbf{\MakeUppercase{\collegePlace}}}\\[0.7cm]

\begin{tikzpicture}
\fill[brandnavy!10] (0,0) circle (1.5cm);
\draw[line width=0.8pt,color=brandteal] (0,0) circle (1.5cm);
\node at (0,0) {\includegraphics[width=1.8cm]{figures/cet_logo.jpeg}};
\end{tikzpicture}\\[0.8cm]

{\Large \textbf{CERTIFICATE}}\\[0.8cm]
\end{center}

\noindent
This is to certify that this record belongs to \textbf{\MakeUppercase{\studentname}} (\textbf{\ktuid}) of \textbf{\class\ (\batch)} and contains the bonafide work carried out for the course \textbf{\courseCode\ : \courseName} in the Department of \textbf{\MakeUppercase{\deptName}} during the academic year \textbf{\year}.\\[2cm]

\begin{flushright}
\textbf{Faculty in Charge}\\[2.4cm]
\textbf{Head of Department}
\end{flushright}

\vfill
\noindent\rule{\textwidth}{0.6pt}\\
\textbf{External Examiner}
"""

ZIP_CONTENTS_TEMPLATE_ALT = r"""
\begin{center}
\vspace*{0.6cm}
{\Huge \textbf{LAB INDEX}}\\[0.5cm]
\rule{0.32\textwidth}{0.8pt}
\end{center}

\setlength{\LTleft}{0pt}
\setlength{\LTright}{0pt}

\begin{longtable}{|c|p{7.4cm}|c|c|c|}
\hline
\textbf{SL NO.} & \centering\textbf{EXPERIMENT NAME} & \textbf{PAGE} & \textbf{DATE} & \textbf{SIGN} \tabularnewline
\hline
\endfirsthead
\hline
\textbf{SL NO.} & \centering\textbf{EXPERIMENT NAME} & \textbf{PAGE} & \textbf{DATE} & \textbf{SIGN} \tabularnewline
\hline
\endhead

\multicolumn{5}{|c|}{\textbf{CYCLE I}} \tabularnewline \hline
1 & NETWORK CONFIGURATION AND LINUX COMMANDS & 1 &  &  \tabularnewline \hline
2 & NETWORK PROGRAMMING SYSTEM CALLS IN LINUX &  &  &  \tabularnewline \hline
\multicolumn{5}{|c|}{\textbf{CYCLE II}} \tabularnewline \hline
3 & TCP CLIENT-SERVER SOCKET PROGRAMMING &  &  &  \tabularnewline \hline
4 & TCP MULTI-USER CHAT SERVER &  &  &  \tabularnewline \hline
5 & UDP CLIENT-SERVER SOCKET PROGRAMMING &  &  &  \tabularnewline \hline
6 & UDP CONCURRENT TIME SERVER &  &  &  \tabularnewline \hline
7 & FILE TRANSFER PROTOCOL IMPLEMENTATION &  &  &  \tabularnewline \hline
\multicolumn{5}{|c|}{\textbf{CYCLE III}} \tabularnewline \hline
8 & STOP-AND-WAIT PROTOCOL &  &  &  \tabularnewline \hline
9 & STOP-AND-WAIT ARQ &  &  &  \tabularnewline \hline
10 & GO-BACK-N ARQ &  &  &  \tabularnewline \hline
11 & SELECTIVE REPEAT ARQ &  &  &  \tabularnewline \hline
\multicolumn{5}{|c|}{\textbf{CYCLE IV}} \tabularnewline \hline
12 & DISTANCE VECTOR ROUTING &  &  &  \tabularnewline \hline
13 & LINK STATE ROUTING &  &  &  \tabularnewline \hline
\multicolumn{5}{|c|}{\textbf{CYCLE V}} \tabularnewline \hline
14 & LEAKY BUCKET CONGESTION CONTROL &  &  &  \tabularnewline \hline
\multicolumn{5}{|c|}{\textbf{CYCLE VI}} \tabularnewline \hline
15 & WIRESHARK PACKET ANALYSIS &  &  &  \tabularnewline \hline
16 & TCP THREE-WAY HANDSHAKE &  &  &  \tabularnewline \hline
17 & WIRESHARK TOOL FEATURES &  &  &  \tabularnewline \hline
\multicolumn{5}{|c|}{\textbf{CYCLE VII}} \tabularnewline \hline
18 & NETWORK SERVICES STUDY &  &  &  \tabularnewline \hline
\multicolumn{5}{|c|}{\textbf{CYCLE VIII}} \tabularnewline \hline
19 & NS2 SIMULATOR STUDY &  &  &  \tabularnewline \hline
\end{longtable}
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
            model="llama-3.3-70b-versatile",
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
        Act as a precise code-to-JSON parser. Analyze the C code provided and return ONLY a raw JSON object. The algorithm should be detailed and perfect.
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
        "output": "Simulated terminal output including mock inputs"
        }}

        ### CODE:
        {program.code}
        """

    data = extract_json(llm_generate(prompt))

    algos = [
        AlgorithmData(**a)
        for a in data["algorithms"]
    ]

    return data["aim"], algos, data["output"]


def generate_metadata(aim):
    prompt="generate a concise experiment heading based on this AIM:\n\n" + aim
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
TEMPLATE_LIBRARY_DIR = BASE_DIR / "template_library"
UPLOADED_TEMPLATE_DIR = TEMPLATE_LIBRARY_DIR / "uploads"

BUILTIN_TEMPLATES = {
    "template-1": {
        "name": "Template 1 - Classic Record",
        "description": "The original bundled lab-record design already present in the backend.",
        "download_filename": "template-1-classic-record.zip",
        "files": {
            "main.tex": ZIP_MAIN_TEMPLATE,
            "cover_page.tex": ZIP_COVER_TEMPLATE,
            "follow_page.tex": ZIP_FOLLOW_TEMPLATE,
            "contents.tex": ZIP_CONTENTS_TEMPLATE,
        },
    },
    "template-2": {
        "name": "Template 2 - Modern Record",
        "description": "A second built-in record template with a cleaner cover page, circular logo section, and updated table styling.",
        "download_filename": "template-2-modern-record.zip",
        "files": {
            "main.tex": ZIP_MAIN_TEMPLATE_ALT,
            "cover_page.tex": ZIP_COVER_TEMPLATE_ALT,
            "follow_page.tex": ZIP_FOLLOW_TEMPLATE_ALT,
            "contents.tex": ZIP_CONTENTS_TEMPLATE_ALT,
        },
    },
}


def slugify(value: str):
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "template"


def ensure_template_dirs():
    UPLOADED_TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)


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


def build_uploaded_template_summary(path: Path):
    label = path.stem.replace("_", " ").replace("-", " ").strip() or "Custom Template"
    return TemplateSummary(
        id=path.stem,
        name=label.title(),
        description="Uploaded ZIP template available for direct download.",
        source="uploaded",
        is_customizable=False,
        preview_url=None,
        download_filename=path.name,
    )


def list_template_summaries():
    ensure_template_dirs()
    templates = [build_builtin_template_summary(template_id) for template_id in BUILTIN_TEMPLATES]
    for path in sorted(UPLOADED_TEMPLATE_DIR.glob("*.zip")):
        templates.append(build_uploaded_template_summary(path))
    return templates


def get_uploaded_template_path(template_id: str):
    candidate = UPLOADED_TEMPLATE_DIR / f"{template_id}.zip"
    if candidate.exists():
        return candidate
    raise HTTPException(404, "Template not found")


def resolve_template_summary(template_id: str):
    if template_id in BUILTIN_TEMPLATES:
        return build_builtin_template_summary(template_id)
    return build_uploaded_template_summary(get_uploaded_template_path(template_id))


def render_preview_pdf(title: str, subtitle: str, accent: Tuple[float, float, float], details: List[str], logo_stream: Optional[bytes] = None):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    page.draw_rect(fitz.Rect(0, 0, 595, 842), fill=(0.97, 0.98, 1.0), color=(0.97, 0.98, 1.0))
    page.draw_rect(fitz.Rect(36, 36, 559, 806), color=(0.55, 0.62, 0.78), width=1.5, fill=(1, 1, 1))
    page.draw_rect(fitz.Rect(36, 36, 559, 166), fill=accent, color=accent)
    page.draw_rect(fitz.Rect(64, 360, 531, 724), color=(0.88, 0.9, 0.96), fill=(0.98, 0.985, 1), width=1.2)

    page.insert_text((64, 84), "Lab Record Studio", fontsize=18, fontname="helv", color=(1, 1, 1))
    page.insert_text((64, 118), title, fontsize=28, fontname="helv", color=(1, 1, 1))
    page.insert_text((64, 146), subtitle, fontsize=12, fontname="helv", color=(0.93, 0.95, 1))

    circle_center = fitz.Point(458, 248)
    circle_radius = 68
    page.draw_circle(circle_center, circle_radius, color=accent, fill=(0.96, 0.98, 1), width=2.5)
    if logo_stream:
        image_rect = fitz.Rect(circle_center.x - 44, circle_center.y - 44, circle_center.x + 44, circle_center.y + 44)
        try:
            page.insert_image(image_rect, stream=logo_stream, keep_proportion=True)
        except RuntimeError:
            pass
    else:
        page.insert_text((circle_center.x - 22, circle_center.y + 6), "LOGO", fontsize=16, fontname="helv", color=accent)

    page.insert_text((64, 226), "Preview", fontsize=13, fontname="helv", color=accent)
    page.insert_textbox(
        fitz.Rect(64, 246, 360, 332),
        "Select this template first, then download the ZIP package or continue to experiment generation. The LaTeX snippet generator stays unchanged.",
        fontsize=14,
        fontname="helv",
        color=(0.2, 0.25, 0.35),
        lineheight=1.35,
    )

    page.insert_text((88, 396), "Template Contents", fontsize=18, fontname="helv", color=(0.16, 0.21, 0.3))

    y = 430
    for detail in details[:12]:
        page.draw_circle(fitz.Point(98, y - 4), 3.2, color=accent, fill=accent)
        page.insert_textbox(
            fitz.Rect(112, y - 14, 500, y + 12),
            detail,
            fontsize=12.5,
            fontname="helv",
            color=(0.22, 0.26, 0.35),
        )
        y += 30

    out = doc.tobytes()
    doc.close()
    return out


def build_builtin_preview_pdf(template_id: str):
    logo_path = BASE_DIR / "figures" / "cet_logo.jpeg"
    logo_stream = logo_path.read_bytes() if logo_path.exists() else None
    if template_id == "template-1":
        return render_preview_pdf(
            title="Template 1 - Classic Record",
            subtitle="Admin-curated preview for the original bundled record format.",
            accent=(0.08, 0.25, 0.55),
            details=[
                "Traditional lab record cover page with institution heading.",
                "Default follow page and experiment index layout.",
                "Uses the current LaTeX structure already present in the backend.",
                "Best when you want continuity with the existing project format.",
            ],
            logo_stream=logo_stream,
        )

    return render_preview_pdf(
        title="Template 2 - Modern Record",
        subtitle="Admin-curated preview for the alternate built-in template.",
        accent=(0.06, 0.45, 0.56),
        details=[
            "Cleaner cover layout with stronger spacing and boxed student details.",
            "Circular logo treatment integrated into the title and certificate pages.",
            "Updated index styling for a more polished record-book look.",
            "Uses a separate built-in LaTeX file set when selected.",
        ],
        logo_stream=logo_stream,
    )


def get_builtin_template_files(template_id: str):
    if template_id not in BUILTIN_TEMPLATES:
        raise HTTPException(404, "Built-in template not found")
    return BUILTIN_TEMPLATES[template_id]["files"]
def build_template_zip(payload: TemplateRequest, template_files: Optional[dict] = None):
    values = payload.model_dump()
    files = template_files or BUILTIN_TEMPLATES["template-1"]["files"]

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Render and add your .tex files
        for file_name, template in files.items():
            zf.writestr(file_name, render_zip_template(template, values))
        
        # 2. Add the logo to the 'figures' folder
        # Ensure the path to your local file is correct!
        logo_path = BASE_DIR / "figures" / "cet_logo.jpeg"
        
        if logo_path.exists():
            # The second argument 'arcname' sets the path inside the ZIP
            zf.write(logo_path, arcname="figures/cet_logo.jpeg")
        else:
            print(f"Lowkey error: Logo not found at {logo_path} 💀")

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


def build_outputs(programs,s):

    out = []

    for p in programs:
        out.append(
f"""\\begin{{tcolorbox}}[myoutputbox,title=Terminal Output]
\\begin{{verbatim}}
s23a48@administrator-rusa:˜/s6$ gcc {s}.c
s23a48@administrator-rusa:˜/s6$ ./a.out
{p.output}
\\end{{verbatim}}
\\end{{tcolorbox}}"""
        )

    return "\n".join(out)


def build_latex(exp: ExperimentData):

    latex = LATEX_TEMPLATE
    latex=latex.replace("<nombor>", exp.experiment_number[0])
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
        build_outputs(exp.programs,str(exp.experiment_number))
    )

    return latex


# =========================================================
# PIPELINE
# =========================================================
def process_programs(programs):

    algorithms = []
    aim = ""

    for p in programs:

        prog_aim, algos, output = generate_academic(p)

        p.output = output

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


@app.post("/api/templates/upload", response_model=TemplateSummary)
async def upload_template(file: UploadFile = File(...)):
    ensure_template_dirs()

    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(400, "Please upload a ZIP template file.")

    template_name = slugify(Path(file.filename).stem)
    target = UPLOADED_TEMPLATE_DIR / f"{template_name}.zip"
    suffix = 1
    while target.exists():
        target = UPLOADED_TEMPLATE_DIR / f"{template_name}-{suffix}.zip"
        suffix += 1

    target.write_bytes(await file.read())
    return build_uploaded_template_summary(target)


@app.get("/api/templates/{template_id}/preview")
async def get_template_preview(template_id: str):
    if template_id not in BUILTIN_TEMPLATES:
        raise HTTPException(404, "Preview is only available for built-in templates.")

    preview_bytes = build_builtin_preview_pdf(template_id)

    headers = {"Content-Disposition": f'inline; filename="{template_id}-preview.pdf"'}
    return StreamingResponse(io.BytesIO(preview_bytes), media_type="application/pdf", headers=headers)


@app.post("/api/templates/{template_id}/download")
async def download_selected_template(template_id: str, payload: TemplateRequest):
    if template_id in BUILTIN_TEMPLATES:
        zip_buffer = build_template_zip(payload, get_builtin_template_files(template_id))
        filename = build_builtin_template_summary(template_id).download_filename
    else:
        template_path = get_uploaded_template_path(template_id)
        zip_buffer = io.BytesIO(template_path.read_bytes())
        filename = template_path.name

    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(zip_buffer, media_type="application/zip", headers=headers)


@app.post("/api/download-template")
async def download_template(payload: TemplateRequest):
    zip_buffer = build_template_zip(payload)
    headers = {"Content-Disposition": 'attachment; filename="latex_template.zip"'}
    return StreamingResponse(zip_buffer, media_type="application/zip", headers=headers)
