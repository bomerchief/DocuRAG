import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 429) {
      err.message = 'Too many requests. Please wait a moment and try again.'
    }
    return Promise.reject(err)
  }
)

export interface Document {
  id: string
  name: string
  file_type: string
  file_size_bytes: number
  num_chunks: number
  status: 'processing' | 'ready' | 'error'
  error_message?: string
  created_at: string
  chunk_size?: number
  chunk_overlap?: number
  embedding_model?: string
}

export interface Source {
  chunk_id: string
  document: string
  page: number
  score: number
  snippet: string
  section?: string
}

export interface ChatMetrics {
  retrieval_latency_ms: number
  generation_latency_ms: number
  total_latency_ms: number
  chunks_retrieved: number
  prompt_size: number
  response_length: number
}

export interface WebSource {
  title: string
  url: string
  snippet: string
}

export interface ChatResponse {
  query_id: string
  answer: string
  sources: Source[]
  web_sources: WebSource[]
  metrics: ChatMetrics
}

export interface EvalRunSummary {
  id: string
  dataset_name: string
  embedding_model: string
  llm_model: string
  chunk_size: number
  chunk_overlap: number
  top_k: number
  similarity_threshold: number
  prompt_version: string
  num_questions: number
  recall_at_5?: number
  precision_at_5?: number
  mrr?: number
  faithfulness?: number
  answer_correctness?: number
  hallucination_rate?: number
  avg_latency_ms?: number
  created_at: string
}

export interface EvalRunDetail extends EvalRunSummary {
  config: Record<string, unknown>
  metrics: Record<string, number | null>
  question_results: QuestionResult[]
}

export interface QuestionResult {
  question: string
  expected_answer: string
  generated_answer: string
  recall_at_k?: number
  precision_at_k?: number
  reciprocal_rank?: number
  hit?: number
  faithfulness?: number
  answer_correctness?: number
  hallucination_label?: string
  retrieval_latency_ms?: number
  generation_latency_ms?: number
  total_latency_ms?: number
  retrieved_chunk_ids?: string[]
  retrieved_scores?: number[]
  context_chunks?: ContextChunk[]
  category?: string
  difficulty?: string
}

export interface ContextChunk {
  chunk_id: string
  document: string
  page: number
  section?: string
  score: number
  text: string
}

export interface EvalRunProgress {
  run_id: string
  status: string
  current: number
  total: number
}

// Documents
export const uploadDocument = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api.post<Document>('/documents', form)
}
export const listDocuments = () => api.get<Document[]>('/documents')
export const deleteDocument = (id: string) => api.delete(`/documents/${id}`)

// Chat
export const sendChat = (question: string, documentIds?: string[], topK?: number) =>
  api.post<ChatResponse>('/chat', { question, document_ids: documentIds, top_k: topK })

export const getChatHistory = (limit = 50) =>
  api.get<ChatResponse[]>(`/chat/history?limit=${limit}`)

export const inspectQuery = (queryId: string) =>
  api.get(`/chat/${queryId}/inspect`)

export const getMonitoring = () => api.get('/monitoring')

// Evaluation
export const startEvalRun = (params: {
  dataset: string
  top_k: number
  chunk_size: number
  chunk_overlap: number
  similarity_threshold: number
  prompt_version: string
  document_ids?: string[]
}) => api.post<{ run_id: string; status: string }>('/evaluation/run', params)

export const listEvalRuns = () => api.get<EvalRunSummary[]>('/evaluation/runs')
export const getEvalRun = (id: string) => api.get<EvalRunDetail>(`/evaluation/runs/${id}`)
export const getEvalRunStatus = (id: string) => api.get<EvalRunProgress>(`/evaluation/runs/${id}/status`)
export const listDatasets = () => api.get<string[]>('/evaluation/datasets')

// Health
export const getHealth = () => api.get('/health')
export const getConfig = () => api.get('/health/config')
