import { useState } from "react";
import { api, type FileRow } from "../api/client";
import { IndexProgress } from "../components/IndexProgress";
import { useAsync } from "../hooks/useAsync";

export function SettingsPage() {
  const health = useAsync(() => api<{ status: string; version: string; embedder: string }>("/health"), []);
  const files = useAsync(() => api<{ files: FileRow[] }>("/files"), []);
  const [retag, setRetag] = useState<string | null>(null);

  return (
    <>
      <h2>Settings &amp; index</h2>
      <IndexProgress onFinished={files.reload} />
      <div className="card">
        <h3>Backend</h3>
        {health.error && (
          <p className="error" role="alert">
            {health.error}
          </p>
        )}
        {health.data && (
          <p>
            status <strong>{health.data.status}</strong> · v{health.data.version} · embedder{" "}
            <code>{health.data.embedder}</code>
          </p>
        )}
        {health.data?.embedder === "hashing" && (
          <p className="muted">
            Using the offline lexical embedder. Install <code>sentence-transformers</code> for true semantic
            search.
          </p>
        )}
        <div className="row">
          <button
            type="button"
            onClick={async () => {
              const r = await api<{ retagged: number }>("/files/retag", { method: "POST" });
              setRetag(`Re-tagged ${r.retagged} files`);
              files.reload();
            }}
          >
            Apply tag rules now
          </button>
          {retag && <span role="status">{retag}</span>}
        </div>
        <p className="muted">
          Edit <code>backend/rules/tags.yaml</code>, then click the button above.
        </p>
      </div>
      <div className="card">
        <h3>Indexed files ({files.data?.files.length ?? 0})</h3>
        {files.loading && <p className="muted">Loading…</p>}
        {files.data && files.data.files.length === 0 && <p className="empty">No files indexed.</p>}
        {files.data && files.data.files.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>file</th>
                <th>status</th>
                <th>tags</th>
              </tr>
            </thead>
            <tbody>
              {files.data.files.map((f) => (
                <tr key={f.rel_path}>
                  <td>{f.rel_path}</td>
                  <td className={f.status === "error" ? "error" : ""} title={f.message ?? ""}>
                    {f.status}
                    {f.message ? ` – ${f.message}` : ""}
                  </td>
                  <td>{f.tags.join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
