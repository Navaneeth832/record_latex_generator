"use client";

import { useMemo, useState } from "react";
import MonacoField from "@/components/MonacoField";
import { ExperimentData } from "@/lib/types";
import { parseProgramsFromText } from "@/lib/parsePrograms";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type InputMode = "upload" | "paste";

const emptyExperiment: ExperimentData = {
  experiment_number: "1",
  date: new Date().toLocaleDateString("en-GB"),
  experiment_heading: "CPU SCHEDULING ALGORITHMS",
  aim: "",
  algorithms: [],
  programs: [],
  result:
    "CPU scheduling algorithms are implemented and outputs verified successfully.",
};

export default function Home() {
  const [mode, setMode] = useState<InputMode>("upload");
  const [data, setData] = useState<ExperimentData>(emptyExperiment);
  const [latex, setLatex] = useState("");
  const [pastedText, setPastedText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const parsedPrograms = useMemo(() => parseProgramsFromText(pastedText), [pastedText]);

  const uploadFile = async (file: File) => {
    setLoading(true);
    setError("");
    setLatex("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/api/upload-process`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      setData(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  const processPastedText = async () => {
    setLoading(true);
    setError("");
    setLatex("");

    try {
      if (parsedPrograms.length === 0) {
        throw new Error("Please add at least one heading (### Title) with code.");
      }

      const res = await fetch(`${API_BASE}/api/process-text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: pastedText }),
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      setData(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Text processing failed");
    } finally {
      setLoading(false);
    }
  };

  const generateLatex = async () => {
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/api/generate-latex`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      const json = await res.json();
      setLatex(json.latex ?? "");
    } catch (e) {
      setError(e instanceof Error ? e.message : "LaTeX generation failed");
    } finally {
      setLoading(false);
    }
  };

  const copyLatex = async () => {
    await navigator.clipboard.writeText(latex);
  };

  const downloadLatex = () => {
    const blob = new Blob([latex], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "experiment.tex";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <main className="min-h-screen bg-slate-100 px-4 py-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <h1 className="text-2xl font-bold text-slate-900 md:text-3xl">AI LaTeX Lab Generator</h1>
          <p className="mt-2 text-sm text-slate-600 md:text-base">
            Generate academic lab records from uploaded files or pasted code blocks.
          </p>

          <div className="mt-5 inline-flex rounded-xl bg-slate-100 p-1">
            <button
              type="button"
              onClick={() => setMode("upload")}
              className={`rounded-lg px-4 py-2 text-sm font-medium ${
                mode === "upload" ? "bg-white text-slate-900 shadow" : "text-slate-600"
              }`}
            >
              Upload File
            </button>
            <button
              type="button"
              onClick={() => setMode("paste")}
              className={`rounded-lg px-4 py-2 text-sm font-medium ${
                mode === "paste" ? "bg-white text-slate-900 shadow" : "text-slate-600"
              }`}
            >
              Paste Code
            </button>
          </div>
        </header>

        <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 space-y-4">
          {mode === "upload" ? (
            <>
              <label className="block text-sm font-semibold text-slate-700">Upload source file</label>
              <input
                type="file"
                accept=".pdf,.txt,.zip,.bin"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) uploadFile(file);
                }}
                className="block w-full rounded-lg border border-slate-300 bg-white p-3 text-sm"
              />
            </>
          ) : (
            <>
              <MonacoField
                label="Paste code with headings (### Program Title)"
                language="markdown"
                value={pastedText}
                onChange={setPastedText}
                minHeight="320px"
              />
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <p className="text-sm text-slate-600">
                  Parsed programs: <span className="font-semibold">{parsedPrograms.length}</span>
                </p>
                <button
                  type="button"
                  onClick={processPastedText}
                  disabled={loading}
                  className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
                >
                  Process Pasted Code
                </button>
              </div>
            </>
          )}

          {loading && (
            <div className="rounded-lg bg-blue-50 p-3 text-sm text-blue-700">
              Processing... Please wait.
            </div>
          )}

          {error && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        </section>

        <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 space-y-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <h2 className="text-lg font-semibold text-slate-900">Generated Experiment Data</h2>
            <button
              type="button"
              onClick={generateLatex}
              disabled={loading || data.programs.length === 0}
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
            >
              Generate LaTeX
            </button>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <input
              value={data.experiment_number}
              onChange={(e) => setData({ ...data, experiment_number: e.target.value })}
              className="rounded-lg border border-slate-300 p-2"
              placeholder="Experiment Number"
            />
            <input
              value={data.date}
              onChange={(e) => setData({ ...data, date: e.target.value })}
              className="rounded-lg border border-slate-300 p-2"
              placeholder="Date"
            />
          </div>
        </section>

        {latex && (
          <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 space-y-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <h2 className="text-xl font-semibold">Generated LaTeX</h2>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={copyLatex}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium"
                >
                  Copy
                </button>
                <button
                  type="button"
                  onClick={downloadLatex}
                  className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white"
                >
                  Download .tex
                </button>
              </div>
            </div>

            <MonacoField label="LaTeX" language="latex" value={latex} onChange={setLatex} minHeight="500px" />
          </section>
        )}
      </div>
    </main>
  );
}
