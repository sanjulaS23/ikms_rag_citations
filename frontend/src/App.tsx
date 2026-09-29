import { useMemo, useRef, useState } from "react";

type CitationInfo = {
  page: number | null;
  snippet: string | null;
  source: string | null;
};

type QAResponse = {
  answer: string;
  context: string;
  citations: Record<string, CitationInfo> | null;
};

type AnswerPart = {
  text: string;
  citationId?: string;
};

const citationRegex = /\[C\d+\]/g;

const parseAnswer = (answer: string): AnswerPart[] => {
  const parts: AnswerPart[] = [];
  let lastIndex = 0;
  const matches = answer.matchAll(citationRegex);

  for (const match of matches) {
    const index = match.index ?? 0;
    if (index > lastIndex) {
      parts.push({ text: answer.slice(lastIndex, index) });
    }
    const raw = match[0];
    parts.push({ text: raw, citationId: raw.slice(1, -1) });
    lastIndex = index + raw.length;
  }

  if (lastIndex < answer.length) {
    parts.push({ text: answer.slice(lastIndex) });
  }

  return parts;
};

export default function App() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Record<string, CitationInfo> | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [indexStatus, setIndexStatus] = useState<string | null>(null);
  const sourceRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const answerParts = useMemo(() => parseAnswer(answer), [answer]);
  const REQUEST_TIMEOUT_MS = 180000;

  const handleUploadPDF = async () => {
    if (!selectedFile) {
      setError("Please choose a PDF file to upload.");
      return;
    }

    const file = selectedFile;
    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("/upload-pdf", {
        method: "POST",
        body: formData,
      });

      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(payload?.detail || "Upload failed");
      }

      const chunksIndexed = payload?.chunks_indexed ?? 0;
      const source = payload?.source || file.name;
      setIndexStatus(`Indexed ${chunksIndexed} chunks from ${source}.`);
      setSelectedFile(null);
      const fileInput = document.getElementById("pdf-upload") as HTMLInputElement | null;
      if (fileInput) fileInput.value = "";
    } catch (err) {
      const message = err instanceof Error ? err.message : "Upload failed";
      setError(message);
    } finally {
      setUploading(false);
    }
  };

  const handleSubmit = async () => {
    if (!question.trim()) {
      setError("Please enter a question.");
      return;
    }

    setLoading(true);
    setError(null);
    setAnswer("");
    setCitations(null);
    setSelectedCitation(null);

    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
      const response = await fetch("/qa", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || "Request failed");
      }

      const data = (await response.json()) as QAResponse;
      setAnswer(data.answer || "No answer returned.");
      setCitations(data.citations);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message.includes("aborted") ? "Request timed out." : message);
    } finally {
      window.clearTimeout(timer);
      setLoading(false);
    }
  };

  const handleCitationClick = (citationId: string) => {
    setSelectedCitation(citationId);
    const target = sourceRefs.current[citationId];
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  };

  return (
    <div className="min-h-screen bg-[#0b1220] px-4 py-8 text-slate-100 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-6 flex flex-col gap-4 rounded-2xl border border-slate-800 bg-[#111827]/90 px-5 py-4 shadow-[0_10px_30px_rgba(15,23,42,0.35)] backdrop-blur-sm sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">IKMS RAG</p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-white">Knowledge Assistant</h1>
          </div>
          <div className="flex items-center gap-2 self-start rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-300 sm:self-center">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            Local model online
          </div>
        </header>

        <main className="grid gap-6 lg:grid-cols-[1.35fr,0.95fr]">
          <section className="rounded-3xl border border-slate-800 bg-[#111827] p-5 shadow-[0_10px_30px_rgba(15,23,42,0.35)] sm:p-6">
            <div className="mb-5 flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-slate-400">Document workspace</p>
                <h2 className="mt-1 text-xl font-semibold text-white">Upload and query</h2>
              </div>
              <div className="rounded-full border border-sky-500/30 bg-sky-500/10 px-3 py-1 text-xs font-medium text-sky-300">
                Evidence-backed
              </div>
            </div>

            <div className="rounded-2xl border border-slate-700 bg-[#0f172a] p-4">
              <label className="mb-3 block text-sm font-medium text-slate-300">Upload PDF</label>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <input
                  id="pdf-upload"
                  type="file"
                  accept="application/pdf"
                  className="block w-full rounded-xl border border-slate-700 bg-[#0b1220] px-3 py-2.5 text-sm text-slate-200 file:mr-3 file:rounded-full file:border-0 file:bg-slate-200 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-slate-900 file:cursor-pointer"
                  onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                />
                <button
                  className="rounded-xl bg-sky-500 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-60"
                  onClick={handleUploadPDF}
                  disabled={uploading || !selectedFile}
                >
                  {uploading ? "Uploading..." : "Upload PDF"}
                </button>
              </div>

              {selectedFile && (
                <p className="mt-3 text-xs text-slate-400">Selected file: {selectedFile.name}</p>
              )}
              {indexStatus && (
                <p className="mt-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300">
                  {indexStatus}
                </p>
              )}
            </div>

            <div className="mt-6">
              <label className="mb-2 block text-sm font-medium text-slate-300">Question</label>
              <textarea
                className="w-full min-h-[150px] rounded-2xl border border-slate-700 bg-[#0f172a] px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-sky-500 focus:bg-[#111827] focus:ring-4 focus:ring-sky-500/10"
                placeholder="Ask a question about the uploaded document..."
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
              />
            </div>

            <div className="mt-5 flex items-center gap-3">
              <button
                className="rounded-xl bg-sky-500 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-60"
                onClick={handleSubmit}
                disabled={loading}
              >
                {loading ? "Working..." : "Submit question"}
              </button>
              {loading && (
                <div className="inline-flex items-center gap-2 text-sm text-slate-400">
                  <span className="h-2 w-2 rounded-full bg-sky-400 animate-pulse" />
                  Retrieving and verifying evidence
                </div>
              )}
            </div>

            {error && (
              <div className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">
                {error}
              </div>
            )}

            <div className="mt-8">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-white">Answer</h3>
                {answer && <span className="text-xs font-medium uppercase tracking-[0.2em] text-slate-400">Verified</span>}
              </div>

              <div className="min-h-[180px] rounded-2xl border border-slate-700 bg-[#0f172a] p-4">
                {answer ? (
                  <p className="leading-7 text-slate-100">
                    {answerParts.map((part, index) =>
                      part.citationId ? (
                        <button
                          key={`${part.citationId}-${index}`}
                          className={`mx-1 inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold transition ${
                            selectedCitation === part.citationId
                              ? "border-sky-400 bg-sky-500/10 text-sky-300"
                              : "border-slate-600 bg-slate-900 text-slate-300 hover:border-sky-400 hover:text-sky-300"
                          }`}
                          onClick={() => handleCitationClick(part.citationId!)}
                          title={`Jump to ${part.citationId}`}
                        >
                          {part.text}
                        </button>
                      ) : (
                        <span key={index}>{part.text}</span>
                      )
                    )}
                  </p>
                ) : (
                  <p className="text-base text-slate-400">Submit a question to see evidence-backed answers.</p>
                )}
              </div>
            </div>
          </section>

          <aside className="rounded-3xl border border-slate-800 bg-[#111827] p-5 shadow-[0_10px_30px_rgba(15,23,42,0.35)] sm:p-6">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-lg font-semibold text-white">Source evidence</h3>
              <div className="rounded-full border border-slate-700 bg-slate-900 px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.2em] text-slate-400">
                {citations ? Object.keys(citations).length : 0} chunks
              </div>
            </div>

            <div className="mt-5 space-y-4">
              {citations ? (
                Object.entries(citations).map(([id, info]) => (
                  <div
                    key={id}
                    ref={(el) => {
                      sourceRefs.current[id] = el;
                    }}
                    className={`rounded-2xl border p-4 transition ${
                      selectedCitation === id
                        ? "border-sky-500/40 bg-sky-500/10"
                        : "border-slate-700 bg-[#0f172a]"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-semibold text-sky-300">{id}</span>
                      <span className="text-[11px] font-medium text-slate-400">Page {info.page ?? "?"}</span>
                    </div>
                    <p className="mt-2 text-[10px] font-medium uppercase tracking-[0.2em] text-slate-400">
                      {info.source ?? "Unknown source"}
                    </p>
                    <p className="mt-3 text-sm leading-6 text-slate-300" title={info.snippet ?? "No snippet"}>
                      {info.snippet ?? "Snippet unavailable."}
                    </p>
                  </div>
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-700 bg-[#0f172a] p-5 text-sm text-slate-400">
                  Sources will appear after a successful query.
                </div>
              )}
            </div>
          </aside>
        </main>
      </div>
    </div>
  );
}
