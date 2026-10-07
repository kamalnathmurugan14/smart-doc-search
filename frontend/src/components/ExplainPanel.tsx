import { api, qs, type Explain, type Result } from "../api/client";
import { useAsync } from "../hooks/useAsync";

interface Props {
  query: string;
  result: Result;
  alpha: number;
  onClose: () => void;
}

export function ExplainPanel({ query, result, alpha, onClose }: Props) {
  const { data, error, loading } = useAsync(
    () => api<Explain>("/explain?" + qs({ q: query, chunk_id: result.chunk_id, alpha })),
    [query, result.chunk_id, alpha],
  );
  return (
    <aside className="drawer" role="dialog" aria-label="Explain result">
      <div className="row">
        <h2 style={{ flex: 1, margin: 0, fontSize: 18 }}>Why this ranked here</h2>
        <button type="button" onClick={onClose} autoFocus>
          Close
        </button>
      </div>
      <p className="muted">{result.rel_path}</p>
      {loading && <p>Loading…</p>}
      {error && <p className="error">{error}</p>}
      {data && (
        <>
          <h3>Keyword (BM25)</h3>
          <table>
            <thead>
              <tr>
                <th>term</th>
                <th className="num">tf</th>
                <th className="num">idf</th>
                <th className="num">contribution</th>
              </tr>
            </thead>
            <tbody>
              {data.keyword.terms.map((t, i) => (
                <tr key={t.term + i}>
                  <td>{t.term}</td>
                  <td className="num">{t.tf}</td>
                  <td className="num">{t.idf}</td>
                  <td className="num">{t.contribution}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <th colSpan={3}>sum</th>
                <th className="num">{data.keyword.sum_of_terms}</th>
              </tr>
            </tfoot>
          </table>
          <h3>Semantic</h3>
          <p>
            cosine similarity: <strong>{data.semantic.cosine}</strong>{" "}
            <span className="muted">({data.semantic.embedder})</span>
          </p>
          <ol>
            {data.semantic.top_matching_sentences.map((s) => (
              <li key={s.sentence}>
                {s.sentence} <span className="muted">({s.cosine})</span>
              </li>
            ))}
          </ol>
          <h3>Hybrid</h3>
          <p className="muted">
            <code>{data.hybrid.formula}</code>
          </p>
          <p>
            {data.hybrid.alpha} × {data.hybrid.normalized_scores.semantic} +{" "}
            {(1 - data.hybrid.alpha).toFixed(2)} × {data.hybrid.normalized_scores.keyword} ={" "}
            <strong>{data.hybrid.final}</strong>
          </p>
        </>
      )}
    </aside>
  );
}
