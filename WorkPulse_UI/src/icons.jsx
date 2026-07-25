/* global React */
// Minimal consistent stroke icon set (lucide-style, hand-curated)
const Ic = ({ d, size = 16, stroke = 1.75, fill, style, children, viewBox = "0 0 24 24" }) => (
  <svg width={size} height={size} viewBox={viewBox} fill={fill || "none"} stroke="currentColor"
       strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" style={style} aria-hidden>
    {d ? <path d={d} /> : children}
  </svg>
);

const Icons = {
  // brand
  logo: (p) => <Ic {...p}><path d="M4 17l4-8 4 6 4-10 4 12"/></Ic>,
  sparkle: (p) => <Ic {...p}><path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.5 5.5l2.8 2.8M15.7 15.7l2.8 2.8M18.5 5.5l-2.8 2.8M8.3 15.7l-2.8 2.8"/></Ic>,
  // nav/actions
  plus: (p) => <Ic {...p}><path d="M12 5v14M5 12h14"/></Ic>,
  search: (p) => <Ic {...p}><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></Ic>,
  panelLeft: (p) => <Ic {...p}><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/></Ic>,
  moreH: (p) => <Ic {...p}><circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/></Ic>,
  moreV: (p) => <Ic {...p}><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></Ic>,
  send: (p) => <Ic {...p}><path d="M4 12l16-8-5 18-3-7-8-3z"/></Ic>,
  mic: (p) => <Ic {...p}><rect x="9" y="3" width="6" height="12" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></Ic>,
  paperclip: (p) => <Ic {...p}><path d="M21 11l-8.5 8.5a5 5 0 1 1-7.1-7.1L14 3.9a3.5 3.5 0 0 1 5 5L10.4 17.4a2 2 0 0 1-2.8-2.8L15 7"/></Ic>,
  settings: (p) => <Ic {...p}><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></Ic>,
  // content
  user: (p) => <Ic {...p}><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></Ic>,
  users: (p) => <Ic {...p}><circle cx="9" cy="8" r="4"/><path d="M2 21a7 7 0 0 1 14 0M17 11a4 4 0 1 0 0-8M22 21a7 7 0 0 0-5-6.7"/></Ic>,
  chart: (p) => <Ic {...p}><path d="M3 21V5M21 21H3M7 17V12M11 17V9M15 17v-5M19 17V7"/></Ic>,
  file: (p) => <Ic {...p}><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h5"/></Ic>,
  check: (p) => <Ic {...p}><path d="M5 12l5 5L20 6"/></Ic>,
  checkCircle: (p) => <Ic {...p}><circle cx="12" cy="12" r="9"/><path d="M8.5 12.5l2.5 2.5L15.5 10"/></Ic>,
  x: (p) => <Ic {...p}><path d="M6 6l12 12M18 6L6 18"/></Ic>,
  alert: (p) => <Ic {...p}><path d="M12 3L2 20h20L12 3z"/><path d="M12 10v4M12 17v.5"/></Ic>,
  alertCircle: (p) => <Ic {...p}><circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16v.5"/></Ic>,
  info: (p) => <Ic {...p}><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.5"/></Ic>,
  arrowRight: (p) => <Ic {...p}><path d="M5 12h14M13 6l6 6-6 6"/></Ic>,
  arrowUp: (p) => <Ic {...p}><path d="M12 19V5M6 11l6-6 6 6"/></Ic>,
  coins: (p) => <Ic {...p}><ellipse cx="8" cy="8" rx="6" ry="3"/><path d="M2 8v4c0 1.7 2.7 3 6 3M2 12v4c0 1.7 2.7 3 6 3"/><ellipse cx="16" cy="15" rx="6" ry="3"/><path d="M22 15v4c0 1.7-2.7 3-6 3"/></Ic>,
  clock: (p) => <Ic {...p}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></Ic>,
  shield: (p) => <Ic {...p}><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z"/></Ic>,
  lock: (p) => <Ic {...p}><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 1 1 8 0v4"/></Ic>,
  receipt: (p) => <Ic {...p}><path d="M4 3h16v18l-3-2-3 2-3-2-3 2-4-2V3z"/><path d="M8 8h8M8 12h8M8 16h5"/></Ic>,
  building: (p) => <Ic {...p}><rect x="4" y="3" width="16" height="18" rx="1"/><path d="M9 8h.5M14.5 8h.5M9 12h.5M14.5 12h.5M9 16h.5M14.5 16h.5"/></Ic>,
  package: (p) => <Ic {...p}><path d="M21 8L12 3 3 8v8l9 5 9-5V8z"/><path d="M3 8l9 5 9-5M12 13v8"/></Ic>,
  briefcase: (p) => <Ic {...p}><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 13h18"/></Ic>,
  trending: (p) => <Ic {...p}><path d="M3 17l6-6 4 4 8-8M14 7h7v7"/></Ic>,
  zap: (p) => <Ic {...p}><path d="M13 3L4 14h6l-1 7 9-11h-6l1-7z"/></Ic>,
  pencil: (p) => <Ic {...p}><path d="M14.5 4.5l5 5L8 21H3v-5L14.5 4.5z"/></Ic>,
  trash: (p) => <Ic {...p}><path d="M4 7h16M10 11v6M14 11v6M5 7l1 13a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2l1-13M9 7V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v3"/></Ic>,
  copy: (p) => <Ic {...p}><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/></Ic>,
  refresh: (p) => <Ic {...p}><path d="M3 12a9 9 0 0 1 15-6.7L21 8M21 3v5h-5M21 12a9 9 0 0 1-15 6.7L3 16M3 21v-5h5"/></Ic>,
  externalLink: (p) => <Ic {...p}><path d="M14 4h6v6M20 4L10 14M14 20H6a2 2 0 0 1-2-2V10"/></Ic>,
  sun: (p) => <Ic {...p}><circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M3 12h2M19 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"/></Ic>,
  moon: (p) => <Ic {...p}><path d="M20 15A8 8 0 1 1 9 4a6 6 0 0 0 11 11z"/></Ic>,
  thumbsUp: (p) => <Ic {...p}><path d="M7 22V10l5-7a2 2 0 0 1 2 2v5h6a2 2 0 0 1 2 2l-2 8a2 2 0 0 1-2 2H7z"/><path d="M7 10H3v12h4"/></Ic>,
  thumbsDown: (p) => <Ic {...p}><path d="M17 2v12l-5 7a2 2 0 0 1-2-2v-5H4a2 2 0 0 1-2-2l2-8a2 2 0 0 1 2-2h11z"/><path d="M17 14h4V2h-4"/></Ic>,
  palette: (p) => <Ic {...p}><path d="M12 3a9 9 0 1 0 0 18 3 3 0 0 0 3-3c0-.8-.3-1.4-.9-2-.5-.5-.8-1.2-.8-2 0-1.1.9-2 2-2H18a3 3 0 0 0 3-3c0-3.8-4-6-9-6z"/><circle cx="7.5" cy="10.5" r="1"/><circle cx="12" cy="7.5" r="1"/><circle cx="16.5" cy="10.5" r="1"/></Ic>,
  calendar: (p) => <Ic {...p}><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 9h18M8 3v4M16 3v4"/></Ic>,
  download: (p) => <Ic {...p}><path d="M12 4v12M7 11l5 5 5-5M4 20h16"/></Ic>,
  star: (p) => <Ic {...p}><path d="M12 3l2.7 6 6.3.5-4.8 4.1 1.5 6.4L12 16.8 6.3 20l1.5-6.4L3 9.5 9.3 9 12 3z"/></Ic>,
  leftChevron: (p) => <Ic {...p}><path d="M15 6l-6 6 6 6"/></Ic>,
  stop: (p) => <Ic {...p}><rect x="6" y="6" width="12" height="12" rx="2"/></Ic>,
  message: (p) => <Ic {...p}><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></Ic>,
  globe: (p) => <Ic {...p}><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/></Ic>,
};

window.Icons = Icons;
