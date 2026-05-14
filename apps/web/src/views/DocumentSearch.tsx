import { FormEvent, useState } from 'react'
import { Link } from '@tanstack/react-router'

import {
  DocumentSearchItem,
  DocumentSearchMode,
  DocumentSearchResponse,
  searchDocuments,
} from '../api/drivewise'
import { errorMessage, optionalNumber } from './viewUtils'

export function DocumentSearchPage() {
  const [query, setQuery] = useState('')
  const [documentType, setDocumentType] = useState('')
  const [limit, setLimit] = useState('10')
  const [includeContent, setIncludeContent] = useState(false)
  const [mode, setMode] = useState<DocumentSearchMode>('text_only')
  const [response, setResponse] = useState<DocumentSearchResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const canSubmit = query.trim() !== '' && !isLoading

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsLoading(true)
    setError(null)
    setResponse(null)

    try {
      const data = await searchDocuments({
        query,
        document_type: optionalString(documentType),
        limit: boundedLimit(limit),
        include_content: includeContent,
        mode,
      })
      setResponse(data)
    } catch (caughtError) {
      setError(errorMessage(caughtError, 'Unable to search documents'))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="browse-shell search-shell">
      <header className="browse-header search-header">
        <Link className="text-link" to="/">
          Drivewise MVP
        </Link>
        <div>
          <p className="eyebrow">Document search</p>
          <h1>Search</h1>
          <p className="summary">
            Ricerca read-only sui documenti ingeriti. Il default usa testo e
            scoring deterministico; la modalità vector_fake è solo dev/test.
          </p>
        </div>
      </header>

      <section className="browse-layout search-layout">
        <form className="filter-panel search-panel" onSubmit={handleSubmit}>
          <div className="form-grid">
            <label>
              Query
              <input
                name="query"
                onChange={(event) => setQuery(event.target.value)}
                placeholder="fiat panda"
                required
                value={query}
              />
            </label>
            <label>
              Search mode
              <select
                name="mode"
                onChange={(event) =>
                  setMode(event.target.value as DocumentSearchMode)
                }
                value={mode}
              >
                <option value="text_only">text_only</option>
                <option value="vector_fake">vector_fake</option>
              </select>
            </label>
            <label>
              Document type
              <input
                name="document_type"
                onChange={(event) => setDocumentType(event.target.value)}
                placeholder="vehicle_profile"
                value={documentType}
              />
            </label>
            <label>
              Limit
              <input
                inputMode="numeric"
                max="50"
                min="1"
                name="limit"
                onChange={(event) => setLimit(event.target.value)}
                type="number"
                value={limit}
              />
            </label>
            <label className="checkbox-option">
              <input
                checked={includeContent}
                name="include_content"
                onChange={(event) => setIncludeContent(event.target.checked)}
                type="checkbox"
              />
              Include content
            </label>
          </div>
          {mode === 'vector_fake' ? (
            <p className="status-message">
              Modalità dev: richiede embedding fake generati localmente.
            </p>
          ) : null}
          <button className="primary-button" disabled={!canSubmit} type="submit">
            {isLoading ? 'Searching...' : 'Search documents'}
          </button>
        </form>

        <section className="browse-results search-results" aria-live="polite">
          {isLoading ? <p className="status-message">Ricerca in corso...</p> : null}
          {error ? <p className="error-message">{error}</p> : null}
          {!isLoading && !error && !response ? (
            <p className="status-message">
              Inserisci una query per interrogare `/search/documents`.
            </p>
          ) : null}
          {response ? (
            <SearchResults
              includeContent={includeContent}
              response={response}
            />
          ) : null}
        </section>
      </section>
    </main>
  )
}

function SearchResults({
  includeContent,
  response,
}: {
  includeContent: boolean
  response: DocumentSearchResponse
}) {
  return (
    <>
      <div className="search-result-heading">
        <p className="eyebrow">mode: {response.mode}</p>
        <h2>Risultati per “{response.query}”</h2>
      </div>

      {response.items.length === 0 ? (
        <p className="status-message">{emptySearchMessage(response.mode)}</p>
      ) : (
        <div className="search-result-list">
          {response.items.map((item) => (
            <SearchResultCard
              includeContent={includeContent}
              item={item}
              key={item.id}
            />
          ))}
        </div>
      )}
    </>
  )
}

function emptySearchMessage(mode: DocumentSearchMode) {
  if (mode === 'vector_fake') {
    return 'Nessun documento con embedding o nessun risultato.'
  }

  return 'Nessun match testuale.'
}

function SearchResultCard({
  includeContent,
  item,
}: {
  includeContent: boolean
  item: DocumentSearchItem
}) {
  return (
    <article className="search-card">
      <div className="result-topline">
        <div>
          <h3>{item.title}</h3>
          <p>{item.document_type}</p>
        </div>
        <strong>Score {item.score}</strong>
      </div>

      <p className="search-snippet">{item.snippet}</p>

      <dl className="facts-grid search-metadata">
        {Object.entries(item.metadata).map(([key, value]) => (
          <div key={key}>
            <dt>{key}</dt>
            <dd>{value ?? 'none'}</dd>
          </div>
        ))}
      </dl>

      {includeContent && item.content ? (
        <pre className="content-block">{item.content}</pre>
      ) : null}
    </article>
  )
}

function optionalString(value: string) {
  return value.trim() === '' ? undefined : value.trim()
}

function boundedLimit(value: string) {
  const parsed = optionalNumber(value) ?? 10
  return Math.min(Math.max(parsed, 1), 50)
}
