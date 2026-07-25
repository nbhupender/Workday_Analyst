/* global React, ReactDOM, Icons, Sidebar, TopBar, ChatArea, TweaksPanel */
const { useState, useEffect } = React;

const TWEAK_DEFAULTS = {
  "theme": "light",
  "collapsed": false,
  "accentName": "Indigo",
  "accentH": 232,
  "accentS": 72
};

function ApprovalModal({ open, onClose, onConfirm }) {
  if (!open) return null;
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-head">
          <div className="m-ic"><Icons.shield size={18} /></div>
          <div>
            <h3>Confirm Workday Action</h3>
            <p>Review the action before submitting to Workday.</p>
          </div>
        </div>
        <div className="modal-foot">
          <button className="btn ghost" onClick={onClose}>Cancel</button>
          <button className="btn primary" onClick={onConfirm}><Icons.check size={13} /> Approve & submit</button>
        </div>
      </div>
    </div>
  );
}

const ENABLE_WORKER_RECORD_CARD = false;

function buildDynamicBlocks(data) {
  const blocks = [];

  // 1. Confirm banner
  if (data.rag_matches && data.rag_matches.length > 0) {
    const top = data.rag_matches[0];
    blocks.push({
      kind: "confirm",
      variant: "success",
      title: "Executed via Workday RAG Router",
      sub: `${data.rag_matches.length} API route(s) matched · ${(top.confidence_score ? top.confidence_score * 100 : 90).toFixed(0)}% confidence`
    });
  }

  // 2. Unified Dynamic Table or Record block from raw_context
  if (data.raw_context) {
    let collectionItems = null;
    let collectionTotal = null;
    const mergedRecord = {};

    for (const stepKey in data.raw_context) {
      const stepRes = data.raw_context[stepKey];
      if (!stepRes) continue;

      const stepItems = [];

      if (stepRes.extracted) {
        if (Array.isArray(stepRes.extracted.items)) {
          stepItems.push(...stepRes.extracted.items);
          collectionTotal = stepRes.extracted.total_records_in_workday || stepRes.extracted.count;
        } else if (Array.isArray(stepRes.extracted.data)) {
          stepItems.push(...stepRes.extracted.data);
          collectionTotal = stepRes.extracted.total || stepRes.extracted.data.length;
        } else if (typeof stepRes.extracted === "object" && Object.keys(stepRes.extracted).length > 0) {
          stepItems.push(stepRes.extracted);
        }
      }

      if (stepItems.length === 0 && stepRes.raw_response) {
        try {
          const rawParsed = JSON.parse(stepRes.raw_response);
          if (rawParsed) {
            if (Array.isArray(rawParsed.data)) {
              stepItems.push(...rawParsed.data);
              collectionTotal = collectionTotal || rawParsed.total || rawParsed.data.length;
            } else if (Array.isArray(rawParsed)) {
              stepItems.push(...rawParsed);
            } else if (typeof rawParsed === "object" && Object.keys(rawParsed).length > 0) {
              stepItems.push(rawParsed);
            }
          }
        } catch (e) { }
      }

      if (stepItems.length > 1) {
        collectionItems = stepItems;
      } else {
        for (const item of stepItems) {
          if (!item || typeof item !== "object") continue;
          for (const [k, v] of Object.entries(item)) {
            if (v !== undefined && v !== null && k !== "href") {
              const valStr = typeof v === "object" ? (v.descriptor || v.name || JSON.stringify(v)) : String(v);
              if (k === "descriptor" || k === "name" || k === "worker_name") {
                mergedRecord.descriptor = valStr;
              } else if (!mergedRecord[k] || /^[0-9a-f]{32}$/i.test(mergedRecord[k])) {
                mergedRecord[k] = valStr;
              }
            }
          }
        }
      }
    }

    if (collectionItems && collectionItems.length > 1) {
      // Table block for collections
      const firstItem = collectionItems[0];
      const rawCols = Object.keys(firstItem).filter(k => k !== "href" && typeof firstItem[k] !== "object").slice(0, 5);
      const cols = rawCols.map(c => c.charAt(0).toUpperCase() + c.slice(1).replace(/([A-Z])/g, ' $1'));
      const rows = collectionItems.map(item => rawCols.map(c => {
        const val = item[c];
        if (c.toLowerCase() === "status" || c.toLowerCase() === "ismanager") {
          return val ? ["good", "Yes / Active"] : ["warn", "No / Standard"];
        }
        return val !== undefined && val !== null ? String(val) : "—";
      }));

      blocks.push({
        kind: "table",
        title: "Workday Records Table",
        sub: `${collectionItems.length} records loaded${collectionTotal ? ` (of ${collectionTotal} total in Workday)` : ""}`,
        icon: "file",
        cols,
        rows
      });
    } else if (ENABLE_WORKER_RECORD_CARD && Object.keys(mergedRecord).length > 0) {
      // Single unified Record Block (Disabled)
      let rawName = mergedRecord.descriptor || mergedRecord.name || mergedRecord.worker_name;
      if (!rawName || /^[0-9a-f]{32}$/i.test(rawName)) {
        if (data.query) {
          const qMatch = data.query.match(/(?:of|for|about|who is|is)\s+([A-Z][a-zA-Z\s]+?)(?:\?|$|\s+job|\s+title|\s+manager|\s+email)/i);
          if (qMatch && qMatch[1]) {
            rawName = qMatch[1].trim();
          }
        }
      }
      const name = rawName ? (rawName.charAt(0).toUpperCase() + rawName.slice(1)) : "Worker Record";
      const sub = mergedRecord.businessTitle || mergedRecord.job_title || mergedRecord.title || mergedRecord.type || "Workday Worker";
      const initials = name.split(" ").filter(Boolean).map(w => w[0]).join("").slice(0, 2).toUpperCase();

      const isCompQuery = data.query && /\b(salary|pay|compensation|allowance|earning|wage|bonus)\b/i.test(data.query);

      const meta = Object.entries(mergedRecord)
        .filter(([k]) => {
          if (k === "href" || k === "id" || k === "descriptor" || k === "name" || k === "businessTitle" || k === "job_title" || k === "title") return false;
          if (!isCompQuery && (k.includes("pay") || k.includes("salary") || k.includes("compensation") || k.includes("basis"))) return false;
          return true;
        })
        .slice(0, 6)
        .map(([k, v]) => [k.replace(/([A-Z])/g, ' $1').toLowerCase(), typeof v === "object" ? (v?.descriptor || JSON.stringify(v)) : String(v)]);

      let blockTitle = "Worker Record";
      if (mergedRecord.cost_center) blockTitle = "Cost Center Detail";
      else if (mergedRecord.company) blockTitle = "Company Detail";
      else if (mergedRecord.job_title) blockTitle = "Job Title Detail";
      else if (mergedRecord.total_base_pay || mergedRecord.total_salary_and_allowances) blockTitle = "Compensation Detail";

      blocks.push({
        kind: "record",
        title: blockTitle,
        name,
        sub,
        avatar: { initials: initials || "WD", color: "var(--accent)" },
        meta,
        actions: ["View Profile", "Send Message"]
      });
    }
  }


  // 3. RAG Debug block
  if (data.raw_context && data.rag_matches && data.rag_matches.length > 0) {
    blocks.push({
      kind: "debug",
      title: "RAG & Execution Plan Details",
      ragMatches: data.rag_matches,
      plan: data.plan
    });
  }

  return blocks;
}

