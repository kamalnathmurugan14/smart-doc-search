import type { Mode, Result } from "../api/client";
import { ScoreBar } from "./ScoreBar";
import { TagChip } from "./TagChip";

const ICON: Record<string, string> = { pdf: "📕", docx: "📘", txt: "📄", md: "📝" };

export function ResultCard({
  r,
  mode,
  onExplain,
}: {
  r: Result;
  mode: Mode;
  onExplain: (r: Result) => void;
}) {
  const ext = r.file.split(".").pop() ?? "";
  return (
    <article className="card result">
      <h3>
        <span aria-hidden>{ICON[ext] ?? "📄"}</span> {r.file}
      </h3>
      <div className="muted">
        {r.rel_path} · page {r.page}
      </div>
      {/* snippet_html is escaped by the backend; only <mark> tags are added */}
      <p className="snippet" dangerouslySetInnerHTML={{ __html: r.snippet_html }} />
      <div className="bars">
        <ScoreBar
          name="keyword"
          value={r.norm.keyword}
          label={r.scores.keyword.toFixed(2)}
          color="var(--bar-kw)"
        />
        <ScoreBar
          name="semantic"
          value={r.norm.semantic}
          label={r.scores.semantic.toFixed(2)}
          color="var(--bar-sem)"
        />
        {mode === "hybrid" && (
          <ScoreBar
            name="hybrid"
            value={r.scores.hybrid}
            label={r.scores.hybrid.toFixed(2)}
            color="var(--bar-hyb)"
          />
        )}
      </div>
      <div className="row">
        {r.tags.map((t) => (
          <TagChip key={t} tag={t} />
        ))}
        <span style={{ flex: 1 }} />
        <button type="button" onClick={() => onExplain(r)}>
          Explain
        </button>
        <button
          type="button"
          onClick={() => navigator.clipboard?.writeText(r.rel_path)}
          title="Copy path to clipboard"
        >
          Copy path
        </button>
      </div>
    </article>
  );
}
