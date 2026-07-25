/* global React, Icons */

function Bar(data) {
  const max = Math.max(...data.map(d => d.v));
  return (
    <div>
      <div className="bar-chart">
        {data.map((d, i) => (
          <div key={i} className="bar" style={{ height: `${(d.v / max) * 100}%` }} data-label={`${d.label}: $${d.v}K`} />
        ))}
      </div>
      <div className="bar-labels">
        {data.map((d, i) => <div key={i}>{d.label}</div>)}
      </div>
    </div>
  );
}

function ChartBlock({ block }) {
  const I = Icons[block.icon] || Icons.chart;
  return (
    <div className="block">
      <div className="block-head">
        <div className="b-icon"><I size={14} /></div>
        <div className="b-title">{block.title}</div>
        {block.badge && <span className="b-badge">{block.badge}</span>}
      </div>
      <div className="chart-wrap">
        <div className="chart-kpis">
          {block.kpis.map((k, i) => (
            <div key={i} className="kpi">
              <label>{k.label}</label>
              <div>
                <span className="v">{k.value}</span>
                {k.delta && <span className={"d " + (k.deltaDir === "down" ? "neg" : "")}>{k.delta}</span>}
              </div>
            </div>
          ))}
        </div>
        {Bar(block.data)}
      </div>
    </div>
  );
}

