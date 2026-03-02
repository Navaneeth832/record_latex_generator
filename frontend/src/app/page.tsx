import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-100 px-4 py-8">
      <div className="mx-auto max-w-5xl space-y-6">
        <header className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <h1 className="text-3xl font-bold text-slate-900">LaTeX Lab Workspace</h1>
          <p className="mt-2 text-sm text-slate-600 md:text-base">
            Choose what you want to do first: generate experiment LaTeX or download a personalized full LaTeX template ZIP.
          </p>
        </header>

        <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Link
            href="/generate"
            className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 transition hover:shadow-md hover:ring-slate-300"
          >
            <h2 className="text-xl font-semibold text-slate-900">Generate Experiment LaTeX</h2>
            <p className="mt-2 text-sm text-slate-600">
              Open the current AI-assisted workflow to upload/paste code, review output, and export experiment LaTeX.
            </p>
            <span className="mt-4 inline-block rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white">Open Generator</span>
          </Link>

          <Link
            href="/template"
            className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 transition hover:shadow-md hover:ring-slate-300"
          >
            <h2 className="text-xl font-semibold text-slate-900">Download LaTeX Template</h2>
            <p className="mt-2 text-sm text-slate-600">
              Fill details like name, lab name, and course code, then download a ZIP with `main.tex`, `cover_page.tex`,
              `follow_page.tex`, and `contents.tex`.
            </p>
            <span className="mt-4 inline-block rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white">Open Template Form</span>
          </Link>
        </section>
      </div>
    </main>
  );
}
