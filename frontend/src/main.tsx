import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

type Node = {
  id: number;
  name: string;
  x: number;
  y: number;
  sensing_trust: number;
  communication_trust: number;
  status: string;
  sensing_status: string;
  communication_status: string;
  temperature: number | null;
  humidity: number | null;
  event: boolean;
  reason: string;
  route: number[];
};
type Event = { time: number; node_id: number; kind: string; message: string };
type State = {
  step: number;
  complete: boolean;
  playing: boolean;
  config: {
    nodes: number;
    steps: number;
    scenario: string;
    method: string;
    seed: number;
    fault_start: number;
    fault_end: number;
  };
  nodes: Node[];
  gateway: { x: number; y: number };
  links: number[][];
  metrics: Record<string, number | null>;
  events: Event[];
  history: {
    time: number;
    sensing: Record<number, number>;
    communication: Record<number, number>;
  }[];
};
type Summary = {
  nodes: number;
  scenario: string;
  method: string;
  runs: number;
  metrics: Record<
    string,
    { mean: number | null; std: number | null; ci95: number[] | null }
  >;
};
const scenarios = [
  ["normal", "Normal operation"],
  ["sensor_bias", "Sensor bias"],
  ["noise", "Random noise"],
  ["packet_loss", "Packet loss"],
  ["high_latency", "High latency"],
  ["node_failure", "Node failure"],
  ["intermittent", "Intermittent fault"],
  ["multiple", "Multiple failures"],
  ["environment", "Environmental event"],
];
const colors: Record<string, string> = {
  healthy: "#208267",
  suspicious: "#c68a2e",
  isolated: "#d25355",
  recovering: "#548cbb",
};
const percent = (v: number | null | undefined) =>
  v == null ? "—" : `${(v * 100).toFixed(1)}%`;
