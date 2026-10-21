import { useEffect, useState } from 'react'
import DocumentUpload from '../components/DocumentUpload'
import { listDocuments, deleteDocument } from '../services/api'
import type { Document } from '../services/api'

const statusColor = {
  ready: 'text-green-400',
  processing: 'text-yellow-400',
  error: 'text-red-400',
}

const fmtSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function Documents() {
  const [docs, setDocs] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)

  const refresh = () => {
    listDocuments().then((r) => {
      setDocs(r.data)
      setLoading(false)
    })
  }

  useEffect(() => {
    refresh()
    // Poll for processing status
    const interval = setInterval(refresh, 3000)
    return () => clearInterval(interval)
  }, [])

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this document?')) return
    await deleteDocument(id)
    refresh()
  }

  return (
    <div className="p-6 max-w-4xl">
      <h1 className="text-xl font-semibold mb-6">Documents</h1>
      <DocumentUpload onUploaded={refresh} />

      <div className="mt-6 space-y-3">
        {loading && <p className="text-gray-500 text-sm">Loading...</p>}
        {!loading && docs.length === 0 && (
          <p className="text-gray-500 text-sm">No documents uploaded yet.</p>
        )}
        {docs.map((doc) => (
          <div
            key={doc.id}
            className="bg-gray-800 border border-gray-700 rounded-xl p-4 flex items-center justify-between"
          >
            <div>
              <p className="font-medium text-sm">{doc.name}</p>
              <div className="flex gap-4 mt-1 text-xs text-gray-400">
                <span>{fmtSize(doc.file_size_bytes)}</span>
                {doc.num_chunks > 0 && <span>{doc.num_chunks} chunks</span>}
                {doc.chunk_size && <span>chunk_size={doc.chunk_size}</span>}
                <span>{new Date(doc.created_at).toLocaleDateString()}</span>
              </div>
              {doc.error_message && (
                <p className="text-red-400 text-xs mt-1">{doc.error_message}</p>
              )}
            </div>
            <div className="flex items-center gap-4">
              <span className={`text-xs font-medium ${statusColor[doc.status]}`}>
                {doc.status === 'ready' ? '✓ Ready' : doc.status === 'processing' ? '⟳ Processing' : '✗ Error'}
              </span>
              <button
                onClick={() => handleDelete(doc.id)}
                className="text-gray-500 hover:text-red-400 text-xs transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
