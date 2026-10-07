// Tiny typed fetch wrapper. Every backend error has the shape { error: { code, message } }.
export const API_URL: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new ApiError("NETWORK", "Cannot reach the backend. Is it running on " + API_URL + "?", 0);
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(
      body?.error?.code ?? "HTTP_" + res.status,
      body?.error?.message ?? res.statusText,
      res.status,
    );
  }
  return body as T;
}

export const qs = (params: Record<string, string | number | undefined>) =>
  new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== "")
      .map(([k, v]) => [k, String(v)]),
  ).toString();

// ---- types -------------------------------------------------------------
export type Mode = "keyword" | "semantic" | "hybrid";
export interface Entry {
  name: string;
  type: "dir" | "file";
  size: number;
  modified: string;
  path: string;
}
export interface Tree {
  path: string;
  entries: Entry[];
}
export interface Scores {
  keyword: number;
  semantic: number;
  hybrid: number;
}
export interface Result {
  file: string;
  rel_path: string;
  page: number;
  snippet_html: string;
  scores: Scores;
  norm: { keyword: number; semantic: number };
  tags: string[];
  chunk_id: number;
}
export interface SearchResponse {
  query: string;
  mode: Mode;
  results: Result[];
}
export interface IndexStatus {
  state: "idle" | "running";
  progress: { done: number; total: number };
  last_run: null | {
    files_seen: number;
    files_indexed: number;
    files_skipped: number;
    files_removed: number;
    errors: { rel_path: string; error: string }[];
  };
}
export interface Explain {
  keyword: {
    terms: { term: string; tf: number; idf: number; contribution: number }[];
    score: number;
    sum_of_terms: number;
  };
  semantic: {
    cosine: number;
    embedder: string;
    top_matching_sentences: { sentence: string; cosine: number }[];
  };
  hybrid: {
    formula: string;
    alpha: number;
    normalized_scores: { keyword: number; semantic: number };
    final: number;
  };
}
export interface Duplicates {
  exact: string[][];
  near: { files: string[]; similarity: number }[];
}
export interface FileRow {
  rel_path: string;
  ext: string;
  size_bytes: number;
  tags: string[];
  status: string;
  message: string | null;
}
