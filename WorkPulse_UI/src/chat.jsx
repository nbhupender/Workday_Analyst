/* global React, Icons, RichBlock */
const { useRef: useChatRef, useEffect: useChatEffect } = React;

function TopBar({ convo, onOpenTweaks }) {
  return (
    <div className="topbar">
      <div className="topbar-title">
        <span className="crumb">Chats</span>
        <span className="sep">/</span>
        <span className="cur">{convo ? convo.title : "New chat"}</span>
      </div>
      <div className="topbar-status">
        <span className="dot" />
        Connected to Workday · Production
      </div>
      <div className="topbar-actions">
        <button className="tb-btn"><Icons.star size={14} /></button>
        <button className="tb-btn"><Icons.copy size={14} /> Share</button>
        <button className="tb-btn bordered" onClick={onOpenTweaks}>
          <Icons.palette size={14} /> Tweaks
        </button>
      </div>
    </div>
  );
}

function UserMsg({ m, userProfile }) {
  const initials = (userProfile && userProfile.initials) ? userProfile.initials : "LM";
  return (
    <div className="msg user-msg">
      <div className="msg-avatar user">{initials}</div>
      <div className="msg-body">
        <div className="msg-head"><b>You</b><span className="time">{m.time}</span></div>
        <div className="msg-text">{m.text}</div>
      </div>
    </div>
  );
}

