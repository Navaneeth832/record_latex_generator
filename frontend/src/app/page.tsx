"use client";

import { useMemo, useState } from "react";
import MonacoField from "@/components/MonacoField";
import { ExperimentData } from "@/lib/types";
import { parseProgramsFromText } from "@/lib/parsePrograms";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type InputMode = "upload" | "paste";
type Step = 1 | 2 | 3;

const emptyExperiment: ExperimentData = {
  experiment_number: "1",
  date: new Date().toLocaleDateString("en-GB"),
  experiment_heading: "",
  aim: "",
  algorithms: [],
  programs: [],
  result: "",
};

function StepIndicator({ step }: { step: Step }) {
  const items = [
    { id: 1, label: "Input" },
    { id: 2, label: "Review & Correct" },
    { id: 3, label: "Final LaTeX" },
  ] as const;

  return (
    <div className="flex flex-wrap items-center gap-3">
      {items.map((item, index) => (
        <div key={item.id} className="flex items-center gap-3">
          <div
            className={`flex h-9 w-9 items-center justify-center rounded-full text-sm font-semibold transition-all ${
              step >= item.id ? "bg-slate-900 text-white" : "bg-slate-200 text-slate-600"
            }`}
          >
            {item.id}
          </div>
          <span className={`text-sm ${step >= item.id ? "text-slate-900" : "text-slate-500"}`}>{item.label}</span>
          {index < items.length - 1 && <div className="h-px w-8 bg-slate-300" />}
        </div>
      ))}
    </div>
  );
}

