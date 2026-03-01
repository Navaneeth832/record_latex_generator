"use client";

import { useState } from "react";
import MonacoField from "@/components/MonacoField";
import { AlgorithmData, ExperimentData } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

const emptyExperiment: ExperimentData = {
  experiment_number: "1",
  date: new Date().toLocaleDateString("en-GB"),
  experiment_heading: "Operating System Programs",
  title: "",
  aim: "",
  algorithms: [],
  programs: [],
  result: "Program executed and output verified successfully.",
};

export default function Home() {
  const [data, setData] = useState<ExperimentData>(emptyExperiment);
  const [latex, setLatex] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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
      const json = await res.json();
      setData(json);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
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

  const updateAlgorithm = (index: number, algo: AlgorithmData) => {
    const next = [...data.algorithms];
    next[index] = algo;
    setData({ ...data, algorithms: next });
  };

  return (
    <main className="mx-auto max-w-6xl p-6 space-y-6">
      <h1 className="text-3xl font-bold">AI LaTeX Lab Generator</h1>

      <div className="rounded bg-white p-4 shadow space-y-3">
        <input
          type="file"
          accept=".pdf,.txt,.zip"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) uploadFile(file);
          }}
          className="block w-full rounded border p-2"
        />
        {loading && <p className="text-blue-600">Processing...</p>}
        {error && <p className="text-red-600 whitespace-pre-wrap">{error}</p>}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 rounded bg-white p-4 shadow">
        <input
          value={data.experiment_number}
          onChange={(e) => setData({ ...data, experiment_number: e.target.value })}
          className="rounded border p-2"
          placeholder="Experiment Number"
        />
        <input
          value={data.date}
          onChange={(e) => setData({ ...data, date: e.target.value })}
          className="rounded border p-2"
          placeholder="Date"
        />
        <input
          value={data.experiment_heading}
          onChange={(e) => setData({ ...data, experiment_heading: e.target.value })}
          className="rounded border p-2 md:col-span-2"
          placeholder="Heading"
        />
        <input
          value={data.title}
          onChange={(e) => setData({ ...data, title: e.target.value })}
          className="rounded border p-2 md:col-span-2"
          placeholder="Title"
        />
        <textarea
          value={data.aim}
          onChange={(e) => setData({ ...data, aim: e.target.value })}
          className="rounded border p-2 md:col-span-2"
          rows={4}
          placeholder="AIM"
        />
      </div>

      <div className="space-y-4">
        {data.algorithms.map((algo, i) => (
          <div key={i} className="rounded bg-white p-4 shadow space-y-2">
            <input
              value={algo.name}
              onChange={(e) => updateAlgorithm(i, { ...algo, name: e.target.value })}
              className="rounded border p-2 w-full"
              placeholder={`Algorithm ${i + 1} Name`}
            />
            <MonacoField
              label="Algorithm Steps (one step per line)"
              language="markdown"
              value={algo.steps.join("\n")}
              onChange={(value) =>
                updateAlgorithm(i, {
                  ...algo,
                  steps: value.split("\n").map((s) => s.trim()).filter(Boolean),
                })
              }
              minHeight="180px"
            />
          </div>
        ))}
      </div>

      <div className="space-y-6">
        {data.programs.map((program, i) => (
          <div key={i} className="rounded bg-white p-4 shadow space-y-3">
            <h2 className="text-xl font-semibold">Listing {i + 1}</h2>
            <input
              value={program.title}
              onChange={(e) => {
                const next = [...data.programs];
                next[i] = { ...program, title: e.target.value };
                setData({ ...data, programs: next });
              }}
              className="rounded border p-2 w-full"
              placeholder="Program title"
            />
            <MonacoField
              label="Program Code"
              language="c"
              value={program.code}
              onChange={(value) => {
                const next = [...data.programs];
                next[i] = { ...program, code: value };
                setData({ ...data, programs: next });
              }}
              minHeight="280px"
            />
            <MonacoField
              label="Program Output"
              language="plaintext"
              value={program.output}
              onChange={(value) => {
                const next = [...data.programs];
                next[i] = { ...program, output: value };
                setData({ ...data, programs: next });
              }}
              minHeight="180px"
            />
          </div>
        ))}
      </div>

      <button
        onClick={generateLatex}
        disabled={loading || data.programs.length === 0}
        className="rounded bg-black px-4 py-2 text-white disabled:opacity-50"
      >
        Generate LaTeX
      </button>

      {latex && (
        <div className="rounded bg-white p-4 shadow space-y-2">
          <h2 className="text-xl font-semibold">Generated LaTeX</h2>
          <MonacoField
            label="LaTeX"
            language="latex"
            value={latex}
            onChange={setLatex}
            minHeight="500px"
          />
        </div>
      )}
    </main>
  );
}