const label = (s: string) => s.replaceAll("_", " ");
async function api(path: string, body?: unknown) {
  const r = await fetch(
    "/api" + path,
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  if (!r.ok) {
    const message = await r.text();
    throw new Error(`${r.status}: ${message}`);
  }
  return r.json();
}
function Graph({
  state,
  selected,
  onSelect,
}: {
  state: State;
  selected: number;
  onSelect: (id: number) => void;
}) {
  const all = [{ id: 0, ...state.gateway }, ...state.nodes];
  const maxX = Math.max(...all.map((n) => n.x)),
    maxY = Math.max(...all.map((n) => n.y));
  const pos = (id: number) => {
    const n = all.find((n) => n.id === id)!;
    return {
      x: 48 + ((n.x + 1) / (maxX + 1)) * 580,
      y: 38 + (n.y / Math.max(maxY, 1)) * 292,
    };
  };
  const route = state.nodes.find((n) => n.id === selected)?.route || [];
  return (
    <svg
      className="network"
      viewBox="0 0 680 370"
      role="img"
      aria-label="Network topology. Select a node to inspect trust and route."
    >
      <defs>
        <pattern id="dots" width="18" height="18" patternUnits="userSpaceOnUse">
          <circle cx="1" cy="1" r=".7" fill="#cad4ce" />
        </pattern>
      </defs>
      <rect width="680" height="370" fill="url(#dots)" />
      {state.links.map(([a, b]) => {
        const p = pos(a),
          q = pos(b);
        return (
          <line
            key={`${a}-${b}`}
            x1={p.x}
            y1={p.y}
            x2={q.x}
            y2={q.y}
            stroke="#d5dfd9"
            strokeWidth="1.5"
          />
        );
      })}
      {route.slice(1).map((id, k) => {
        const p = pos(route[k]),
          q = pos(id);
        return (
          <line
            key={id}
            x1={p.x}
            y1={p.y}
            x2={q.x}
            y2={q.y}
            stroke="#208267"
            strokeWidth="3"
            strokeDasharray="5 4"
          />
        );
      })}
      {all.map((n) => {
        const p = pos(n.id),
          data = state.nodes.find((x) => x.id === n.id);
        return (
          <g
            key={n.id}
            transform={`translate(${p.x} ${p.y})`}
            onClick={() => n.id && onSelect(n.id)}
            tabIndex={n.id ? 0 : undefined}
            role={n.id ? "button" : undefined}
            aria-label={
              n.id ? `Inspect N${String(n.id).padStart(2, "0")}` : "Gateway"
            }
            onKeyDown={(e) => {
              if (e.key === "Enter" && n.id) onSelect(n.id);
            }}
            style={{ cursor: n.id ? "pointer" : "default" }}
          >
            {selected === n.id && (
              <circle r="24" fill="none" stroke="#208267" strokeWidth="1" />
            )}
            <circle
              r={n.id ? 14 : 20}
              fill={n.id ? colors[data!.status] : "#193c30"}
              stroke="white"
              strokeWidth="3"
            />
            <text
              textAnchor="middle"
              dy="4"
              fill="white"
              fontSize="10"
              fontWeight="700"
            >
              {n.id || "G"}
            </text>
            <text textAnchor="middle" y="33" fontSize="10" fill="#6f7f76">
              {n.id ? `N${String(n.id).padStart(2, "0")}` : "GATEWAY"}
            </text>
            {data?.event && <circle cx="13" cy="-13" r="5" fill="#b9db62" />}
          </g>
        );
      })}
    </svg>
  );
}
function TrustChart({ state, node }: { state: State; node: number }) {
  const points = (dimension: "sensing" | "communication") =>
    state.history
      .map(
        (h, i) =>
          `${15 + (i / Math.max(state.history.length - 1, 1)) * 310},${110 - (h[dimension][node] || 0) * 90}`,
      )
      .join(" ");
  return (
    <svg
      viewBox="0 0 340 140"
      className="trust-chart"
      role="img"
      aria-label="Sensing and communication trust over simulated time"
    >
      {[0.4, 0.7, 1].map((v) => (
        <g key={v}>
          <line
            x1="15"
            y1={110 - v * 90}
            x2="325"
            y2={110 - v * 90}
            stroke="#dce3de"
            strokeDasharray="3 3"
          />
          <text x="0" y={114 - v * 90} fontSize="8" fill="#87958d">
            {v}
          </text>
        </g>
      ))}
      <polyline
        fill="none"
        stroke="#208267"
        strokeWidth="2.5"
        points={points("sensing")}
      />
      <polyline
        fill="none"
        stroke="#6a94b0"
        strokeWidth="2"
        points={points("communication")}
      />
      <text x="15" y="135" fontSize="9" fill="#87958d">
        0s
      </text>
      <text x="295" y="135" fontSize="9" fill="#87958d">
        {state.step * 2}s
      </text>
    </svg>
  );
}
function App() {
  const [state, setState] = useState<State | null>(null),
    [error, setError] = useState(""),
    [tab, setTab] = useState("Overview"),
    [selected, setSelected] = useState(6),
    [scenario, setScenario] = useState("sensor_bias"),
    [nodes, setNodes] = useState(20),
    [method, setMethod] = useState("adaptive"),
    [seed, setSeed] = useState(1),
    [busy, setBusy] = useState(false),
    [fault, setFault] = useState("sensor_bias");
  const [experiments, setExperiments] = useState<Summary[]>([]),
    [live, setLive] = useState<{ nodes: any[]; limitation: string }>({
      nodes: [],
      limitation: "",
    }),
    [reg, setReg] = useState({ node_id: "N01", x: 0, y: 0 });
  useEffect(() => {
    let active = true;
    const update = async () => {
      try {
        const s = await api("/state");
        if (active) {
          setState(s);
          setError("");
        }
      } catch (e) {
        if (active) setError(String(e));
      }
    };
    void update();
    const timer = setInterval(update, 600);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);
  useEffect(() => {
    if (tab === "Experiments")
      api("/experiments")
        .then(setExperiments)
        .catch((e) => setError(String(e)));
    if (tab === "Live gateway") {
      const refresh = () =>
        api("/live")
          .then(setLive)
          .catch((e) => setError(String(e)));
      void refresh();
      const timer = setInterval(refresh, 2000);
      return () => clearInterval(timer);
    }
  }, [tab]);
  const action = async (path: string, body: unknown = {}) => {
    setBusy(true);
    try {
      await api(path, body);
      setState(await api("/state"));
      setError("");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };
  const selectedNode =
    state?.nodes.find((n) => n.id === selected) || state?.nodes[0];
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon">⠿</span>
          <div>
            adaptive<span>SENSOR NETWORK LAB</span>
          </div>
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {["Overview", "Live gateway", "Experiments", "Methodology"].map(
            (item, i) => (
              <button
                key={item}
                className={tab === item ? "active" : ""}
                onClick={() => setTab(item)}
              >
                <span>{["◈", "⌁", "▥", "≡"][i]}</span>
                {item}
                {tab === item && <i />}
              </button>
            ),
          )}
        </nav>
        <div className="sidebar-bottom">
          <span className="tiny-dot" /> LOCAL RESEARCH BUILD
          <p>
            Observe. Validate.
            <br />
            Recover.
          </p>
          <small>
            Candidate mechanism · v1.0
            <br />
            Simulation results, not field claims.
          </small>
        </div>
      </aside>
      <main>
        <header>
          <div className="crumb">
            WORKSPACE <span>/</span> {tab.toUpperCase()}
          </div>
          <div className="privacy">
            <span className="tiny-dot" />
            Private · local only
          </div>
        </header>
        <div className="page-heading">
          <div>
            <div className="eyebrow">ADAPTIVE TRUST-AWARE IOT</div>
            <h1>
              {tab === "Overview"
                ? "A network built to recover."
                : tab === "Experiments"
                  ? "Evidence, not assumptions."
                  : tab === "Live gateway"
                    ? "From sensor to observer."
                    : "Understand every decision."}
            </h1>
            <p>
              {tab === "Overview"
                ? "Follow sensor health, contextual evidence and routing as the network adapts."
                : tab === "Experiments"
                  ? "Reproducible comparisons across methods, faults and independent seeds."
                  : tab === "Live gateway"
                    ? "Registered devices and validated telemetry from your local gateway."
                    : "A small, explainable mechanism with explicit limitations."}
            </p>
          </div>
          <span className="version">RESEARCH PROTOTYPE</span>
        </div>
        {error && (
          <div className="error" role="alert">
            Connection or request error: {error}
          </div>
        )}
        {tab === "Overview" && state && (
          <>
            <section className="scenario-panel">
              <div>
                <span className="section-kicker">01 / SCENARIO LAB</span>
                <h3>Set the conditions</h3>
              </div>
              <label>
                Scenario
                <select
                  value={scenario}
                  onChange={(e) => setScenario(e.target.value)}
                >
                  {scenarios.map(([v, l]) => (
                    <option key={v} value={v}>
                      {l}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Nodes
                <select
                  value={nodes}
                  onChange={(e) => setNodes(+e.target.value)}
                >
                  {[9, 20, 50, 100].map((n) => (
                    <option key={n}>{n}</option>
                  ))}
                </select>
              </label>
              <label>
                Method
                <select
                  value={method}
                  onChange={(e) => setMethod(e.target.value)}
                >
                  {["adaptive", "static", "conventional"].map((m) => (
                    <option key={m}>{m}</option>
                  ))}
                </select>
              </label>
              <label className="seed">
                Seed
                <input
                  type="number"
                  min="0"
                  value={seed}
                  onChange={(e) => setSeed(+e.target.value)}
                />
              </label>
              <button
                className="primary"
                disabled={busy}
                onClick={() => {
                  setSelected(Math.floor(nodes / 3));
                  void action("/simulation", {
                    nodes,
                    scenario,
                    method,
                    seed,
                    steps: 240,
                  });
                }}
              >
                Reset experiment ↗
              </button>
            </section>
            <div className="metrics">
              {[
                [
                  "Healthy nodes",
                  `${state.nodes.filter((n) => n.status === "healthy").length} / ${state.nodes.length}`,
                  "Currently trusted in both dimensions",
                ],
                [
                  "Packet delivery",
                  percent(state.metrics.pdr),
                  "Delivered / all generated samples",
                ],
                [
                  "Accepted data reliability",
                  percent(state.metrics.data_reliability),
                  "Correct / accepted readings",
                ],
                [
                  "Reliable yield",
                  percent(state.metrics.reliable_yield),
                  "Correct accepted / generated",
                ],
              ].map(([title, value, sub], i) => (
                <section className="metric" key={title}>
                  <span>
                    {title}
                    <b>{["◉", "↗", "✓", "◇"][i]}</b>
                  </span>
                  <strong>{value}</strong>
                  <small>{sub}</small>
                </section>
              ))}
            </div>
            <div className="main-grid">
              <section className="card topology">
                <div className="card-heading">
                  <div>
                    <span className="section-kicker">
                      02 / NETWORK TOPOLOGY
                    </span>
                    <h3>Every connection matters</h3>
                  </div>
                  <span className="badge neutral">
                    {state.config.method} · {state.config.nodes} nodes
                  </span>
                </div>
                <Graph
                  state={state}
                  selected={selectedNode?.id || 1}
                  onSelect={setSelected}
                />
                <div className="graph-footer">
                  <div className="legend">
                    {Object.entries(colors).map(([s, c]) => (
                      <span key={s}>
                        <i style={{ background: c }} />
                        {s}
                      </span>
                    ))}
                  </div>
                  <span>Dashed line: selected route</span>
                </div>
                <div className="playbar">
                  <button
                    className="primary"
                    disabled={busy || state.complete}
                    onClick={() => action(state.playing ? "/pause" : "/play")}
                  >
                    {state.playing ? "Ⅱ Pause" : "▶ Run"}
                  </button>
                  <button
                    className="secondary"
                    disabled={busy || state.playing || state.complete}
                    onClick={() => action("/step")}
                  >
                    Step +2s
                  </button>
                  <div className="progress">
                    <div
                      style={{
                        width: `${(state.step / state.config.steps) * 100}%`,
                      }}
                    />
                  </div>
                  <span>
                    {state.complete
                      ? "Complete"
                      : `${state.step * 2}s / ${state.config.steps * 2}s`}
                  </span>
                </div>
                <div className="run-note">
                  {label(state.config.scenario)} · seed {state.config.seed} ·
                  fault/event window {state.config.fault_start * 2}–
                  {state.config.fault_end * 2}s
                </div>
              </section>
              {selectedNode && (
                <section className="card inspector">
                  <div className="card-heading">
                    <span className="section-kicker">03 / NODE INSPECTOR</span>
                    <span className={`badge ${selectedNode.status}`}>
                      {selectedNode.status}
                    </span>
                  </div>
                  <h2>
                    {selectedNode.name}
                    <small> SENSOR NODE</small>
                  </h2>
                  <div className="readings">
                    <div>
                      <strong>
                        {selectedNode.temperature?.toFixed(1) ?? "—"}
                        <small> °C</small>
                      </strong>
                      <span>Temperature</span>
                    </div>
                    <div>
                      <strong>
                        {selectedNode.humidity?.toFixed(1) ?? "—"}
                        <small> %</small>
                      </strong>
                      <span>Humidity</span>
                    </div>
                  </div>
                  {[
                    ["Sensing trust", selectedNode.sensing_trust, "#208267"],
                    [
                      "Communication trust",
                      selectedNode.communication_trust,
                      "#6a94b0",
                    ],
                  ].map(([l, v, c]) => (
                    <div className="trust-row" key={String(l)}>
                      <span>
                        {l}
                        <b>{Number(v).toFixed(2)}</b>
                      </span>
                      <div>
                        <i
                          style={{
                            width: `${Number(v) * 100}%`,
                            background: String(c),
                          }}
                        />
                      </div>
                    </div>
                  ))}
                  <TrustChart state={state} node={selectedNode.id} />
                  <div className="reason">
                    <span>OBSERVATION</span>
                    <p>{selectedNode.reason}</p>
                  </div>
                  <div className="inject">
                    <label>
                      Manual fault
                      <select
                        value={fault}
                        onChange={(e) => setFault(e.target.value)}
                      >
                        {[
                          "none",
                          "sensor_bias",
                          "noise",
                          "packet_loss",
                          "high_latency",
                          "node_failure",
                          "intermittent",
                        ].map((m) => (
                          <option key={m} value={m}>
                            {label(m)}
                          </option>
                        ))}
                      </select>
                    </label>
                    <button
                      className="secondary"
                      disabled={busy}
                      onClick={() =>
                        action("/faults", {
                          node_id: selectedNode.id,
                          mode: fault,
                        })
                      }
                    >
                      Apply
                    </button>
                  </div>
                  <small className="muted">
                    “None” restores this node. Manual overrides persist until
                    reset.
                  </small>
                </section>
              )}
            </div>
            <div className="bottom-grid">
              <section className="card">
                <div className="card-heading">
                  <div>
                    <span className="section-kicker">04 / NODE REGISTER</span>
                    <h3>Health at a glance</h3>
                  </div>
                  <span className="muted">Select a row to inspect</span>
                </div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Node</th>
                        <th>Sensing</th>
                        <th>Comms</th>
                        <th>Status</th>
                        <th>Route to gateway</th>
                      </tr>
                    </thead>
                    <tbody>
                      {state.nodes.map((n) => (
                        <tr
                          key={n.id}
                          className={
                            selectedNode?.id === n.id ? "selected" : ""
                          }
                          onClick={() => setSelected(n.id)}
                        >
                          <td>
                            <button
                              className="text-button"
                              onClick={() => setSelected(n.id)}
                            >
                              {n.name}
                            </button>
                          </td>
                          <td>{n.sensing_trust.toFixed(2)}</td>
                          <td>{n.communication_trust.toFixed(2)}</td>
                          <td>
                            <span className={`badge ${n.status}`}>
                              {n.status}
                            </span>
                          </td>
                          <td className="route">
                            {n.route.length
                              ? n.route
                                  .map((i) => (i === 0 ? "G" : `N${i}`))
                                  .join(" → ")
                              : "No route"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
              <section className="card timeline">
                <div className="card-heading">
                  <div>
                    <span className="section-kicker">05 / EVENT STREAM</span>
                    <h3>The recovery story</h3>
                  </div>
                  <span className="live-tag">● LIVE</span>
                </div>
                {state.events.length === 0 ? (
                  <div className="empty">
                    No transitions yet.
                    <p>
                      Run a scenario to watch observations become decisions.
                    </p>
                  </div>
                ) : (
                  <ol>
                    {state.events
                      .slice(-25)
                      .reverse()
                      .map((e, i) => (
                        <li key={`${e.time}-${i}`}>
                          <i
                            style={{ background: colors[e.kind] || "#8b9b91" }}
                          />
                          <div>
                            <small>
                              {e.time.toFixed(0)}s · N
                              {String(e.node_id).padStart(2, "0")}
                            </small>
                            <p>{e.message}</p>
                          </div>
                        </li>
                      ))}
                  </ol>
                )}
              </section>
            </div>
          </>
        )}
        {tab === "Experiments" && (
          <section className="card">
            <div className="card-heading">
              <h3>Benchmark results</h3>
              <label>
                Network size
                <select
                  value={nodes}
                  onChange={(e) => setNodes(+e.target.value)}
                >
                  {[20, 50, 100].map((n) => (
                    <option key={n}>{n}</option>
                  ))}
                </select>
              </label>
            </div>
            <p className="inner-note">
              Means from actual simulations. Full standard deviations,
              confidence intervals, paired tests and raw runs are in the local
              results folder.
            </p>
            {!experiments.length ? (
              <div className="empty">No completed benchmark results yet.</div>
            ) : (
              <div className="table-wrap tall">
                <table>
                  <thead>
                    <tr>
                      <th>Scenario</th>
                      <th>Method</th>
                      <th>Runs</th>
                      <th>PDR</th>
                      <th>Data reliability</th>
                      <th>Reliable yield</th>
                      <th>False positives</th>
                    </tr>
                  </thead>
                  <tbody>
                    {experiments
                      .filter((r) => r.nodes === nodes)
                      .map((r) => (
                        <tr key={r.scenario + r.method}>
                          <td>{label(r.scenario)}</td>
                          <td>
                            <span
                              className={`badge ${r.method === "adaptive" ? "healthy" : "neutral"}`}
                            >
                              {r.method}
                            </span>
                          </td>
                          <td>{r.runs}</td>
                          {[
                            "pdr",
                            "data_reliability",
                            "reliable_yield",
                            "fpr",
                          ].map((m) => (
                            <td
                              key={m}
                              title={`95% CI: ${r.metrics[m].ci95?.map(percent).join(" – ") || "unavailable"}`}
                            >
                              {percent(r.metrics[m].mean)}
                            </td>
                          ))}
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}
        {tab === "Live gateway" && (
          <section className="card">
            <div className="card-heading">
              <h3>Registered sensor nodes</h3>
              <span className="badge neutral">
                {live.nodes.length} registered
              </span>
            </div>
            <div className="registration">
              <label>
                Node ID
                <input
                  value={reg.node_id}
                  onChange={(e) => setReg({ ...reg, node_id: e.target.value })}
                />
              </label>
              <label>
                X
                <input
                  type="number"
                  value={reg.x}
                  onChange={(e) => setReg({ ...reg, x: +e.target.value })}
                />
              </label>
              <label>
                Y
                <input
                  type="number"
                  value={reg.y}
                  onChange={(e) => setReg({ ...reg, y: +e.target.value })}
                />
              </label>
              <button
                className="primary"
                onClick={async () => {
                  await action("/nodes", reg);
                  setLive(await api("/live"));
                }}
              >
                Register
              </button>
            </div>
            <p className="inner-note">{live.limitation}</p>
            <table>
              <thead>
                <tr>
                  <th>Node</th>
                  <th>Temperature</th>
                  <th>Humidity</th>
                  <th>Sensing trust</th>
                  <th>Communication trust</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {live.nodes.map((n) => (
                  <tr key={n.node_id}>
                    <td>{n.node_id}</td>
                    <td>{n.telemetry?.temperature ?? "—"}</td>
                    <td>{n.telemetry?.humidity ?? "—"}</td>
                    <td>{n.sensing_trust.toFixed(2)}</td>
                    <td>{n.communication_trust.toFixed(2)}</td>
                    <td>{n.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
        {tab === "Methodology" && (
          <div className="method-grid">
            {[
              [
                "01",
                "Observe independently",
                "Sensing trust evaluates fresh readings against nearby trusted witnesses. Communication trust evaluates on-time diagnostic responses. A sensing fault alone does not disqualify a relay.",
              ],
              [
                "02",
                "Preserve environmental context",
                "Coherent changes supported by two nearby witnesses can remain trusted. Insufficient evidence produces uncertainty. Correlated faults can still resemble genuine events.",
              ],
              [
                "03",
                "Recover with evidence",
                "Suspect and isolated states reflect accumulated evidence. Rejoining requires sustained good observations and a probation period. Monitoring continues on a costed management channel.",
              ],
              [
                "04",
                "Keep evaluation honest",
                "Fault labels and true environmental values belong to the evaluator. Algorithms receive only observations and declared topology. Shared seeds pair exogenous disturbances across methods.",
              ],
              [
                "05",
                "Understand the model",
                "This is a central-controller, discrete-event software model with half-duplex link service, bounded retries and a separate diagnostic channel. It is not a validated radio or security model.",
              ],
              [
                "06",
                "Candidate contribution",
                "The joint policy remains a research hypothesis. Existing work covers trust routing, event validation and recovery. No patentability, novelty or publication guarantee is claimed.",
              ],
            ].map(([n, t, b]) => (
              <section className="card method" key={n}>
                <span className="section-kicker">{n}</span>
                <h3>{t}</h3>
                <p>{b}</p>
              </section>
            ))}
          </div>
        )}
        <footer>
          ADAPTIVE / SELF-HEALING IOT
          <span>Local research workspace · All metrics are simulated</span>
        </footer>
      </main>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
