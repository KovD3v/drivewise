import { useEffect, useMemo, useState } from 'react'
import { Link } from '@tanstack/react-router'

import { fetchDocument, IngestedDocument } from '../api/drivewise'
import { errorMessage } from './viewUtils'

export function DocumentDetailPage({ documentId }: { documentId: string }) {
  const [document, setDocument] = useState<IngestedDocument | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let isCurrent = true
    setIsLoading(true)
    setError(null)

    fetchDocument(documentId)
      .then((data) => {
        if (isCurrent) {
          setDocument(data)
        }
      })
      .catch((caughtError) => {
        if (isCurrent) {
          setError(errorMessage(caughtError, 'Unable to load document'))
          setDocument(null)
        }
      })
      .finally(() => {
        if (isCurrent) {
          setIsLoading(false)
        }
      })

    return () => {
      isCurrent = false
    }
  }, [documentId])

  const safeMetadata = useMemo(
    () => stripEmbeddingKeys(document?.metadata ?? {}),
    [document],
  )

  return (
    <main className="browse-shell">
      <header className="browse-header">
        <Link className="text-link" to="/documents">
          Documenti
        </Link>
        <div>
          <p className="eyebrow">Document detail</p>
          <h1>{document ? document.title : 'Dettaglio documento'}</h1>
          {document ? (
            <p className="summary">
              {document.document_type} · {formatDateTime(document.created_at)}
            </p>
          ) : null}
        </div>
      </header>

      <section className="detail-panel" aria-live="polite">
        {isLoading ? <p className="status-message">Caricamento…</p> : null}
        {error ? <p className="error-message">{error}</p> : null}

        {document ? (
          <>
            <dl className="facts-grid detail-facts">
              <Fact label="Document type" value={document.document_type} />
              <Fact label="Source id" value={document.source_id} />
              <Fact label="Vehicle id" value={document.vehicle_id ?? '-'} />
              <Fact label="Listing id" value={document.listing_id ?? '-'} />
              <Fact label="Created at" value={formatDateTime(document.created_at)} />
            </dl>

            <section className="detail-section">
              <h2>Content</h2>
              <pre className="content-block">{document.content}</pre>
            </section>

            <section className="detail-section">
              <h2>Metadata</h2>
              <pre className="metadata-pre">
                {JSON.stringify(safeMetadata, null, 2)}
              </pre>
            </section>
          </>
        ) : null}
      </section>
    </main>
  )
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  )
}

function stripEmbeddingKeys(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(stripEmbeddingKeys)
  }

  if (!isPlainObject(value)) {
    return value
  }

  return Object.fromEntries(
    Object.entries(value)
      .filter(([key]) => key !== 'embedding' && key !== 'embedding_model')
      .map(([key, item]) => [key, stripEmbeddingKeys(item)]),
  )
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function formatDateTime(value: string) {
  return value.replace('T', ' ').replace('Z', ' UTC')
}
