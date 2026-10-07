import { useCallback, useEffect, useState } from "react";
import { api, type IndexStatus } from "../api/client";

export function IndexProgress({ onFinished }: { onFinished?: () => void }) {
  const [status, setStatus] = useState<IndexStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setStatus(await api<IndexStatus>("/index/status"));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);
  useEffect(() => {
    void refresh();
  }, [refresh]);

  const running = status?.state === "running";
  useEffect(() => {
    if (!running) return;
    const id = setInterval(async () => {
      const s = await api<IndexStatus>("/index/status").catch(() => null);
      if (!s) return;
      setStatus(s);
      if (s.state === "idle") {
        const l = s.last_run;
        if (l)
          setToast(
            `Indexed ${l.files_indexed}, skipped ${l.files_skipped}, removed ${l.files_removed}` +
              (l.errors.length ? `, ${l.errors.length} error(s)` : ""),
          );
        onFinished?.();
      }
    }, 600);
    return () => clearInterval(id);
  }, [running, onFinished]);

  const start = async (force: boolean) => {
    setToast(null);
    try {
      await api("/index", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ force }),
      });
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div className="card">
      <div className="row">
        <button className="primary" type="button" onClick={() => start(false)} disabled={running}>
          {running ? "Indexing…" : "Re-index"}
        </button>
        <button type="button" onClick={() => start(true)} disabled={running} title="Re-process every file">
          Force full re-index
        </button>
        {status?.last_run && !running && (
          <span className="muted">
            last run: {status.last_run.files_seen} files seen, {status.last_run.files_skipped} unchanged
          </span>
        )}
      </div>
      {running && status && (
        <p>
          <progress
            max={Math.max(status.progress.total, 1)}
            value={status.progress.done}
            aria-label="Indexing progress"
          />
          <span className="muted">
            {status.progress.done} / {status.progress.total} files
          </span>
        </p>
      )}
      {toast && <p role="status">✅ {toast}</p>}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {status?.last_run?.errors.map((e) => (
        <p key={e.rel_path} className="error">
          ⚠ {e.rel_path}: {e.error}
        </p>
      ))}
    </div>
  );
}
