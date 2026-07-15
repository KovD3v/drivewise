import { FormEvent, useState } from 'react'
import { Link } from '@tanstack/react-router'

import {
  DocumentFilters,
  fetchDocuments,
  IngestedDocument,
} from '../api/drivewise'
import { errorMessage, optionalNumber } from './viewUtils'

export function DocumentListPage({
  initialDocuments,
}: {
  initialDocuments: IngestedDocument[]
}) {
  const [query, setQuery] = useState('')
  const [documentType, setDocumentType] = useState('')
  const [limit, setLimit] = useState('')
  const [filteredDocuments, setFilteredDocuments] = useState<
    IngestedDocument[] | null
  >(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const documents = filteredDocuments ?? initialDocuments

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const filters: DocumentFilters = {
      q: optionalString(query),
      document_type: optionalString(documentType),
      limit: optionalNumber(limit),
    }
    setIsLoading(true)
    setError(null)
    try {
      setFilteredDocuments(await fetchDocuments(filters))
    } catch (caughtError) {
      setError(errorMessage(caughtError, 'Unable to load documents'))
      setFilteredDocuments([])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="browse-shell">
      <header className="browse-header">
        <Link className="text-link" to="/">
          Drivewise MVP
        </Link>
        <div>
          <p className="eyebrow">Document explorer</p>
          <h1>Documenti</h1>
          <p className="summary">
            Consulta i documenti locali ingeriti e le proposte conservative
            salvate nei metadata.
          </p>
        </div>
      </header>

      <section className="browse-layout">
        <form className="filter-panel" onSubmit={handleSubmit}>
          <div className="form-grid">
            <label>
              Ricerca
              <input
                name="q"
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Fiat Panda"
                value={query}
              />
            </label>
            <label>
              Document type
              <input
                name="document_type"
                onChange={(event) => setDocumentType(event.target.value)}
                placeholder="listing_snapshot"
                value={documentType}
              />
            </label>
            <label>
              Limit
              <input
                inputMode="numeric"
                max="100"
                min="1"
                name="limit"
                onChange={(event) => setLimit(event.target.value)}
                placeholder="20"
                type="number"
                value={limit}
              />
            </label>
          </div>
          <button className="primary-button" type="submit">
            Applica filtri
          </button>
        </form>

        <section className="browse-results" aria-live="polite">
          {isLoading ? <p className="status-message">Caricamento…</p> : null}
          {error ? <p className="error-message">{error}</p> : null}
          {!isLoading && !error && documents.length === 0 ? (
            <p className="status-message">Nessun documento trovato.</p>
          ) : null}

          <div className="card-grid">
            {documents.map((document) => (
              <DocumentCard document={document} key={document.id} />
            ))}
          </div>
        </section>
      </section>
    </main>
  )
}

function DocumentCard({ document }: { document: IngestedDocument }) {
  const metadata = document.metadata
  const localPath = metadataValue(metadata, 'local_path')
  const proposedVehicle = objectValue(metadata, 'proposed_vehicle')
  const proposedListing = objectValue(metadata, 'proposed_listing')

  return (
    <article className="data-card">
      <div className="card-heading">
        <h2>{document.title}</h2>
        <p>
          {document.document_type} · {formatDateTime(document.created_at)}
        </p>
      </div>

      <dl className="facts-grid">
        <Fact label="Document type" value={document.document_type} />
        <Fact label="Created at" value={formatDateTime(document.created_at)} />
        {localPath ? <Fact label="Local path" value={localPath} /> : null}
      </dl>

      {Object.keys(proposedVehicle).length > 0 ? (
        <MetadataBlock
          title="Proposed vehicle"
          values={[formatProposedVehicle(proposedVehicle)]}
        />
      ) : null}

      {Object.keys(proposedListing).length > 0 ? (
        <MetadataBlock
          title="Proposed listing"
          values={formatKeyValues(proposedListing)}
        />
      ) : null}

      <Link
        className="text-link"
        params={{ documentId: document.id }}
        to="/documents/$documentId"
      >
        Dettaglio documento
      </Link>
    </article>
  )
}

function MetadataBlock({ title, values }: { title: string; values: string[] }) {
  return (
    <section className="metadata-summary">
      <h3>{title}</h3>
      {values.map((value) => (
        <p key={value}>{value}</p>
      ))}
    </section>
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

function optionalString(value: string) {
  return value.trim() === '' ? undefined : value.trim()
}

function metadataValue(metadata: Record<string, unknown>, key: string) {
  const value = metadata[key]
  return typeof value === 'string' ? value : null
}

function objectValue(metadata: Record<string, unknown>, key: string) {
  const value = metadata[key]
  return isPlainObject(value) ? value : {}
}

function formatProposedVehicle(value: Record<string, unknown>) {
  const make = stringValue(value.make)
  const model = stringValue(value.model)
  const displayName = [make, model].filter(Boolean).join(' ')
  const otherValues = formatKeyValues(value).filter(
    (item) => !item.startsWith('make:') && !item.startsWith('model:'),
  )

  return [displayName, ...otherValues].filter(Boolean).join(' · ')
}

function formatKeyValues(value: Record<string, unknown>) {
  return Object.entries(value).map(([key, item]) => `${key}: ${String(item)}`)
}

function stringValue(value: unknown) {
  return typeof value === 'string' ? value : ''
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function formatDateTime(value: string) {
  return value.replace('T', ' ').replace('Z', ' UTC')
}
