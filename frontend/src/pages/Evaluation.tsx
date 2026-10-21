import { useEffect, useRef, useState } from 'react'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts'
import MetricCard from '../components/MetricCard'
import EvaluationTable from '../components/EvaluationTable'
import {
  listEvalRuns, getEvalRun, startEvalRun, listDatasets, listDocuments, getEvalRunStatus,
} from '../services/api'
import type { EvalRunSummary, EvalRunDetail, QuestionResult, ContextChunk } from '../services/api'

// ── helpers ──────────────────────────────────────────────────────────────────
const fmt = (v?: number | null, digits = 3) =>
  v == null ? '—' : v.toFixed(digits)

const scoreColor = (v?: number | null) => {
  if (v == null) return 'text-gray-400'
  if (v >= 0.75) return 'text-green-400'
  if (v >= 0.5) return 'text-yellow-400'
  return 'text-red-400'
}

const hallucinationBadge = (label?: string) => {
  if (label === 'SUPPORTED') return 'bg-green-900/50 text-green-400 border-green-700'
  if (label === 'PARTIALLY_SUPPORTED') return 'bg-yellow-900/50 text-yellow-400 border-yellow-700'
  return 'bg-red-900/50 text-red-400 border-red-700'
}

// ── sub-components ────────────────────────────────────────────────────────────
function ContextChunkCard({ chunk, index }: { chunk: ContextChunk; index: number }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-gray-700 rounded-lg p-3 text-xs">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-gray-500 font-mono">[Chunk {index}]</span>
          <span className="text-blue-300 font-medium">📄 {chunk.document || 'Unknown'}</span>
          {chunk.page > 0 && <span className="text-gray-400">Page {chunk.page}</span>}
          {chunk.section && <span className="text-gray-500">§ {chunk.section}</span>}
          <span className="text-green-400">Similarity: {chunk.score.toFixed(3)}</span>
        </div>
        <button onClick={() => setOpen(!open)} className="text-gray-500 hover:text-gray-300 ml-2 shrink-0">
          {open ? '▲ Hide' : '▼ Show'}
        </button>
      </div>
      {open && (
        <p className="mt-2 text-gray-300 leading-relaxed border-t border-gray-700 pt-2 whitespace-pre-wrap">
          {chunk.text}
        </p>
      )}
    </div>
  )
}

