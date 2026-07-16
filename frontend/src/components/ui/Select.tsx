import { useEffect, useRef, useState } from "react";

export interface Option {
  value: string;
  label: string;
  sub?: string;
}

export function Select({
  options,
  value,
  onChange,
  placeholder = "Select…",
  disabled,
  loading,
  searchable = true,
}: {
  options: Option[];
  value: string | null;
  onChange: (v: string) => void;
  placeholder?: string;
  disabled?: boolean;
  loading?: boolean;
  searchable?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);
  useEffect(() => {
    if (!open) setQ("");
  }, [open]);

  const selected = options.find((o) => o.value === value) ?? null;
  const filtered = q
    ? options.filter((o) => (o.label + " " + (o.sub ?? "")).toLowerCase().includes(q.toLowerCase()))
    : options;

  return (
    <div className={"select" + (open ? " select--open" : "")} ref={ref}>
      <button
        type="button"
        className="select__trigger"
        data-placeholder={!selected}
        disabled={disabled || loading}
        onClick={() => setOpen((o) => !o)}
      >
        <span>{loading ? "Loading…" : selected ? selected.label : placeholder}</span>
        <span className="select__chev">▾</span>
      </button>
      {open && !disabled && (
        <div className="select__pop">
          {searchable && (
            <input
              autoFocus
              className="select__search"
              placeholder="Search…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          )}
          <div className="select__list">
            {filtered.length === 0 && <div className="select__empty">No matches</div>}
            {filtered.map((o) => (
              <div
                key={o.value}
                className={"select__opt" + (o.value === value ? " select__opt--selected" : "")}
                onClick={() => {
                  onChange(o.value);
                  setOpen(false);
                }}
              >
                <span className="select__opt-main">{o.label}</span>
                {o.sub && <span className="select__opt-sub">{o.sub}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
