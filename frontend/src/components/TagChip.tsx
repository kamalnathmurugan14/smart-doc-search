export function TagChip({ tag, active, onClick }: { tag: string; active?: boolean; onClick?: () => void }) {
  if (!onClick) return <span className="chip">{tag}</span>;
  return (
    <button
      type="button"
      className={`chip${active ? " active" : ""}`}
      aria-pressed={!!active}
      onClick={onClick}
    >
      {tag}
    </button>
  );
}
