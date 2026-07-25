/* global React, Icons */
const ACCENTS = [
  { name: "Indigo", h: 232, s: 72 },
  { name: "Violet", h: 266, s: 70 },
  { name: "Teal",   h: 178, s: 62 },
  { name: "Emerald", h: 152, s: 58 },
  { name: "Amber",  h: 34,  s: 88 },
  { name: "Rose",   h: 346, s: 72 },
];

function TweaksPanel({ open, onClose, theme, setTheme, collapsed, setCollapsed, accent, setAccent }) {
  if (!open) return null;
  return (
    <div className="tweaks" role="dialog" aria-label="Tweaks">
      <div className="tw-head">
        <Icons.palette size={14} /> <b>Tweaks</b>
        <button className="tw-close" onClick={onClose}><Icons.x size={14} /></button>
      </div>
      <div className="tw-body">
        <div className="tw-row">
          <label>Appearance</label>
          <div className="tw-seg">
            <button data-on={theme === "light"} onClick={() => setTheme("light")}><Icons.sun /> Light</button>
            <button data-on={theme === "dark"} onClick={() => setTheme("dark")}><Icons.moon /> Dark</button>
          </div>
        </div>
        <div className="tw-row">
          <label>Sidebar</label>
          <div className="tw-seg">
            <button data-on={!collapsed} onClick={() => setCollapsed(false)}>Expanded</button>
            <button data-on={collapsed} onClick={() => setCollapsed(true)}>Collapsed</button>
          </div>
        </div>
        <div className="tw-row">
          <label>Accent color</label>
          <div className="tw-swatches">
            {ACCENTS.map(a => (
              <button key={a.name} className="tw-swatch"
                      data-on={accent.h === a.h}
                      onClick={() => setAccent(a)}
                      title={a.name}
                      style={{ background: `hsl(${a.h} ${a.s}% 56%)` }} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

window.TweaksPanel = TweaksPanel;