export default function Home() {
  const [mode, setMode] = useState<InputMode>("upload");
  const [step, setStep] = useState<Step>(1);
  const [data, setData] = useState<ExperimentData>(emptyExperiment);
  const [latex, setLatex] = useState("");
  const [pastedText, setPastedText] = useState("");
  const [uploadFileData, setUploadFileData] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const parsedPrograms = useMemo(() => parseProgramsFromText(pastedText), [pastedText]);

  const resetMessages = () => {
    setError("");
    setSuccess("");
  };

  const generateExperiment = async () => {
    setLoading(true);
    resetMessages();
    setLatex("");

    try {
      if (mode === "upload") {
        if (!uploadFileData) {
          throw new Error("Please select a file to generate experiment data.");
        }

        const formData = new FormData();
        formData.append("file", uploadFileData);

        const res = await fetch(`${API_BASE}/api/upload-process`, {
          method: "POST",
          body: formData,
        });

        if (!res.ok) {
          throw new Error(await res.text());
        }

        setData(await res.json());
      } else {
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
      }

      setStep(2);
      setSuccess("Experiment generated successfully. Review and correct if needed.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Experiment generation failed");
    } finally {
      setLoading(false);
    }
  };

  const regenerate = async () => {
    await generateExperiment();
  };

  const generateLatex = async () => {
    setLoading(true);
    resetMessages();

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
      setStep(3);
      setSuccess("Final LaTeX generated successfully.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "LaTeX generation failed");
    } finally {
      setLoading(false);
    }
  };

  const copyLatex = async () => {
    await navigator.clipboard.writeText(latex);
    setSuccess("LaTeX copied to clipboard.");
  };

  const downloadLatex = () => {
    const blob = new Blob([latex], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "experiment.tex";
    a.click();
    URL.revokeObjectURL(url);
    setSuccess("Downloaded experiment.tex");
  };

  return (
    <main className="min-h-screen bg-slate-100 px-4 py-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <h1 className="text-2xl font-bold text-slate-900 md:text-3xl">AI LaTeX Lab Generator</h1>
          <p className="mt-2 text-sm text-slate-600 md:text-base">
            Human-in-the-loop workflow: Generate with AI, review and correct, then export final LaTeX.
          </p>
          <div className="mt-5">
            <StepIndicator step={step} />
          </div>
        </header>

        {success && <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div>}
        {error && <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

        <section className={`rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 transition-all ${step === 1 ? "opacity-100" : "opacity-95"}`}>
          <h2 className="text-lg font-semibold text-slate-900">Step 1 — Input & AI Generation</h2>

          <div className="mt-4 inline-flex rounded-xl bg-slate-100 p-1">
            <button
              type="button"
              onClick={() => setMode("upload")}
              className={`rounded-lg px-4 py-2 text-sm font-medium ${mode === "upload" ? "bg-white text-slate-900 shadow" : "text-slate-600"}`}
            >
              Upload File
            </button>
            <button
              type="button"
              onClick={() => setMode("paste")}
              className={`rounded-lg px-4 py-2 text-sm font-medium ${mode === "paste" ? "bg-white text-slate-900 shadow" : "text-slate-600"}`}
            >
              Paste Code
            </button>
          </div>

          <div className="mt-4 space-y-4">
            {mode === "upload" ? (
              <>
                <label className="block text-sm font-semibold text-slate-700">Upload source file</label>
                <input
                  type="file"
                  accept=".pdf,.txt,.zip,.bin"
                  onChange={(e) => setUploadFileData(e.target.files?.[0] ?? null)}
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
                <p className="text-sm text-slate-600">
                  Parsed programs: <span className="font-semibold">{parsedPrograms.length}</span>
                </p>
              </>
            )}
          </div>

          <div className="mt-5">
            <button
              type="button"
              onClick={generateExperiment}
              disabled={loading}
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
            >
              {loading ? "Generating..." : "Generate Experiment"}
            </button>
          </div>
        </section>

        {step >= 2 && (
          <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 transition-all">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <h2 className="text-lg font-semibold text-slate-900">Step 2 — Review & Correct Experiment</h2>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={regenerate}
                  disabled={loading}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium"
                >
                  Regenerate
                </button>
                <button
                  type="button"
                  onClick={generateLatex}
                  disabled={loading || data.programs.length === 0}
                  className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
                >
                  Generate Final LaTeX
                </button>
              </div>
            </div>

            <div className="mt-5 space-y-4">
              <details open className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <summary className="cursor-pointer font-semibold text-slate-900">Experiment Details</summary>
                <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
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
                  <input
                    value={data.experiment_heading}
                    onChange={(e) => setData({ ...data, experiment_heading: e.target.value })}
                    className="rounded-lg border border-slate-300 p-2 md:col-span-2"
                    placeholder="Experiment Heading"
                  />
                </div>
              </details>

              <details open className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <summary className="cursor-pointer font-semibold text-slate-900">AIM</summary>
                <textarea
                  value={data.aim}
                  onChange={(e) => setData({ ...data, aim: e.target.value })}
                  className="mt-4 w-full rounded-lg border border-slate-300 p-3"
                  rows={5}
                />
              </details>

              <details open className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <summary className="cursor-pointer font-semibold text-slate-900">Algorithms</summary>
                <div className="mt-4 space-y-4">
                  {data.algorithms.map((algo, index) => (
                    <div key={index} className="rounded-lg border border-slate-200 bg-white p-3">
                      <input
                        value={algo.name}
                        onChange={(e) => {
                          const next = [...data.algorithms];
                          next[index] = { ...algo, name: e.target.value };
                          setData({ ...data, algorithms: next });
                        }}
                        className="w-full rounded-lg border border-slate-300 p-2"
                        placeholder={`Algorithm ${index + 1} Name`}
                      />
                      <MonacoField
                        label="Steps (editable, one step per line)"
                        language="markdown"
                        value={algo.steps.join("\n")}
                        onChange={(value) => {
                          const next = [...data.algorithms];
                          next[index] = {
                            ...algo,
                            steps: value
                              .split("\n")
                              .map((stepText) => stepText.trim())
                              .filter(Boolean),
                          };
                          setData({ ...data, algorithms: next });
                        }}
                        minHeight="160px"
                      />
                    </div>
                  ))}
                </div>
              </details>

              <details open className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <summary className="cursor-pointer font-semibold text-slate-900">Programs & Output</summary>
                <div className="mt-4 space-y-4">
                  {data.programs.map((program, index) => (
                    <div key={index} className="rounded-lg border border-slate-200 bg-white p-3 space-y-3">
                      <input
                        value={program.title}
                        onChange={(e) => {
                          const next = [...data.programs];
                          next[index] = { ...program, title: e.target.value };
                          setData({ ...data, programs: next });
                        }}
                        className="w-full rounded-lg border border-slate-300 p-2"
                        placeholder={`Program ${index + 1} Title`}
                      />
                      <MonacoField label="Program Code (read-only)" language="c" value={program.code} onChange={() => {}} minHeight="220px" readOnly />
                      <MonacoField label="Execution Output (read-only)" language="plaintext" value={program.output} onChange={() => {}} minHeight="140px" readOnly />
                    </div>
                  ))}
                </div>
              </details>

              <details open className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <summary className="cursor-pointer font-semibold text-slate-900">Result</summary>
                <textarea
                  value={data.result}
                  onChange={(e) => setData({ ...data, result: e.target.value })}
                  className="mt-4 w-full rounded-lg border border-slate-300 p-3"
                  rows={4}
                />
              </details>
            </div>
          </section>
        )}

        {step >= 3 && latex && (
          <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 transition-all">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <h2 className="text-xl font-semibold">Step 3 — Final LaTeX</h2>
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

            <div className="mt-4">
              <MonacoField label="Generated LaTeX" language="latex" value={latex} onChange={setLatex} minHeight="500px" />
            </div>
          </section>
        )}

        {loading && <div className="rounded-xl bg-blue-50 px-4 py-3 text-sm text-blue-700">Processing... Please wait.</div>}
      </div>
    </main>
  );
}
