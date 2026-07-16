export function InfoTip({ text }: { text: string }) {
  return (
    <span className="infotip" tabIndex={0} aria-label={text}>
      <span className="infotip__q" aria-hidden>?</span>
      <span className="infotip__pop" role="tooltip">{text}</span>
    </span>
  );
}
