import { FileExplorer } from "../components/FileExplorer";

export function ExplorerPage() {
  return (
    <>
      <h2>Explorer</h2>
      <p className="muted">
        Files inside your <code>DOCS_ROOT</code>. Uploaded files are saved there; click <em>Re-index</em> in
        Settings to make them searchable.
      </p>
      <FileExplorer />
    </>
  );
}
