import { useState, type FormEvent } from "react";
import type { Mode } from "../api/client";
import { ModeToggle } from "./ModeToggle";

interface Props {
  initial?: string;
  mode: Mode;
  alpha: number;
  onMode: (m: Mode) => void;
  onAlpha: (a: number) => void;
  onSearch: (q: string) => void;
}

export function SearchBar({ initial = "", mode, alpha, onMode, onAlpha, onSearch }: Props) {
  const [q, setQ] = useState(initial);
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (q.trim()) onSearch(q.trim());
  };
  return (
    <form className="searchbar" onSubmit={submit} role="search">
      <label className="sr-only" htmlFor="q">
        Search documents
      </label>
      <input
        id="q"
        type="search"
        placeholder="Search your documents…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      <ModeToggle mode={mode} onChange={onMode} />
      {mode === "hybrid" && (
        <label className="row muted">
          semantic weight
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={alpha}
            onChange={(e) => onAlpha(Number(e.target.value))}
            aria-label="Hybrid alpha"
          />
          <span>{alpha.toFixed(2)}</span>
        </label>
      )}
      <button className="primary" type="submit">
        Search
      </button>
    </form>
  );
}
