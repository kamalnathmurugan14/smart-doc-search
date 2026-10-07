import type { Mode } from "../api/client";

const MODES: Mode[] = ["keyword", "semantic", "hybrid"];

export function ModeToggle({ mode, onChange }: { mode: Mode; onChange: (m: Mode) => void }) {
  return (
    <div className="segmented" role="group" aria-label="Search mode">
      {MODES.map((m) => (
        <button key={m} type="button" aria-pressed={mode === m} onClick={() => onChange(m)}>
          {m}
        </button>
      ))}
    </div>
  );
}