function QuestionRow({ q, index }: { q: QuestionResult; index: number }) {
  const [open, setOpen] = useState(false)
  const overallScore = ((q.faithfulness ?? 0) + (q.answer_correctness ?? 0)) / 2

  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden">
      {/* Summary row */}
      <button
        onClick={() => setOpen(!open)}
        className="w-full text-left px-4 py-3 hover:bg-gray-750 transition-colors flex items-start gap-3"
      >
        <span className="text-gray-500 font-mono text-xs mt-0.5 shrink-0">#{index + 1}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-200 font-medium truncate">{q.question}</p>
          <div className="flex flex-wrap gap-3 mt-1 text-xs text-gray-400">
            <span className={scoreColor(overallScore)}>Score: {fmt(overallScore)}</span>
            <span className={scoreColor(q.faithfulness)}>Faith: {fmt(q.faithfulness)}</span>
            <span className={scoreColor(q.answer_correctness)}>Correct: {fmt(q.answer_correctness)}</span>
            <span>Recall: {fmt(q.recall_at_k)}</span>
            <span>Precision: {fmt(q.precision_at_k)}</span>
            <span className="text-gray-500">{q.total_latency_ms?.toFixed(0) ?? '—'}ms</span>
            <span className="text-gray-500">{q.context_chunks?.length ?? 0} chunks</span>
            {q.hallucination_label && (
              <span className={`px-1.5 py-0.5 rounded border text-xs ${hallucinationBadge(q.hallucination_label)}`}>
                {q.hallucination_label}
              </span>
            )}
            {q.category && <span className="text-gray-600">{q.category}</span>}
          </div>
        </div>
        <span className="text-gray-500 text-xs shrink-0">{open ? '▲' : '▼'}</span>
      </button>

      {/* Expanded detail */}
      {open && (
        <div className="border-t border-gray-700 px-4 py-4 space-y-4 bg-gray-900/50">
          {/* Answers */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {q.expected_answer && (
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Expected Answer</p>
                <p className="text-xs text-gray-300 leading-relaxed bg-gray-800 rounded p-2">{q.expected_answer}</p>
              </div>
            )}
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Generated Answer</p>
              <p className="text-xs text-gray-300 leading-relaxed bg-gray-800 rounded p-2">
                {q.generated_answer || <span className="text-gray-600 italic">No answer generated</span>}
              </p>
            </div>
          </div>

          {/* Metrics grid */}
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Metrics</p>
            <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
              {[
                { label: 'Faithfulness', value: q.faithfulness },
                { label: 'Correctness', value: q.answer_correctness },
                { label: 'Recall@K', value: q.recall_at_k },
                { label: 'Precision@K', value: q.precision_at_k },
                { label: 'MRR', value: q.reciprocal_rank },
                { label: 'Latency', value: q.total_latency_ms != null ? `${q.total_latency_ms.toFixed(0)}ms` : null },
              ].map(({ label, value }) => (
                <div key={label} className="bg-gray-800 rounded p-2 text-center">
                  <p className="text-gray-500 text-xs">{label}</p>
                  <p className={`text-sm font-semibold mt-0.5 ${typeof value === 'number' ? scoreColor(value) : 'text-gray-300'}`}>
                    {value == null ? '—' : typeof value === 'number' ? value.toFixed(3) : value}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Retrieved context */}
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">
              Retrieved Context ({q.context_chunks?.length ?? 0} chunks)
            </p>
            {q.context_chunks && q.context_chunks.length > 0 ? (
              <div className="space-y-2">
                {q.context_chunks.map((chunk, ci) => (
                  <ContextChunkCard key={chunk.chunk_id || ci} chunk={chunk} index={ci + 1} />
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-600 italic">No context chunks retrieved for this question.</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ── main page ─────────────────────────────────────────────────────────────────
export default function Evaluation() {
  const [runs, setRuns] = useState<EvalRunSummary[]>([])
  const [selectedRun, setSelectedRun] = useState<EvalRunDetail | null>(null)
  const [datasets, setDatasets] = useState<string[]>([])
  const [docIds, setDocIds] = useState<string[]>([])
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)
  const [runSuccess, setRunSuccess] = useState(false)
  const [progress, setProgress] = useState<{ current: number; total: number } | null>(null)
  const [activeRunId, setActiveRunId] = useState<string | null>(null)
  const progressIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const [form, setForm] = useState({
    dataset: 'sample_questions.json',
    top_k: 5,
    chunk_size: 800,
    chunk_overlap: 100,
    similarity_threshold: 0.5,
    prompt_version: 'v1',
  })

  const refresh = () => listEvalRuns().then((r) => setRuns(r.data)).catch(() => {})

  useEffect(() => {
    refresh()
    listDatasets().then((r) => setDatasets(r.data)).catch(() => {})
    listDocuments()
      .then((r) => setDocIds(r.data.filter((d) => d.status === 'ready').map((d) => d.id)))
      .catch(() => {})
    const interval = setInterval(refresh, 5000)
    return () => clearInterval(interval)
  }, [])

  // Poll progress when a run is active
  useEffect(() => {
    if (!activeRunId) return
    progressIntervalRef.current = setInterval(async () => {
      try {
        const res = await getEvalRunStatus(activeRunId)
        const { status, current, total } = res.data
        setProgress({ current, total })
        if (status === 'completed' || status.startsWith('error')) {
          clearInterval(progressIntervalRef.current!)
          setRunning(false)
          setActiveRunId(null)
          setProgress(null)
          if (status.startsWith('error')) {
            setRunError(status.replace('error: ', ''))
          } else {
            setRunSuccess(true)
            setTimeout(() => setRunSuccess(false), 4000)
          }
          await refresh()
          // Auto-select the latest run
          const latest = await listEvalRuns()
          if (latest.data[0]) {
            const detail = await getEvalRun(latest.data[0].id)
            setSelectedRun(detail.data)
          }
        }
      } catch {
        // ignore polling errors
      }
    }, 1500)
    return () => clearInterval(progressIntervalRef.current!)
  }, [activeRunId])

  const handleSelect = async (id: string) => {
    try {
      const r = await getEvalRun(id)
      setSelectedRun(r.data)
    } catch {
      setRunError('Failed to load evaluation run details.')
    }
  }

  const handleRun = async () => {
    if (running) return
    setRunning(true)
    setRunError(null)
    setRunSuccess(false)
    setProgress(null)
    try {
      const res = await startEvalRun({ ...form, document_ids: docIds.length ? docIds : undefined })
      setActiveRunId(res.data.run_id)
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setRunError(detail ?? 'Failed to start evaluation. Check that documents are uploaded and the backend is running.')
      setRunning(false)
    }
  }

  const metrics = selectedRun?.metrics

  // Chart data: comparison of all runs
  const comparisonChartData = runs.slice(0, 8).map((r, i) => ({
    name: `exp-${String(i + 1).padStart(3, '0')}`,
    Faithfulness: r.faithfulness ?? 0,
    Correctness: r.answer_correctness ?? 0,
    'Recall@5': r.recall_at_5 ?? 0,
    'Precision@5': r.precision_at_5 ?? 0,
    MRR: r.mrr ?? 0,
  })).reverse()

  const recallData = metrics
    ? [
        { k: 'K=1', value: metrics.recall_at_1 ?? 0 },
        { k: 'K=3', value: metrics.recall_at_3 ?? 0 },
        { k: 'K=5', value: metrics.recall_at_5 ?? 0 },
        { k: 'K=10', value: metrics.recall_at_10 ?? 0 },
      ]
    : []

  const genData = metrics
    ? [
        { name: 'Faithfulness', value: metrics.faithfulness ?? 0 },
        { name: 'Correctness', value: metrics.answer_correctness ?? 0 },
        { name: 'Ctx Relevance', value: metrics.context_relevance ?? 0 },
        { name: 'Ans Relevance', value: metrics.answer_relevance ?? 0 },
      ]
    : []

  const overallScore = metrics
    ? ((metrics.faithfulness ?? 0) + (metrics.answer_correctness ?? 0) + (metrics.recall_at_5 ?? 0)) / 3
    : null

  const avgChunks = selectedRun?.question_results?.length
    ? selectedRun.question_results.reduce((s, q) => s + (q.context_chunks?.length ?? 0), 0) /
      selectedRun.question_results.length
    : null

  return (
    <div className="p-6 max-w-7xl space-y-8">
      <h1 className="text-xl font-semibold">Evaluation Dashboard</h1>

      {/* ── Run form ── */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
        <h2 className="font-medium mb-3 text-sm text-gray-300">Run Evaluation</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
          <label className="flex flex-col gap-1">
            <span className="text-gray-400 text-xs">Dataset</span>
            <select
              value={form.dataset}
              onChange={(e) => setForm({ ...form, dataset: e.target.value })}
              disabled={running}
              className="bg-gray-700 border border-gray-600 rounded px-2 py-1 disabled:opacity-50"
            >
              {datasets.length === 0 && <option>sample_questions.json</option>}
              {datasets.map((d) => <option key={d}>{d}</option>)}
            </select>
          </label>
          {(['top_k', 'chunk_size', 'chunk_overlap'] as const).map((key) => (
            <label key={key} className="flex flex-col gap-1">
              <span className="text-gray-400 text-xs">{key}</span>
              <input
                type="number"
                value={form[key]}
                disabled={running}
                onChange={(e) => setForm({ ...form, [key]: Number(e.target.value) })}
                className="bg-gray-700 border border-gray-600 rounded px-2 py-1 disabled:opacity-50"
              />
            </label>
          ))}
          <label className="flex flex-col gap-1">
            <span className="text-gray-400 text-xs">Similarity Threshold</span>
            <input
              type="number"
              step="0.05"
              value={form.similarity_threshold}
              disabled={running}
              onChange={(e) => setForm({ ...form, similarity_threshold: Number(e.target.value) })}
              className="bg-gray-700 border border-gray-600 rounded px-2 py-1 disabled:opacity-50"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-gray-400 text-xs">Prompt Version</span>
            <select
              value={form.prompt_version}
              disabled={running}
              onChange={(e) => setForm({ ...form, prompt_version: e.target.value })}
              className="bg-gray-700 border border-gray-600 rounded px-2 py-1 disabled:opacity-50"
            >
              <option>v1</option>
              <option>v2</option>
            </select>
          </label>
        </div>

        <div className="mt-4 flex items-center gap-4 flex-wrap">
          <button
            onClick={handleRun}
            disabled={running}
            className="bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            {running ? '⏳ Running...' : 'Run Evaluation'}
          </button>

          {running && progress && (
            <div className="flex items-center gap-3">
              <div className="w-40 bg-gray-700 rounded-full h-2">
                <div
                  className="bg-blue-500 h-2 rounded-full transition-all"
                  style={{ width: `${progress.total > 0 ? (progress.current / progress.total) * 100 : 0}%` }}
                />
              </div>
              <span className="text-xs text-gray-400">
                Evaluating {progress.current} / {progress.total} questions...
              </span>
            </div>
          )}
          {running && !progress && (
            <span className="text-xs text-gray-400 animate-pulse">Initializing evaluation...</span>
          )}
          {runSuccess && (
            <span className="text-xs text-green-400 font-medium">✓ Evaluation completed successfully</span>
          )}
          {runError && (
            <span className="text-xs text-red-400">✗ {runError}</span>
          )}
        </div>
      </div>

      {/* ── Overall metrics ── */}
      {metrics ? (
        <div>
          <h2 className="text-sm font-medium text-gray-300 mb-3">
            Evaluation Results
            {selectedRun && (
              <span className="ml-2 text-gray-500 font-normal text-xs">
                — {selectedRun.dataset_name} · {selectedRun.num_questions} questions ·{' '}
                {selectedRun.created_at ? new Date(selectedRun.created_at).toLocaleString() : ''}
              </span>
            )}
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard label="Overall Score" value={overallScore} color="blue" sub="avg of faith+correct+recall" />
            <MetricCard label="Faithfulness" value={metrics.faithfulness} color="green" sub="answer grounded in context" />
            <MetricCard label="Answer Correctness" value={metrics.answer_correctness} color="blue" sub="vs expected answer" />
            <MetricCard label="Context Relevance" value={metrics.context_relevance} color="purple" sub="context matches question" />
            <MetricCard label="Answer Relevance" value={metrics.answer_relevance} color="purple" sub="answer matches question" />
            <MetricCard label="Recall@5" value={metrics.recall_at_5} color="green" sub="relevant chunks retrieved" />
            <MetricCard label="Precision@5" value={metrics.precision_at_5} color="blue" sub="retrieved chunks relevant" />
            <MetricCard label="MRR" value={metrics.mrr} color="yellow" sub="mean reciprocal rank" />
            <MetricCard label="Hit Rate" value={metrics.hit_rate} color="green" sub="any relevant chunk found" />
            <MetricCard label="Hallucination Rate" value={metrics.hallucination_rate} color="red" sub="unsupported answers" />
            <MetricCard
              label="Avg Latency"
              value={metrics.avg_latency_ms != null ? `${metrics.avg_latency_ms.toFixed(0)}ms` : null}
              color="yellow"
              sub={`p95: ${metrics.p95_latency_ms?.toFixed(0) ?? '—'}ms`}
            />
            <MetricCard
              label="Avg Retrieved Chunks"
              value={avgChunks != null ? avgChunks.toFixed(1) : null}
              color="blue"
              sub="per question"
            />
          </div>
        </div>
      ) : (
        runs.length === 0 && (
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-8 text-center text-gray-500">
            <p className="text-3xl mb-3">📊</p>
            <p className="text-sm font-medium text-gray-400">No evaluation results yet.</p>
            <p className="text-xs mt-2 text-gray-600">
              Upload documents and run your first evaluation to see RAG quality metrics,
              question-level results, retrieved context, and experiment comparisons.
            </p>
          </div>
        )
      )}

      {/* ── Charts ── */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
            <h3 className="text-sm font-medium mb-3 text-gray-300">Recall@K</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={recallData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="k" tick={{ fill: '#9ca3af', fontSize: 12 }} />
                <YAxis domain={[0, 1]} tick={{ fill: '#9ca3af', fontSize: 12 }} />
                <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }} />
                <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
            <h3 className="text-sm font-medium mb-3 text-gray-300">Generation Quality</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RadarChart data={genData}>
                <PolarGrid stroke="#374151" />
                <PolarAngleAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                <Radar dataKey="value" stroke="#10b981" fill="#10b981" fillOpacity={0.3} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* ── Experiment comparison chart (multi-run) ── */}
      {runs.length > 1 && (
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
          <h3 className="text-sm font-medium mb-3 text-gray-300">Experiment Comparison — Metrics Over Runs</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={comparisonChartData} margin={{ left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <YAxis domain={[0, 1]} tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }} />
              <Legend wrapperStyle={{ fontSize: 11, color: '#9ca3af' }} />
              <Bar dataKey="Faithfulness" fill="#10b981" radius={[3, 3, 0, 0]} />
              <Bar dataKey="Correctness" fill="#3b82f6" radius={[3, 3, 0, 0]} />
              <Bar dataKey="Recall@5" fill="#8b5cf6" radius={[3, 3, 0, 0]} />
              <Bar dataKey="Precision@5" fill="#f59e0b" radius={[3, 3, 0, 0]} />
              <Bar dataKey="MRR" fill="#ec4899" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Experiment table ── */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
        <h2 className="font-medium mb-3 text-sm text-gray-300">Experiment Comparison</h2>
        <EvaluationTable runs={runs} onSelect={handleSelect} selectedId={selectedRun?.id} />
      </div>

      {/* ── Question-level results ── */}
      {selectedRun && (
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
          <h2 className="font-medium mb-1 text-sm text-gray-300">Question-level Results</h2>
          {selectedRun.question_results && selectedRun.question_results.length > 0 ? (
            <>
              <p className="text-xs text-gray-500 mb-3">
                {selectedRun.question_results.length} questions evaluated. Click a row to expand details and inspect retrieved context.
              </p>
              <div className="space-y-2">
                {selectedRun.question_results.map((q, i) => (
                  <QuestionRow key={i} q={q} index={i} />
                ))}
              </div>
            </>
          ) : (
            <p className="text-xs text-gray-500 py-4 text-center">
              {selectedRun.dataset_name?.startsWith('ERROR')
                ? `Evaluation failed: ${selectedRun.dataset_name}`
                : 'Evaluation is still running or no question results are available yet.'}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
