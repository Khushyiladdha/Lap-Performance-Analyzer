import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHead,
  CheckRow,
  InfoTip,
  Legend,
  Select,
  Stat,
  Stepper,
  Tabs,
} from "./components/ui";

const DRIVERS = [
  { value: "LEC", label: "Charles Leclerc", sub: "Ferrari" },
  { value: "VER", label: "Max Verstappen", sub: "Red Bull Racing" },
  { value: "SAI", label: "Carlos Sainz", sub: "Ferrari" },
  { value: "HAM", label: "Lewis Hamilton", sub: "Mercedes" },
];

export function DesignSystemPreview() {
  const [tab, setTab] = useState("overview");
  const [driver, setDriver] = useState<string | null>("LEC");

  return (
    <div style={{ maxWidth: 980, margin: "0 auto", padding: 40, display: "flex", flexDirection: "column", gap: 34 }}>
      <div>
        <div className="t-hero">Design System v2</div>
        <p className="t-body" style={{ marginTop: 10 }}>
          Elevated slate, brighter and larger type, thermal colour kept as a labeled semantic. The
          primitives below are the building blocks of the guided wizard.
        </p>
      </div>

      <Stepper steps={["Welcome", "Choose Data", "Configure", "Run", "Results"]} current={2} />

      <section style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <Button variant="primary">Run Analysis</Button>
        <Button variant="secondary">Import CSV</Button>
        <Button variant="ghost">Back</Button>
        <Button variant="primary" disabled>Disabled</Button>
      </section>

      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))", gap: 16 }}>
        <Card className="card--pad"><Stat label="Gap" value="+0.814s" tone="loss" sub="vs fastest lap" info="Total time difference over the lap." /></Card>
        <Card className="card--pad"><Stat label="Biggest loss" value="Turn 11" sub="+0.219s" /></Card>
        <Card className="card--pad"><Stat label="Time gained" value="−0.065s" tone="gain" sub="Turn 4" info="Where the analysed lap was actually faster." /></Card>
        <Card className="card--pad"><Stat label="Confidence" value="High" sub="signals agree" /></Card>
      </section>

      <section style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
        <Badge tone="accent">◈ Self-recorded</Badge>
        <Badge tone="loss">Lockup</Badge>
        <Badge tone="gain">Wheelspin</Badge>
        <Badge tone="ok">Reconciled ±0.10s</Badge>
        <Badge>Formula 1</Badge>
      </section>

      <Card>
        <CardHead>
          <span className="t-h3">Searchable dropdown & tabs</span>
          <span className="t-label">reused for driver / event pickers</span>
        </CardHead>
        <CardBody>
          <div style={{ maxWidth: 320, marginBottom: 20 }}>
            <div className="t-label" style={{ marginBottom: 8, display: "flex", gap: 6 }}>
              Driver <InfoTip text="Pick any driver in the session — full names, searchable." />
            </div>
            <Select options={DRIVERS} value={driver} onChange={setDriver} placeholder="Choose a driver" />
          </div>
          <Tabs
            tabs={[
              { id: "overview", label: "Overview" },
              { id: "corners", label: "Corner Analysis" },
              { id: "track", label: "Track View" },
              { id: "telemetry", label: "Telemetry" },
              { id: "validation", label: "Validation" },
            ]}
            active={tab}
            onChange={setTab}
          />
          <p className="t-sm" style={{ marginTop: 16 }}>Active tab: <b style={{ color: "var(--text)" }}>{tab}</b></p>
        </CardBody>
      </Card>

      <Card className="card--pad">
        <div className="t-h3" style={{ marginBottom: 14 }}>Data-quality checks</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <CheckRow ok name="Track closes into a loop" detail="0.07% of track" />
          <CheckRow ok name="Braking + acceleration zones" detail="both present" />
          <CheckRow ok={false} name="Position (X/Y) present" detail="no GPS data" />
        </div>
        <div style={{ marginTop: 18 }}><Legend /></div>
      </Card>
    </div>
  );
}
