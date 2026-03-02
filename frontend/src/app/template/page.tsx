"use client";

import { useState } from "react";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type TemplateForm = {
  name: string;
  lab_name: string;
  course_code: string;
  course_name: string;
  department: string;
  institution: string;
  semester: string;
  academic_year: string;
  submitted_to: string;
  submitted_by: string;
  roll_number: string;
  section: string;
  experiment_title: string;
  date: string;
};

const initialForm: TemplateForm = {
  name: "",
  lab_name: "",
  course_code: "",
  course_name: "",
  department: "",
  institution: "",
  semester: "",
  academic_year: "",
  submitted_to: "",
  submitted_by: "",
  roll_number: "",
  section: "",
  experiment_title: "",
  date: new Date().toLocaleDateString("en-GB"),
};

export default function TemplatePage() {
  const [form, setForm] = useState<TemplateForm>(initialForm);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const setField = (key: keyof TemplateForm, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const downloadZip = async () => {
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/api/download-template`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "latex_template.zip";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to download template ZIP");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-100 px-4 py-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <header className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <div className="flex items-center justify-between gap-3">
            <h1 className="text-2xl font-bold text-slate-900 md:text-3xl">Download LaTeX Template</h1>
            <Link href="/" className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700">
              Back Home
            </Link>
          </div>
          <p className="mt-2 text-sm text-slate-600">
            Fill in details once and download a ZIP with `main.tex`, `cover_page.tex`, `follow_page.tex`, and `contents.tex`.
          </p>
        </header>

        {error && <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

        <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <input value={form.name} onChange={(e) => setField("name", e.target.value)} className="rounded-lg border border-slate-300 p-2" placeholder="Name" />
            <input value={form.lab_name} onChange={(e) => setField("lab_name", e.target.value)} className="rounded-lg border border-slate-300 p-2" placeholder="Lab Name" />
            <input value={form.course_code} onChange={(e) => setField("course_code", e.target.value)} className="rounded-lg border border-slate-300 p-2" placeholder="Course Code" />
            <input value={form.course_name} onChange={(e) => setField("course_name", e.target.value)} className="rounded-lg border border-slate-300 p-2" placeholder="Course Name" />
            <input value={form.department} onChange={(e) => setField("department", e.target.value)} className="rounded-lg border border-slate-300 p-2" placeholder="Department" />
            <input value={form.institution} onChange={(e) => setField("institution", e.target.value)} className="rounded-lg border border-slate-300 p-2" placeholder="Institution" />
            <input value={form.semester} onChange={(e) => setField("semester", e.target.value)} className="rounded-lg border border-slate-300 p-2" placeholder="Semester" />
            <input value={form.academic_year} onChange={(e) => setField("academic_year", e.target.value)} className="rounded-lg border border-slate-300 p-2" placeholder="Academic Year" />
            <input value={form.submitted_to} onChange={(e) => setField("submitted_to", e.target.value)} className="rounded-lg border border-slate-300 p-2" placeholder="Submitted To" />
            <input value={form.submitted_by} onChange={(e) => setField("submitted_by", e.target.value)} className="rounded-lg border border-slate-300 p-2" placeholder="Submitted By" />
            <input value={form.roll_number} onChange={(e) => setField("roll_number", e.target.value)} className="rounded-lg border border-slate-300 p-2" placeholder="Roll Number" />
            <input value={form.section} onChange={(e) => setField("section", e.target.value)} className="rounded-lg border border-slate-300 p-2" placeholder="Section" />
            <input
              value={form.experiment_title}
              onChange={(e) => setField("experiment_title", e.target.value)}
              className="rounded-lg border border-slate-300 p-2 md:col-span-2"
              placeholder="Experiment Title"
            />
            <input value={form.date} onChange={(e) => setField("date", e.target.value)} className="rounded-lg border border-slate-300 p-2 md:col-span-2" placeholder="Date" />
          </div>

          <div className="mt-5">
            <button
              type="button"
              onClick={downloadZip}
              disabled={loading}
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
            >
              {loading ? "Preparing ZIP..." : "Download ZIP"}
            </button>
          </div>
        </section>
      </div>
    </main>
  );
}
