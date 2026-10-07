import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, qs, type FileRow, type Mode, type Result, type SearchResponse } from "../api/client";
import { ExplainPanel } from "../components/ExplainPanel";
import { ResultCard } from "../components/ResultCard";
import { SearchBar } from "../components/SearchBar";
import { TagChip } from "../components/TagChip";

export function SearchPage() {
  const [mode, setMode] = useState<Mode>("hybrid");
  const [alpha, setAlpha] = useState(0.5);
  const [query, setQuery] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [allTags, setAllTags] = useState<string[]>([]);
  const [indexed, setIndexed] = useState<boolean | null>(null);
  const [resp, setResp] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [explain, setExplain] = useState<Result | null>(null);

  useEffect(() => {
    api<{ files: FileRow[]; all_tags: string[] }>("/files")
      .then((r) => {
        setIndexed(r.files.length > 0);
        setAllTags(r.all_tags);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  // Re-run the search whenever the query, mode, alpha or tag filter changes.
  useEffect(() => {
    if (!query) return;
    let alive = true;
    setLoading(true);
    api<SearchResponse>(
      "/search?" + qs({ q: query, mode, alpha: mode === "hybrid" ? alpha : undefined, tags: tags.join(",") }),
    )
      .then((r) => alive && (setResp(r), setError(null)))
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [query, mode, alpha, tags]);

  return (
    <>
      <h2>Search</h2>
      {indexed === false && (
        <div className="card">
          <h3>Welcome 👋</h3>
          <p>
            Nothing is indexed yet. Choose your folder in <code>backend/.env</code> (<code>DOCS_ROOT</code>),
            then click <strong>Re-index</strong> on the <Link to="/settings">Settings</Link> page — or drop
            files in the <Link to="/explorer">Explorer</Link>.
          </p>
        </div>
      )}
      <SearchBar mode={mode} alpha={alpha} onMode={setMode} onAlpha={setAlpha} onSearch={setQuery} />
      {allTags.length > 0 && (
        <div className="row" style={{ marginBottom: 12 }} aria-label="Tag filters">
          <span className="muted">Tags:</span>
          {allTags.map((t) => (
            <TagChip
              key={t}
              tag={t}
              active={tags.includes(t)}
              onClick={() => setTags((c) => (c.includes(t) ? c.filter((x) => x !== t) : [...c, t]))}
            />
          ))}
        </div>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {loading && <p className="muted">Searching…</p>}
      {!loading && resp && resp.results.length === 0 && (
        <p className="empty">
          No results for “{resp.query}” in {resp.mode} mode. Try another mode.
        </p>
      )}
      {resp?.results.map((r) => (
        <ResultCard key={r.chunk_id} r={r} mode={resp.mode} onExplain={setExplain} />
      ))}
      {explain && (
        <ExplainPanel query={query} result={explain} alpha={alpha} onClose={() => setExplain(null)} />
      )}
    </>
  );
}
