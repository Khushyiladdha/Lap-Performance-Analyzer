export function CheckRow({ ok, name, detail }: { ok: boolean; name: string; detail?: string }) {
  return (
    <div className="checkrow">
      <span className={"checkrow__icon " + (ok ? "checkrow__icon--ok" : "checkrow__icon--bad")}>
        {ok ? "✓" : "!"}
      </span>
      <span className="checkrow__name">{name}</span>
      {detail && <span className="checkrow__detail">{detail}</span>}
    </div>
  );
}
