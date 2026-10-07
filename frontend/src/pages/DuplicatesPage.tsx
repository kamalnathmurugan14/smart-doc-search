import { api, type Duplicates } from "../api/client";
import { useAsync } from "../hooks/useAsync";

export function DuplicatesPage() {
  const { data, error, loading, reload } = useAsync(() => api<Duplicates>("/duplicates"), []);
  return (
    <>
      <div className="row">
        <h2 style={{ flex: 1 }}>Duplicates</h2>
        <button type="button" onClick={reload}>
          Refresh
        </button>
      </div>
      {loading && <p className="muted">Loading…</p>}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {data && data.exact.length === 0 && data.near.length === 0 && (
        <p className="empty">No duplicates found 🎉</p>
      )}
      {data && data.exact.length > 0 && (
        <section>
          <h3>
            Exact duplicates <span className="muted">(identical SHA-256)</span>
          </h3>
          {data.exact.map((g) => (
            <div className="card" key={g.join("|")}>
              <ul>
                {g.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            </div>
          ))}
        </section>
      )}
      {data && data.near.length > 0 && (
        <section>
          <h3>
            Near duplicates <span className="muted">(similar embeddings, confirmed by shingle overlap)</span>
          </h3>
          {data.near.map((g) => (
            <div className="card" key={g.files.join("|")}>
              <span className="chip">similarity {g.similarity}</span>
              <ul>
                {g.files.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            </div>
          ))}
        </section>
      )}
    </>
  );
}
