import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Result } from "../api/client";
import { FileExplorer } from "./FileExplorer";
import { ModeToggle } from "./ModeToggle";
import { ResultCard } from "./ResultCard";
import { ScoreBar } from "./ScoreBar";

const result: Result = {
  file: "invoice.pdf",
  rel_path: "billing/invoice.pdf",
  page: 2,
  snippet_html: "Total <mark>due</mark> now",
  scores: { keyword: 3.2, semantic: 0.41, hybrid: 0.9 },
  norm: { keyword: 1, semantic: 0.5 },
  tags: ["Invoice"],
  chunk_id: 7,
};

const json = (body: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status }));
afterEach(() => vi.restoreAllMocks());

describe("ResultCard", () => {
  it("shows snippet highlight, tags, and fires explain", async () => {
    const onExplain = vi.fn();
    render(<ResultCard r={result} mode="hybrid" onExplain={onExplain} />);
    expect(screen.getByText("due").tagName).toBe("MARK");
    expect(screen.getByText("Invoice")).toBeInTheDocument();
    expect(screen.getAllByRole("meter")).toHaveLength(3);
    await userEvent.click(screen.getByRole("button", { name: "Explain" }));
    expect(onExplain).toHaveBeenCalledWith(result);
  });
  it("hides the hybrid bar in keyword mode", () => {
    render(<ResultCard r={result} mode="keyword" onExplain={() => {}} />);
    expect(screen.getAllByRole("meter")).toHaveLength(2);
  });
});

describe("ModeToggle / ScoreBar", () => {
  it("marks the active mode and reports changes", async () => {
    const onChange = vi.fn();
    render(<ModeToggle mode="keyword" onChange={onChange} />);
    expect(screen.getByRole("button", { name: "keyword" })).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(screen.getByRole("button", { name: "semantic" }));
    expect(onChange).toHaveBeenCalledWith("semantic");
  });
  it("clamps bar value", () => {
    render(<ScoreBar name="x" value={5} label="5" color="red" />);
    expect(screen.getByRole("meter")).toHaveAttribute("aria-valuenow", "100");
  });
});

describe("FileExplorer", () => {
  const tree = {
    path: "",
    entries: [
      { name: "sub", type: "dir", size: 0, modified: "2026-01-01T00:00:00+00:00", path: "sub" },
      { name: "a.txt", type: "file", size: 2048, modified: "2026-01-01T00:00:00+00:00", path: "a.txt" },
    ],
  };

  it("lists entries, supports checkbox selection", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => json(tree));
    const onSel = vi.fn();
    render(<FileExplorer selectable selected={[]} onSelectionChange={onSel} />);
    expect(await screen.findByText("a.txt")).toBeInTheDocument();
    expect(screen.getByText(/2.0 KB/)).toBeInTheDocument();
    await userEvent.click(screen.getByLabelText("Select a.txt"));
    expect(onSel).toHaveBeenCalledWith(["a.txt"]);
  });

  it("shows an error state and an empty state", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      json({ error: { code: "NOT_FOUND", message: "Folder not found" } }, 404),
    );
    render(<FileExplorer />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Folder not found");
    vi.restoreAllMocks();
    vi.spyOn(globalThis, "fetch").mockImplementation(() => json({ path: "", entries: [] }));
    await userEvent.click(screen.getByRole("button", { name: /refresh/i }));
    await waitFor(() => expect(screen.getByText(/no supported files/i)).toBeInTheDocument());
  });

  it("navigates into a folder via the tree endpoint", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(() => json(tree));
    render(<FileExplorer />);
    await userEvent.click(await screen.findByRole("button", { name: "sub" }));
    await waitFor(() => expect(spy.mock.calls.some((c) => String(c[0]).includes("path=sub"))).toBe(true));
  });
});
