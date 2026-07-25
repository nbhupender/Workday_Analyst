/* global React, Icons */
function Sidebar({ collapsed, onToggleCollapse, conversations, activeId, onSelect, onNew, query, onQuery, userProfile }) {
  const groups = [];
  const byGroup = {};
  const pinned = conversations.filter(c => c.pinned);
  const filtered = conversations.filter(c => {
    if (!query.trim()) return true;
    return c.title.toLowerCase().includes(query.toLowerCase());
  });
  for (const c of filtered) {
    if (!byGroup[c.group]) { byGroup[c.group] = []; groups.push(c.group); }
    byGroup[c.group].push(c);
  }

  const profile = userProfile || { name: "Logan McNeil", initials: "LM", title: "Vice President, Human Resources" };

  return (
    <aside className="sidebar">
      <div className="sb-top">
        <div className="sb-logo"><Icons.logo size={16} /></div>
        <div className="sb-wordmark">
          WorkPulse
          <small>Workday ERP assistant</small>
        </div>
        <button className="sb-collapse" onClick={onToggleCollapse} title={collapsed ? "Expand" : "Collapse"}>
          <Icons.panelLeft size={16} />
        </button>
      </div>

      <button className="sb-new" onClick={onNew}>
        <Icons.plus size={15} />
        <span className="sb-new-label">New chat</span>
        <span className="sb-new-kbd">⌘K</span>
      </button>

      <div className="sb-search">
        <Icons.search />
        <input placeholder="Search chats" value={query} onChange={e => onQuery(e.target.value)} />
      </div>

      <div className="sb-scroll">
        {pinned.length > 0 && !query && (
          <div className="sb-group">
            <div className="sb-group-label">Pinned</div>
            {pinned.map(c => (
              <div key={"p" + c.id}
                   className="sb-item"
                   data-active={activeId === c.id}
                   onClick={() => onSelect(c.id)}>
                <Icons.star size={13} className="sb-item-icon" />
                <span className="sb-item-title">{c.title}</span>
                <span className="sb-item-menu"><Icons.moreH size={13} /></span>
              </div>
            ))}
          </div>
        )}
        {groups.map(g => (
          <div key={g} className="sb-group">
            <div className="sb-group-label">{g}</div>
            {byGroup[g].map(c => (
              <div key={c.id}
                   className="sb-item"
                   data-active={activeId === c.id}
                   onClick={() => onSelect(c.id)}>
                <span className="sb-item-title">{c.title}</span>
                <span className="sb-item-menu"><Icons.moreH size={13} /></span>
              </div>
            ))}
          </div>
        ))}
      </div>

      <div className="sb-bottom">
        <div className="sb-avatar">{profile.initials}</div>
        <div className="sb-bottom-info">
          <b>{profile.name}</b>
          <small>{profile.title}</small>
        </div>
        <button className="sb-settings" title="Settings"><Icons.settings size={15} /></button>
      </div>
    </aside>
  );
}

window.Sidebar = Sidebar;
