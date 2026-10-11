"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ContentsAnalysisResponse, TemplateForm, TemplateSummary } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

const initialForm: TemplateForm = {
  name: "",
  lab_name: "",
  course_code: "",
  course_name: "",
  department: "COMPUTER SCIENCE AND ENGINEERING",
  institution: "COLLEGE OF ENGINEERING TRIVANDRUM",
  semester: "S7",
  academic_year: "",
  submitted_to: "",
  submitted_by: "",
  roll_number: "TVE23CS099",
  section: "",
  experiment_title: "",
  date: new Date().toLocaleDateString("en-GB"),
  contents_cycles: [],
};

export default function Home() {
  const [template, setTemplate] = useState<TemplateSummary | null>(null);
  const [form, setForm] = useState<TemplateForm>(initialForm);
  const [loading, setLoading] = useState(false);
  const [analyzingContents, setAnalyzingContents] = useState(false);
  const [contentsText, setContentsText] = useState("");
  const [contentsFile, setContentsFile] = useState<File | null>(null);
  const [contentsPreview, setContentsPreview] = useState("");
  const [generatedFiles, setGeneratedFiles] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    const loadTemplate = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/templates`);
        if (!res.ok) {
          throw new Error(await res.text());
        }

        const json: TemplateSummary[] = await res.json();
        if (json.length > 0) {
          setTemplate(json[0]);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load template");
      }
    };

    void loadTemplate();
    if (typeof window !== "undefined") {
      localStorage.setItem("selectedTemplateId", "template-1");
      const savedRoll = localStorage.getItem("roll_number");
      const savedSem = localStorage.getItem("semester");
      if (savedRoll || savedSem) {
        setForm((prev) => ({
          ...prev,
          roll_number: savedRoll || prev.roll_number,
          semester: savedSem || prev.semester,
        }));
      }
    }
  }, []);

  const setField = (key: keyof TemplateForm, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    if (typeof window !== "undefined") {
      if (key === "roll_number") localStorage.setItem("roll_number", value);
      if (key === "semester") localStorage.setItem("semester", value);
    }
  };

  const resetMessages = () => {
    setError("");
    setSuccess("");
  };

  const analyzeContents = async () => {
    setAnalyzingContents(true);
    resetMessages();

    try {
      let res: Response;

      if (contentsFile) {
        const formData = new FormData();
        formData.append("file", contentsFile);
        res = await fetch(`${API_BASE}/api/templates/template-1/analyze-contents-upload`, {
          method: "POST",
          body: formData,
        });
      } else {
        if (!contentsText.trim()) {
          throw new Error("Paste the table of contents text or upload a PDF before analyzing.");
        }

        res = await fetch(`${API_BASE}/api/templates/template-1/analyze-contents-text`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: contentsText.trim() }),
        });
      }

      if (!res.ok) {
        throw new Error(await res.text());
      }

      const analysis: ContentsAnalysisResponse = await res.json();
      setForm((prev) => ({ ...prev, contents_cycles: analysis.cycles }));
      setContentsPreview(analysis.contents_tex);
      setGeneratedFiles(analysis.generated_files);
      setSuccess(`Contents analyzed successfully. ${analysis.generated_files.length} files will be generated in the ZIP.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to analyze the table of contents");
    } finally {
      setAnalyzingContents(false);
    }
  };

  const downloadTemplate = async () => {
    setLoading(true);
    resetMessages();

    try {
      const res = await fetch(`${API_BASE}/api/templates/template-1/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = template?.download_filename ?? "Navaneeth-modern-record.zip";
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);
      setSuccess("Lab Record ZIP package downloaded successfully.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to download template");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_#eff6ff_0%,_#f8fafc_45%,_#e2e8f0_100%)] px-4 py-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="overflow-hidden rounded-[2rem] border border-slate-200 bg-white/90 shadow-[0_24px_80px_rgba(15,23,42,0.08)] backdrop-blur">
          <div className="grid gap-6 px-6 py-6 lg:grid-cols-[1.1fr_1fr] md:px-8 items-center">
            <div className="flex flex-col justify-between space-y-6">
              <div className="space-y-5">
                <div className="inline-flex rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-sky-700">
                  Navaneeth Lab Record
                </div>
                <div className="space-y-3">
                  <h1 className="text-4xl font-bold tracking-tight text-slate-950 md:text-5xl">Lab Record Studio</h1>
                  <p className="max-w-xl text-sm leading-7 text-slate-600 md:text-base">
                    Preview the record PDF, customize the lab cover and course information, analyze the table of contents, and download the full LaTeX ZIP bundle or generate experiment snippets.
                  </p>
                </div>

                <div className="flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={downloadTemplate}
                    disabled={loading}
                    className="rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {loading ? "Preparing ZIP..." : "Download Template ZIP"}
                  </button>
                  <Link
                    href="/generate"
                    className="rounded-full border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-white"
                  >
                    Generate Experiment LaTeX
                  </Link>
                </div>
              </div>

              <div className="flex items-center justify-between border-t border-slate-100 pt-4 text-xs text-slate-500">
                <span className="font-medium text-slate-700">{template?.name ?? "Navaneeth - Lab Record"}</span>
                <a
                  href={`${API_BASE}/api/templates/template-1/preview`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 font-semibold text-sky-700 hover:text-sky-800 transition"
                >
                  <span>Open PDF in new tab</span>
                  <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              </div>
            </div>

            <div className="overflow-hidden rounded-[1.75rem] border border-slate-200 bg-slate-100 shadow-inner">
              <iframe
                title="Lab Record Preview"
                src={`${API_BASE}/api/templates/template-1/preview`}
                className="h-[460px] w-full border-0"
              />
            </div>
          </div>
        </header>

        {success && <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div>}
        {error && <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

        <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-2xl font-semibold text-slate-900">Template Details</h2>
                <p className="mt-1 text-sm text-slate-600">
                  These values are injected into the record template before download.
                </p>
              </div>
              <div className="flex h-20 w-20 items-center justify-center rounded-full border-2 border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">
                Logo
              </div>
            </div>

            <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-2">
              <input value={form.name} onChange={(e) => setField("name", e.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" placeholder="Name" />
              <input value={form.course_code} onChange={(e) => setField("course_code", e.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" placeholder="Course Code" />
              <input value={form.course_name} onChange={(e) => setField("course_name", e.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" placeholder="Course Name" />
              <input value={form.department} onChange={(e) => setField("department", e.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" placeholder="Department" />
              <input value={form.institution} onChange={(e) => setField("institution", e.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" placeholder="Institution" />
              <input value={form.semester} onChange={(e) => setField("semester", e.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" placeholder="Semester (e.g. S7)" />
              <input value={form.academic_year} onChange={(e) => setField("academic_year", e.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" placeholder="Academic Year" />
              <input value={form.roll_number} onChange={(e) => setField("roll_number", e.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" placeholder="Lab Roll Number (e.g. s23a48)" />
              <input value={form.section} onChange={(e) => setField("section", e.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" placeholder="Section" />
            </div>

            <div className="mt-8 space-y-4 rounded-[1.5rem] border border-slate-200 bg-slate-50 p-5">
              <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-slate-900">Table of Contents Analyzer</h3>
                  <p className="mt-1 text-sm text-slate-600">
                    Paste the contents table or upload a PDF. The app will generate the matching `contents.tex`, empty experiment files, and `main.tex` includes.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={analyzeContents}
                  disabled={analyzingContents}
                  className="rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
                >
                  {analyzingContents ? "Analyzing..." : "Analyze Contents"}
                </button>
              </div>

              <textarea
                value={contentsText}
                onChange={(e) => setContentsText(e.target.value)}
                className="min-h-[180px] w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm"
                placeholder="Paste the table of contents here if you are not uploading a PDF."
              />

              <input
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.webp"
                onChange={(e) => setContentsFile(e.target.files?.[0] ?? null)}
                className="block w-full rounded-xl border border-slate-300 bg-white p-3 text-sm"
              />

              {form.contents_cycles.length > 0 && (
                <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
                  <div className="rounded-xl border border-slate-200 bg-white p-4">
                    <p className="text-sm font-semibold text-slate-900">Detected Structure</p>
                    <div className="mt-3 space-y-3 text-sm text-slate-700">
                      {form.contents_cycles.map((cycle) => (
                        <div key={cycle.cycle_number}>
                          <p className="font-semibold">{`Cycle ${cycle.cycle_number}: ${cycle.title}`}</p>
                          <p className="mt-1 text-slate-500">{`${cycle.entries.length} experiment(s)`}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-200 bg-white p-4">
                    <p className="text-sm font-semibold text-slate-900">Generated Files</p>
                    <p className="mt-1 text-sm text-slate-500">{generatedFiles.join(", ")}</p>
                    <textarea
                      readOnly
                      value={contentsPreview}
                      className="mt-4 min-h-[220px] w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 font-mono text-xs text-slate-700"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          <aside className="rounded-[1.75rem] border border-slate-200 bg-[linear-gradient(180deg,_#ffffff_0%,_#f8fafc_100%)] p-6 shadow-sm">
            <h2 className="text-2xl font-semibold text-slate-900">Next Actions</h2>
            <p className="mt-2 text-sm leading-7 text-slate-600">
              Download the complete ZIP project for Overleaf or your local TeX distribution, or use the experiment generator to convert program code into report snippets.
            </p>

            <div className="mt-6 space-y-3">
              <button
                type="button"
                onClick={downloadTemplate}
                disabled={loading}
                className="w-full rounded-2xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Preparing Download..." : "Download Template ZIP"}
              </button>
              <Link
                href="/generate"
                className="block w-full rounded-2xl border border-slate-300 px-4 py-3 text-center text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-white"
              >
                Open Experiment Generator
              </Link>
            </div>

            <div className="mt-6 rounded-[1.5rem] border border-slate-200 bg-white p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Package Details</p>
              <p className="mt-3 text-lg font-semibold text-slate-900">{template?.download_filename ?? "record-template.zip"}</p>
              <p className="mt-2 text-sm text-slate-600">
                Bundled with `main.tex`, `cover_page.tex`, `follow_page.tex`, `contents.tex`, and college insignia logo.
              </p>
            </div>
          </aside>
        </section>
      </div>
    </main>
  );
}