function TableBlock({ block }) {
  const I = Icons[block.icon] || Icons.file;
  return (
    <div className="block">
      <div className="block-head">
        <div className="b-icon"><I size={14} /></div>
        <div className="b-title">{block.title}</div>
        {block.sub && <span className="b-sub">{block.sub}</span>}
      </div>
      <div style={{ overflowX: "auto" }}>
        <table className="dt">
          <thead>
            <tr>{block.cols.map((c, i) => <th key={i} className={i >= 2 && i < block.cols.length - 1 ? "num" : ""}>{c}</th>)}</tr>
          </thead>
          <tbody>
            {block.rows.map((row, i) => (
              <tr key={i}>
                {row.map((cell, j) => {
                  const isNum = j >= 2 && j < block.cols.length - 1 && typeof cell === "string" && /[\$\d]/.test(cell);
                  if (Array.isArray(cell)) {
                    return <td key={j}><span className={"pill " + cell[0]}>{cell[1]}</span></td>;
                  }
                  return <td key={j} className={isNum ? "num" : ""}>{cell}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RecordBlock({ block }) {
  const I = Icons[block.icon] || Icons.user;
  return (
    <div className="block">
      <div className="block-head">
        <div className="b-icon"><I size={14} /></div>
        <div className="b-title">{block.title}</div>
      </div>
      <div className="record">
        <div className="record-avatar" style={{ background: block.avatar.color }}>{block.avatar.initials}</div>
        <div className="record-main">
          <div className="record-name">{block.name}</div>
          <div className="record-sub">{block.sub}</div>
          <div className="record-meta">
            {block.meta.map(([k, v], i) => (
              <div key={i}><label>{k}</label><span>{v}</span></div>
            ))}
          </div>
        </div>
      </div>
      {block.actions && (
        <div className="record-actions">
          {block.actions.map((a, i) => (
            <button key={i} className={"ra-btn" + (i === 0 ? " primary" : "")}>
              {i === 0 ? <Icons.externalLink size={12} /> : <Icons.message size={12} />}
              {a}
            </button>
          ))}
          <button className="ra-btn ghost"><Icons.moreH size={12} /></button>
        </div>
      )}
    </div>
  );
}

function ApprovalBlock({ block, onApprove }) {
  const I = Icons[block.icon] || Icons.shield;
  return (
    <div className="block" style={{ borderColor: "color-mix(in oklab, var(--accent) 30%, var(--line))" }}>
      <div className="block-head">
        <div className="b-icon" style={{ background: "var(--warn-soft)", color: "var(--warn)" }}>
          <Icons.shield size={14} />
        </div>
        <div className="b-title">{block.title}</div>
        <span className="b-badge" style={{ background: "var(--warn-soft)", color: "var(--warn)", borderColor: "color-mix(in oklab, var(--warn) 25%, transparent)" }}>Approval required</span>
      </div>
      <div className="approval">
        <div className="approval-msg">{block.message}</div>
        <div className="approval-meta">
          {block.meta.map(([k, v], i) => (
            <div key={i}><label>{k}</label><b>{v}</b></div>
          ))}
        </div>
        <div className="approval-actions">
          <button className="btn primary" onClick={onApprove}><Icons.check size={13} /> Approve & submit</button>
          <button className="btn"><Icons.pencil size={13} /> Edit details</button>
          <button className="btn ghost" style={{ marginLeft: "auto" }}><Icons.x size={13} /> Cancel</button>
        </div>
      </div>
    </div>
  );
}

function ErrorBlock({ block }) {
  return (
    <div className="alert">
      <div className="a-icon"><Icons.alert size={14} /></div>
      <div className="a-body">
        <b>{block.title}</b>
        {block.message}
        {block.actions && (
          <div className="a-actions">
            {block.actions.map((a, i) => (
              <button key={i} className="btn" style={i === 0 ? { background: "var(--accent)", color: "#fff", borderColor: "transparent" } : {}}>
                {a}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ConfirmBlock({ block }) {
  const I = Icons[block.variant === "success" ? "checkCircle" : block.variant === "error" ? "alertCircle" : "info"];
  return (
    <div className={"block"}>
      <div className={"confirm " + (block.variant || "success")}>
        <div className="confirm-icon"><I size={16} /></div>
        <div className="confirm-body">
          <div className="confirm-title">{block.title}</div>
          {block.sub && <div className="confirm-sub">{block.sub}</div>}
        </div>
      </div>
    </div>
  );
}

function DebugBlock({ block }) {
  const [open, setOpen] = React.useState(false);
  return (
    <div className="block">
      <div className="block-head" style={{ cursor: "pointer", userSelect: "none" }} onClick={() => setOpen(!open)}>
        <div className="b-icon"><Icons.zap size={14} /></div>
        <div className="b-title">{block.title || "RAG Execution Details"}</div>
        <span className="b-badge" style={{ background: "var(--bg-sunken)", cursor: "pointer" }}>{open ? "Hide Details" : "Show Details"}</span>
      </div>
      {open && (
        <div style={{ padding: 12, background: "var(--bg-sunken)", fontSize: "0.85rem", fontFamily: "var(--mono)", borderTop: "1px solid var(--line)" }}>
          {block.ragMatches && block.ragMatches.length > 0 && (
            <div style={{ marginBottom: 10 }}>
              <div style={{ fontWeight: 600, marginBottom: 4 }}>Matched RAG Routes:</div>
              {block.ragMatches.map((m, i) => (
                <div key={i} style={{ marginTop: 4, padding: "6px 10px", background: "var(--bg-elev)", borderRadius: 6, border: "1px solid var(--line-2)" }}>
                  <div><strong>Step:</strong> {m.step || "Route"} | <strong>API:</strong> {m.api_name || m.matched_route}</div>
                  {m.confidence_score !== undefined && (
                    <div><strong>Confidence:</strong> {(m.confidence_score * 100).toFixed(1)}%</div>
                  )}
                  {m.executed_url && <div><strong>URL:</strong> <code style={{ color: "var(--accent-ink)" }}>{m.executed_url}</code></div>}
                </div>
              ))}
            </div>
          )}
          {block.plan && (
            <div style={{ marginTop: 8 }}>
              <div style={{ fontWeight: 600, marginBottom: 4 }}>Execution Plan:</div>
              <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", margin: 0, padding: 8, background: "var(--bg-elev)", borderRadius: 6, border: "1px solid var(--line-2)" }}>
                {JSON.stringify(block.plan, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function RichBlock({ block, onApprove }) {
  switch (block.kind) {
    case "chart": return <ChartBlock block={block} />;
    case "table": return <TableBlock block={block} />;
    case "record": return <RecordBlock block={block} />;
    case "approval": return <ApprovalBlock block={block} onApprove={onApprove} />;
    case "error": return <ErrorBlock block={block} />;
    case "confirm": return <ConfirmBlock block={block} />;
    case "debug":
    case "rag": return <DebugBlock block={block} />;
    default: return null;
  }
}

window.RichBlock = RichBlock;