function BotMsg({ m, onApprove }) {
  // Render formatted markdown text (bold, inline code, newlines)
  const renderText = (t) => {
    if (!t) return null;
    const lines = t.split("\n");
    return lines.map((line, lIdx) => {
      const parts = line.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
      const renderedParts = parts.map((p, pIdx) => {
        if (/^\*\*.+\*\*$/.test(p)) {
          return <strong key={pIdx}>{p.slice(2, -2)}</strong>;
        }
        if (/^`[^`]+`$/.test(p)) {
          return <code key={pIdx} style={{ background: "var(--bg-sunken)", padding: "2px 5px", borderRadius: 4, fontFamily: "var(--mono)", fontSize: "0.85em" }}>{p.slice(1, -1)}</code>;
        }
        return p;
      });
      return (
        <React.Fragment key={lIdx}>
          {renderedParts}
          {lIdx < lines.length - 1 && <br />}
        </React.Fragment>
      );
    });
  };


  return (
    <div className="msg">
      <div className="msg-avatar bot"><Icons.logo size={15} /></div>
      <div className="msg-body">
        <div className="msg-head"><b>Pulse</b><span className="time">{m.time}</span></div>
        {m.text && <div className="msg-text"><p>{renderText(m.text)}</p></div>}
        {m.blocks && m.blocks.map((b, i) => <RichBlock key={i} block={b} onApprove={onApprove} />)}
        {m.streaming && (
          <div className="streaming">
            <span className="stream-dots"><span/><span/><span/></span>
            {m.stepText || "Thinking…"}
          </div>
        )}
        {m.followups && (
          <div className="followups">
            {m.followups.map((f, i) => (
              <button key={i} className="fu-chip">
                {f} <Icons.arrowRight />
              </button>
            ))}
          </div>
        )}
        {!m.streaming && m.text && (
          <div style={{ marginTop: 10, display: "flex", gap: 4, opacity: .6 }}>
            <button className="cb-btn" title="Copy"><Icons.copy size={13} /></button>
            <button className="cb-btn" title="Regenerate"><Icons.refresh size={13} /></button>
            <button className="cb-btn" title="Good"><Icons.thumbsUp size={13} /></button>
            <button className="cb-btn" title="Bad"><Icons.thumbsDown size={13} /></button>
          </div>
        )}
      </div>
    </div>
  );
}

function EmptyState({ onQuickPick, userProfile }) {
  const firstName = (userProfile && userProfile.first_name) ? userProfile.first_name : "Logan";
  const examples = [
    { ic: "a", title: "Summarize Q1 expenses", sub: "Break down travel, vendor, and payroll variances vs plan.", icon: "chart" },
    { ic: "b", title: "Create a purchase requisition", sub: "For 12 laptops from Dell, ship to Austin HQ, Net-30.", icon: "receipt" },
    { ic: "c", title: "Find workers on parental leave", sub: "Current + returning in the next 60 days, by team.", icon: "users" },
    { ic: "d", title: "Draft March close checklist", sub: "Include AP cutoff, journal review, and sign-off owners.", icon: "checkCircle" },
  ];
  return (
    <div className="empty-wrap">
      <div className="empty-hero">
        <div className="empty-crest"><Icons.logo size={26} /></div>
        <h1 className="empty-title">Hi {firstName}, what can I <em>pull up</em> from Workday today?</h1>
        <p className="empty-sub">
          Ask about people, spend, procurement, or reports. I can draft, reconcile, route approvals, and cite the records I used.
        </p>
      </div>
      <div className="empty-grid">
        {examples.map((e, i) => {
          const I = Icons[e.icon];
          return (
            <div key={i} className="empty-card" onClick={() => onQuickPick(e.title + " — " + e.sub)}>
              <div className={"ec-ic " + e.ic}><I /></div>
              <div className="ec-body">
                <div className="ec-title">{e.title}</div>
                <div className="ec-sub">{e.sub}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Composer({ onSend, onStop, streaming, value, setValue }) {
  const ref = useChatRef(null);
  useChatEffect(() => {
    if (ref.current) {
      ref.current.style.height = "auto";
      ref.current.style.height = Math.min(ref.current.scrollHeight, 180) + "px";
    }
  }, [value]);

  const submit = () => {
    if (!value.trim() || streaming) return;
    onSend(value.trim());
    setValue("");
  };

  return (
    <div className="composer-wrap">
      <div className="composer">
        <textarea
          ref={ref}
          className="composer-input"
          placeholder="Ask Pulse about people, spend, POs, reports…"
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={e => {
            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
          }}
          rows={1}
        />
        <div className="composer-bar">
          <button className="cb-btn" title="Attach"><Icons.paperclip size={15} /></button>
          <button className="cb-chip"><Icons.globe size={12} /> Workday · Prod</button>
          <button className="cb-chip"><Icons.zap size={12} /> Tools on</button>
          <div className="spacer" />
          <button className="cb-btn" title="Voice"><Icons.mic size={15} /></button>
          {streaming ? (
            <button className="cb-send" onClick={onStop} style={{ background: "var(--ink-2)" }}>
              <Icons.stop size={12} /> Stop
            </button>
          ) : (
            <button className="cb-send" disabled={!value.trim()} onClick={submit}>
              <Icons.arrowUp size={14} /> Send
            </button>
          )}
        </div>
      </div>
      <div className="composer-hint">
        Pulse can make mistakes. Verify critical actions before approving. <kbd>Enter</kbd> to send · <kbd>Shift+Enter</kbd> for newline
      </div>
    </div>
  );
}

function ChatArea({ convo, streaming, streamStep, onSend, onStop, onApprove, composerValue, setComposerValue, onQuickPick, userProfile }) {
  const scrollRef = useChatRef(null);
  useChatEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [convo && convo.messages && convo.messages.length, streaming, streamStep]);

  const isEmpty = !convo || !convo.messages || convo.messages.length === 0;

  return (
    <>
      <div className="chat-scroll" ref={scrollRef}>
        {isEmpty ? (
          <EmptyState onQuickPick={onQuickPick} userProfile={userProfile} />
        ) : (
          <div className="chat-inner">
            {convo.messages.map((m, i) =>
              m.role === "user"
                ? <UserMsg key={i} m={m} userProfile={userProfile} />
                : <BotMsg key={i} m={m} onApprove={onApprove} />
            )}
            {streaming && (
              <BotMsg m={{ streaming: true, time: "now", stepText: streamStep }} />
            )}
          </div>
        )}
      </div>
      <Composer
        onSend={onSend}
        onStop={onStop}
        streaming={streaming}
        value={composerValue}
        setValue={setComposerValue}
      />
    </>
  );
}

window.TopBar = TopBar;
window.ChatArea = ChatArea;