function App() {
  const [theme, setThemeState] = useState(TWEAK_DEFAULTS.theme);
  const [collapsed, setCollapsedState] = useState(TWEAK_DEFAULTS.collapsed);
  const [accent, setAccentState] = useState({
    name: TWEAK_DEFAULTS.accentName,
    h: TWEAK_DEFAULTS.accentH,
    s: TWEAK_DEFAULTS.accentS,
  });
  const [tweaksOpen, setTweaksOpen] = useState(false);

  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState("new-chat");
  const [query, setQuery] = useState("");
  const [composerValue, setComposerValue] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamStep, setStreamStep] = useState("Thinking…");
  const [approvalOpen, setApprovalOpen] = useState(false);
  const [userProfile, setUserProfile] = useState({
    name: "Logan McNeil",
    first_name: "Logan",
    title: "Vice President, Human Resources",
    initials: "LM"
  });

  // Apply theme + accent
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    const root = document.documentElement;
    root.style.setProperty("--accent-h", accent.h);
    root.style.setProperty("--accent-s", accent.s + "%");
  }, [theme, accent]);

  // Fetch current user profile dynamically
  useEffect(() => {
    fetch("/me")
      .then(res => res.json())
      .then(data => {
        if (data && data.name) {
          setUserProfile(data);
        }
      })
      .catch(err => console.log("Could not fetch user profile:", err));
  }, []);

  // Load history from FastAPI backend & group into sessions
  const loadHistory = async () => {
    try {
      const resp = await fetch("/api/history");
      if (!resp.ok) return;
      const logs = await resp.json();
      if (!Array.isArray(logs) || logs.length === 0) return;

      // Group logs into sessions based on timestamp gaps (> 15 mins = new session)
      const chronLogs = [...logs].reverse();
      const sessions = [];
      let currentSession = null;

      for (const log of chronLogs) {
        const time = log.timestamp || 0;
        if (!currentSession || (time - currentSession.lastTime > 900)) {
          const dateStr = time ? new Date(time * 1000).toLocaleDateString([], { month: "short", day: "numeric" }) : "Today";
          currentSession = {
            id: "session-" + (sessions.length + 1),
            title: log.query.length > 35 ? log.query.slice(0, 35) + "…" : log.query,
            group: dateStr,
            lastTime: time,
            lastUpdated: time ? new Date(time * 1000).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) : "now",
            messages: []
          };
          sessions.unshift(currentSession);
        }

        const timeStr = time ? new Date(time * 1000).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) : "now";
        const blocks = buildDynamicBlocks(log);
        let textContent = typeof log.answer === "string" ? log.answer : (log.answer ? JSON.stringify(log.answer, null, 2) : "");

        currentSession.messages.push(
          { role: "user", text: log.query, time: timeStr },
          { role: "bot", text: textContent, time: timeStr, blocks }
        );
        currentSession.lastTime = time;
      }

      if (sessions.length > 0) {
        setConversations(sessions);
        setActiveId(prev => (prev === "new-chat" || !sessions.some(s => s.id === prev) ? sessions[0].id : prev));
      }
    } catch (err) {
      console.error("Failed to load history:", err);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const setTheme = (t) => setThemeState(t);
  const setCollapsed = (c) => setCollapsedState(c);
  const setAccent = (a) => setAccentState(a);

  const active = conversations.find(c => c.id === activeId);

  const handleNew = () => {
    const id = "new-" + Date.now();
    const convo = { id, title: "New chat", group: "Today", lastUpdated: "now", messages: [] };
    setConversations(prev => [convo, ...prev]);
    setActiveId(id);
    setComposerValue("");
  };

  const handleSend = async (text) => {
    const now = new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    let currentId = activeId;

    let targetConvo = conversations.find(c => c.id === currentId);
    if (!targetConvo) {
      currentId = "chat-" + Date.now();
      targetConvo = { id: currentId, title: text.length > 35 ? text.slice(0, 35) + "…" : text, group: "Today", lastUpdated: "now", messages: [] };
      setConversations(prev => [targetConvo, ...prev]);
      setActiveId(currentId);
    }

    // Capture history prior to adding the new user message
    const historyPayload = (targetConvo.messages || []).map(m => ({
      role: m.role === "user" ? "user" : "assistant",
      content: m.text || ""
    }));

    // Add user message to active conversation
    setConversations(prev => prev.map(c => {
      if (c.id !== currentId) return c;
      const messages = [...(c.messages || []), { role: "user", text, time: now }];
      const title = (c.title === "New chat" || !c.title) ? (text.length > 35 ? text.slice(0, 35) + "…" : text) : c.title;
      return { ...c, title, messages, lastUpdated: "now" };
    }));

    setStreaming(true);
    const steps = ["Analyzing query intent...", "Querying Workday RAG Router...", "Executing API requests...", "Synthesizing response..."];
    let stepIdx = 0;
    setStreamStep(steps[0]);
    const stepTimer = setInterval(() => {
      stepIdx = (stepIdx + 1) % steps.length;
      setStreamStep(steps[stepIdx]);
    }, 1200);

    try {
      const resp = await fetch("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: text,
          history: historyPayload,
          debug: true
        })
      });
      clearInterval(stepTimer);
      setStreaming(false);

      if (!resp.ok) {
        const errBody = await resp.json().catch(() => ({}));
        throw new Error(errBody.detail || `Server error (HTTP ${resp.status})`);
      }

      const data = await resp.json();
      let textContent = "";
      if (typeof data.answer === "string") {
        textContent = data.answer;
      } else if (data.answer) {
        textContent = JSON.stringify(data.answer, null, 2);
      }

      const blocks = buildDynamicBlocks(data);

      // Add bot response to active conversation
      setConversations(prev => prev.map(c => {
        if (c.id !== currentId) return c;
        return {
          ...c,
          messages: [...c.messages, {
            role: "bot",
            time: new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }),
            text: textContent,
            blocks: blocks
          }]
        };
      }));

    } catch (err) {
      clearInterval(stepTimer);
      setStreaming(false);
      setConversations(prev => prev.map(c => {
        if (c.id !== currentId) return c;
        return {
          ...c,
          messages: [...c.messages, {
            role: "bot",
            time: new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }),
            text: "Error processing your request.",
            blocks: [{ kind: "error", title: "Execution Error", message: err.message }]
          }]
        };
      }));
    }
  };

  const handleStop = () => setStreaming(false);
  const handleApprove = () => setApprovalOpen(true);
  const handleConfirmApproval = () => setApprovalOpen(false);

  return (
    <div className="app" data-collapsed={collapsed}>
      <Sidebar
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed(!collapsed)}
        conversations={conversations}
        activeId={activeId}
        onSelect={setActiveId}
        onNew={handleNew}
        query={query}
        onQuery={setQuery}
        userProfile={userProfile}
      />
      <div className="main">
        <TopBar convo={active} onOpenTweaks={() => setTweaksOpen(true)} />
        <ChatArea
          convo={active}
          streaming={streaming}
          streamStep={streamStep}
          onSend={handleSend}
          onStop={handleStop}
          onApprove={handleApprove}
          composerValue={composerValue}
          setComposerValue={setComposerValue}
          onQuickPick={(t) => { setComposerValue(t); }}
          userProfile={userProfile}
        />
      </div>
      <TweaksPanel
        open={tweaksOpen}
        onClose={() => setTweaksOpen(false)}
        theme={theme} setTheme={setTheme}
        collapsed={collapsed} setCollapsed={setCollapsed}
        accent={accent} setAccent={setAccent}
      />
      <ApprovalModal open={approvalOpen} onClose={() => setApprovalOpen(false)} onConfirm={handleConfirmApproval} />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
