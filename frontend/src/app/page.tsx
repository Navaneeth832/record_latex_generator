"use client";

import { ChangeEvent, useEffect, useState } from "react";
import Link from "next/link";
import { ContentsAnalysisResponse, TemplateForm, TemplateSummary } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

const initialForm: TemplateForm = {
  name: "YOUR NAME",
  lab_name: "COMPUTER NETWORKS LAB",
  course_code: "CSL 332",
  course_name: "COMPUTER NETWORKS LAB",
  department: "COMPUTER SCIENCE AND ENGINEERING",
  institution: "COLLEGE OF ENGINEERING TRIVANDRUM",
  semester: "S6",
  academic_year: "2025-2026",
  submitted_to: "FACULTY IN CHARGE",
  submitted_by: "YOUR NAME",
  roll_number: "S23XXX",
  section: "A",
  experiment_title: "",
  date: new Date().toLocaleDateString("en-GB"),
  contents_cycles: [],
};

const logoMarks = {
  builtin: "LR",
  uploaded: "ZIP",
} as const;

export default function Home() {
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [form, setForm] = useState<TemplateForm>(initialForm);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [analyzingContents, setAnalyzingContents] = useState(false);
  const [contentsText, setContentsText] = useState("");
  const [contentsFile, setContentsFile] = useState<File | null>(null);
  const [contentsPreview, setContentsPreview] = useState("");
  const [generatedFiles, setGeneratedFiles] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    const loadTemplates = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/templates`);
        if (!res.ok) {
          throw new Error(await res.text());
        }

        const json: TemplateSummary[] = await res.json();
        setTemplates(json);
        setSelectedTemplateId((current) => current || json[0]?.id || "");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load templates");
      }
    };

    void loadTemplates();
  }, []);

  const selectedTemplate = templates.find((template) => template.id === selectedTemplateId) ?? null;

  useEffect(() => {
    if (selectedTemplateId) {
      localStorage.setItem("selectedTemplateId", selectedTemplateId);
    }
  }, [selectedTemplateId]);

  const setField = (key: keyof TemplateForm, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const resetMessages = () => {
    setError("");
    setSuccess("");
  };

  const analyzeContents = async () => {
    if (!selectedTemplate || selectedTemplate.source !== "builtin") {
      setError("Select a built-in template before analyzing the table of contents.");
      return;
    }

    setAnalyzingContents(true);
    resetMessages();

    try {
      let res: Response;

      if (contentsFile) {
        const formData = new FormData();
        formData.append("file", contentsFile);
        res = await fetch(`${API_BASE}/api/templates/${selectedTemplate.id}/analyze-contents-upload`, {
          method: "POST",
          body: formData,
        });
      } else {
        if (!contentsText.trim()) {
          throw new Error("Paste the table of contents text or upload a PDF before analyzing.");
        }

        res = await fetch(`${API_BASE}/api/templates/${selectedTemplate.id}/analyze-contents-text`, {
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

  const downloadSelectedTemplate = async () => {
    if (!selectedTemplate) {
      setError("Select a template before downloading.");
      return;
    }

    setLoading(true);
    resetMessages();

    try {
      const res = await fetch(`${API_BASE}/api/templates/${selectedTemplate.id}/download`, {
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
      anchor.download = selectedTemplate.download_filename;
      anchor.click();
      URL.revokeObjectURL(url);
      setSuccess(`${selectedTemplate.name} is ready to download.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to download selected template");
    } finally {
      setLoading(false);
    }
  };

  const uploadTemplate = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    setUploading(true);
    resetMessages();

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${API_BASE}/api/templates/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      const created: TemplateSummary = await res.json();
      setTemplates((prev) => [...prev, created]);
      setSelectedTemplateId(created.id);
      setSuccess(`${created.name} was added to the template shelf.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Template upload failed");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_#eff6ff_0%,_#f8fafc_45%,_#e2e8f0_100%)] px-4 py-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="overflow-hidden rounded-[2rem] border border-slate-200 bg-white/90 shadow-[0_24px_80px_rgba(15,23,42,0.08)] backdrop-blur">
          <div className="grid gap-6 px-6 py-8 md:grid-cols-[1.4fr_0.8fr] md:px-8">
            <div className="space-y-5">
              <div className="inline-flex rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-sky-700">
                Template-first workspace
              </div>
              <div className="space-y-3">
                <h1 className="text-4xl font-bold tracking-tight text-slate-950 md:text-5xl">Lab Record Studio</h1>
                <p className="max-w-2xl text-sm leading-7 text-slate-600 md:text-base">
                  Pick a record template first, review its PDF preview, then download the ZIP package or move straight to the experiment LaTeX generator.
                </p>
              </div>

              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={downloadSelectedTemplate}
                  disabled={loading || !selectedTemplate}
                  className="rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loading ? "Preparing ZIP..." : "Download Selected Template"}
                </button>
                <Link
                  href="/generate"
                  className="rounded-full border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-white"
                >
                  Generate Experiment LaTeX
                </Link>
              </div>

             
            </div>

            <div className="rounded-[1.75rem] bg-[linear-gradient(160deg,_#082f49_0%,_#0f766e_100%)] p-6 text-white shadow-inner">
              <div className="flex h-full flex-col justify-between gap-6">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm uppercase tracking-[0.24em] text-cyan-100">Selected Template</p>
                    <h2 className="mt-2 text-2xl font-semibold">{selectedTemplate?.name ?? "Loading..."}</h2>
                    <p className="mt-3 max-w-sm text-sm leading-6 text-cyan-50/85">
                      {selectedTemplate?.description ?? "Fetching available templates from the backend library."}
                    </p>
                  </div>
                  <div className="flex h-28 w-28 items-center justify-center rounded-full border-4 border-white/35 bg-white/10 text-lg font-bold tracking-[0.28em] text-white shadow-[inset_0_0_40px_rgba(255,255,255,0.15)]">
                    {selectedTemplate ? logoMarks[selectedTemplate.source] : "LOGO"}
                  </div>
                </div>

                <div className="grid gap-3 rounded-[1.5rem] border border-white/15 bg-white/10 p-4 text-sm text-cyan-50/90 md:grid-cols-2">
                  <div>
                    <p className="text-xs uppercase tracking-[0.22em] text-cyan-100/80">Source</p>
                    <p className="mt-2 font-medium capitalize">{selectedTemplate?.source ?? "..."}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.22em] text-cyan-100/80">Customization</p>
                    <p className="mt-2 font-medium">{selectedTemplate?.is_customizable ? "Uses this template's built-in LaTeX files" : "Downloads as uploaded ZIP"}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </header>

        {success && <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div>}
        {error && <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

        <section className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold text-slate-900">Choose a Template</h2>
              <p className="mt-1 text-sm text-slate-600">The current backend template is the default card, and you can add more ZIP templates with the plus card.</p>
            </div>

            <label className="inline-flex cursor-pointer items-center gap-3 rounded-full border border-dashed border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:border-slate-400">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-950 text-xl leading-none text-white">+</span>
              {uploading ? "Uploading..." : "Add Template ZIP"}
              <input type="file" accept=".zip" onChange={uploadTemplate} className="hidden" />
            </label>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            {templates.map((template) => {
              const isSelected = template.id === selectedTemplateId;
              return (
                <button
                  key={template.id}
                  type="button"
                  onClick={() => setSelectedTemplateId(template.id)}
                  className={`overflow-hidden rounded-[1.75rem] border bg-white text-left shadow-sm transition ${
                    isSelected ? "border-sky-400 shadow-[0_22px_60px_rgba(14,116,144,0.16)]" : "border-slate-200 hover:border-slate-300 hover:shadow-md"
                  }`}
                >
                  <div className="border-b border-slate-200 bg-slate-50 px-5 py-4">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <h3 className="text-lg font-semibold text-slate-900">{template.name}</h3>
                        <p className="mt-1 text-sm text-slate-600">{template.description}</p>
                      </div>
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] ${
                          isSelected ? "bg-sky-100 text-sky-700" : "bg-slate-200 text-slate-600"
                        }`}
                      >
                        {isSelected ? "Selected" : template.source}
                      </span>
                    </div>
                  </div>

                  <div className="bg-slate-100 p-4">
                    {template.preview_url ? (
                      <div className="overflow-hidden rounded-[1.25rem] border border-slate-200 bg-white shadow-inner">
                        <iframe
                          title={`${template.name} preview`}
                          src={`${API_BASE}${template.preview_url}`}
                          className="h-[360px] w-full"
                        />
                      </div>
                    ) : (
                      <div className="flex h-[360px] items-center justify-center rounded-[1.25rem] border border-dashed border-slate-300 bg-white px-8 text-center text-sm leading-7 text-slate-500">
                        Manual upload templates do not have an automatic preview. Select the ZIP and download it directly when needed.
                      </div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-2xl font-semibold text-slate-900">Template Details</h2>
                <p className="mt-1 text-sm text-slate-600">
                  {selectedTemplate?.is_customizable
                    ? "These values are injected into the selected built-in template before download."
                    : "Uploaded templates are downloaded exactly as they were added. The form is only used by the built-in templates."}
                </p>
              </div>
              <div className="flex h-20 w-20 items-center justify-center rounded-full border-2 border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">
                Logo
              </div>
            </div>

            <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-2">
              <input value={form.name} onChange={(e) => setField("name", e.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" placeholder="Name" />
              <input value={form.lab_name} onChange={(e) => setField("lab_name", e.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" placeholder="Lab Name" />
              <input value={form.course_code} onChange={(e) => setField("course_code", e.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" placeholder="Course Code" />
              <input value={form.course_name} onChange={(e) => setField("course_name", e.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" placeholder="Course Name" />
              <input value={form.department} onChange={(e) => setField("department", e.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" placeholder="Department" />
              <input value={form.institution} onChange={(e) => setField("institution", e.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" placeholder="Institution" />
              <input value={form.semester} onChange={(e) => setField("semester", e.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" placeholder="Semester" />
              <input value={form.academic_year} onChange={(e) => setField("academic_year", e.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" placeholder="Academic Year" />
              <input value={form.submitted_to} onChange={(e) => setField("submitted_to", e.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" placeholder="Submitted To" />
              <input value={form.submitted_by} onChange={(e) => setField("submitted_by", e.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" placeholder="Submitted By" />
              <input value={form.roll_number} onChange={(e) => setField("roll_number", e.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" placeholder="Roll Number" />
              <input value={form.section} onChange={(e) => setField("section", e.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm" placeholder="Section" />
              <input
                value={form.experiment_title}
                onChange={(e) => setField("experiment_title", e.target.value)}
                className="rounded-xl border border-slate-300 px-4 py-3 text-sm md:col-span-2"
                placeholder="Experiment Title"
              />
              <input value={form.date} onChange={(e) => setField("date", e.target.value)} className="rounded-xl border border-slate-300 px-4 py-3 text-sm md:col-span-2" placeholder="Date" />
            </div>

            {selectedTemplate?.source === "builtin" && (
              <div className="mt-8 space-y-4 rounded-[1.5rem] border border-slate-200 bg-slate-50 p-5">
                <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-900">Table of Contents Analyzer</h3>
                    <p className="mt-1 text-sm text-slate-600">
                      Paste the contents table or upload a PDF. The app will generate the matching `contents.tex`, empty experiment files, and template-specific `main.tex` includes.
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
            )}
          </div>

          <aside className="rounded-[1.75rem] border border-slate-200 bg-[linear-gradient(180deg,_#ffffff_0%,_#f8fafc_100%)] p-6 shadow-sm">
            <h2 className="text-2xl font-semibold text-slate-900">Next Actions</h2>
            <p className="mt-2 text-sm leading-7 text-slate-600">
              Template selection happens here first. The experiment LaTeX snippet workflow remains the same and is still available on the generator page.
            </p>

            <div className="mt-6 space-y-3">
              <button
                type="button"
                onClick={downloadSelectedTemplate}
                disabled={loading || !selectedTemplate}
                className="w-full rounded-2xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Preparing Download..." : "Download Selected ZIP"}
              </button>
              <Link
                href="/generate"
                className="block w-full rounded-2xl border border-slate-300 px-4 py-3 text-center text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-white"
              >
                Open Experiment Generator
              </Link>
            </div>

            <div className="mt-6 rounded-[1.5rem] border border-slate-200 bg-white p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Selected package</p>
              <p className="mt-3 text-lg font-semibold text-slate-900">{selectedTemplate?.download_filename ?? "Loading..."}</p>
              <p className="mt-2 text-sm text-slate-600">
                {selectedTemplate?.is_customizable
                  ? "The selected built-in template is rendered with the form details before the ZIP is generated."
                  : "This template is downloaded exactly as uploaded, including its bundled files."}
              </p>
            </div>
          </aside>
        </section>
      </div>
    </main>
  );
}
