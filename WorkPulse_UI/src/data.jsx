/* global React */
// Mock data — ERP conversations, rich blocks

const CONVERSATIONS = [
  {
    id: "c1",
    title: "Q1 travel expense analysis",
    group: "Today",
    pinned: true,
    lastUpdated: "2m",
    messages: [
      { role: "user", text: "Pull our Q1 travel expenses by department and flag anything unusual.", time: "10:42 AM" },
      {
        role: "bot",
        text: "Q1 travel expenses totaled **$1.42M** across 7 departments — up **12.4%** vs Q4 but **3.1% under budget**. Two departments stood out:",
        time: "10:42 AM",
        blocks: [
          {
            kind: "chart",
            title: "Travel spend by department — Q1 2026",
            badge: "Finance",
            icon: "chart",
            kpis: [
              { label: "Total spend", value: "$1.42M", delta: "+12.4%", deltaDir: "up" },
              { label: "vs Budget", value: "−3.1%", delta: "under", deltaDir: "up" },
              { label: "Top dept", value: "Sales", delta: "$412K" },
            ],
            data: [
              { label: "Sales", v: 412 },
              { label: "Eng", v: 268 },
              { label: "Exec", v: 198 },
              { label: "Mktg", v: 176 },
              { label: "Ops", v: 142 },
              { label: "CS", v: 118 },
              { label: "HR", v: 106 },
            ],
          },
          {
            kind: "table",
            title: "Flagged transactions",
            sub: "3 of 847 reviewed",
            icon: "alert",
            cols: ["Date", "Employee", "Amount", "Category", "Status"],
            rows: [
              ["Mar 18", "A. Okafor", "$8,420", "Airfare — Last-minute", ["warn", "Review"]],
              ["Mar 22", "M. Lindqvist", "$3,180", "Hotel — Above policy", ["warn", "Review"]],
              ["Feb 04", "K. Patel", "$11,900", "Offsite — Unsubmitted", ["bad", "Missing receipt"]],
            ],
          },
        ],
        followups: [
          "Email the three flagged employees",
          "Draft a Q2 travel budget proposal",
          "Show YoY comparison by quarter",
        ],
      },
    ],
  },
  {
    id: "c2",
    title: "Approve new vendor — Helix Labs",
    group: "Today",
    lastUpdated: "1h",
    needsApproval: true,
    messages: [
      { role: "user", text: "Set up Helix Labs as a new vendor. Net-30 terms, $75K cap.", time: "9:14 AM" },
      {
        role: "bot",
        text: "I'll create the vendor record. Please review before I submit — this requires your approval.",
        time: "9:14 AM",
        blocks: [
          {
            kind: "approval",
            title: "New vendor request",
            icon: "building",
            meta: [
              ["Legal name", "Helix Labs, Inc."],
              ["Tax ID", "EIN ••• 4728"],
              ["Payment terms", "Net-30"],
              ["Spend cap", "$75,000 / year"],
              ["Category", "Professional services"],
              ["Requested by", "You"],
            ],
            message: "Vendor will route through Finance approval after submission. Estimated onboarding: 2 business days.",
          },
        ],
      },
    ],
  },
  {
    id: "c3",
    title: "Direct reports — Maya Chen's team",
    group: "Today",
    lastUpdated: "3h",
    messages: [
      { role: "user", text: "Who reports to Maya Chen and what's their comp band?", time: "7:02 AM" },
      {
        role: "bot",
        text: "Maya Chen leads **6 direct reports** across the Platform team. Here's a snapshot — individual compensation details are redacted per access policy.",
        time: "7:02 AM",
        blocks: [
          {
            kind: "record",
            title: "Maya Chen",
            icon: "user",
            avatar: { initials: "MC", color: "linear-gradient(135deg,#6F8CFF,#3B5BDB)" },
            name: "Maya Chen",
            sub: "Director, Platform Engineering · Worker ID 10284",
            meta: [
              ["Department", "Engineering / Platform"],
              ["Location", "Austin, TX"],
              ["Manager", "Ravi Subramanian"],
              ["Start date", "Aug 12, 2021"],
              ["Direct reports", "6"],
              ["Cost center", "ENG-212"],
            ],
            actions: ["View profile", "Message"],
          },
          {
            kind: "table",
            title: "Direct reports",
            sub: "6 workers",
            icon: "users",
            cols: ["Name", "Title", "Band", "Tenure", "Status"],
            rows: [
              ["Elijah Park", "Staff Engineer", "P5", "3y 4m", ["good", "Active"]],
              ["Priya Narayan", "Senior Engineer II", "P4", "2y 1m", ["good", "Active"]],
              ["Tomás Ribeiro", "Senior Engineer", "P4", "1y 8m", ["good", "Active"]],
              ["Sana Al-Farsi", "Engineer II", "P3", "11 mo", ["good", "Active"]],
              ["Henry Okonkwo", "Engineer II", "P3", "7 mo", ["warn", "Onboarding"]],
              ["Zoe Harbison", "Engineering Manager", "M4", "2y 6m", ["good", "Active"]],
            ],
          },
        ],
        followups: ["Open positions on Maya's team", "Compare headcount vs last year", "Draft 1:1 agenda with Maya"],
      },
    ],
  },
  {
    id: "c4",
    title: "PO-40281 status check",
    group: "Yesterday",
    lastUpdated: "1d",
    messages: [
      { role: "user", text: "Where is PO-40281?", time: "Yesterday 4:18 PM" },
      {
        role: "bot",
        text: "PO-40281 is **awaiting receipt**. Ordered 14 days ago; vendor confirmed ship date of **Apr 21**.",
        time: "Yesterday 4:18 PM",
        blocks: [
          {
            kind: "record",
            title: "Purchase order",
            icon: "receipt",
            avatar: { initials: "PO", color: "linear-gradient(135deg,#F59E0B,#D97706)" },
            name: "PO-40281 · Dell Technologies",
            sub: "12 laptops, docks, peripherals · $38,420",
            meta: [
              ["Status", "Awaiting receipt"],
              ["Issued", "Apr 5, 2026"],
              ["Expected", "Apr 21, 2026"],
              ["Buyer", "N. Harlow"],
              ["Ship to", "HQ — Austin"],
              ["Payment", "Net-45"],
            ],
            actions: ["Track shipment", "Contact vendor"],
          },
        ],
      },
    ],
  },
  {
    id: "c5",
    title: "Draft comp letter — P. Narayan",
    group: "Yesterday",
    lastUpdated: "1d",
  },
  {
    id: "c6",
    title: "Invoice mismatch — Cloudscape Inc.",
    group: "Last 7 days",
    lastUpdated: "3d",
    hasError: true,
    messages: [
      { role: "user", text: "Cloudscape's April invoice doesn't match our PO. Can you figure out why?", time: "Apr 16" },
      {
        role: "bot",
        text: "I couldn't complete the full reconciliation — I don't have access to the Cloudscape billing portal. Here's what I could pull from Workday:",
        time: "Apr 16",
        blocks: [
          {
            kind: "error",
            title: "Permission required",
            message: "I can read your PO and receipts, but the connector to **Cloudscape Billing** is not authorized for your account. An admin can grant access in Settings → Integrations.",
            actions: ["Request access", "Open Settings"],
          },
        ],
      },
    ],
  },
  { id: "c7", title: "Time off policy — parental leave", group: "Last 7 days", lastUpdated: "4d" },
  { id: "c8", title: "Open headcount vs plan", group: "Last 7 days", lastUpdated: "5d" },
  { id: "c9", title: "Close checklist — March", group: "Last 7 days", lastUpdated: "6d" },
  { id: "c10", title: "Onboarding plan: Okonkwo", group: "Older", lastUpdated: "Apr 8" },
  { id: "c11", title: "Supplier risk review", group: "Older", lastUpdated: "Apr 2" },
  { id: "c12", title: "FY25 bonus pool scenarios", group: "Older", lastUpdated: "Mar 28" },
];

// Streaming example — used when user sends a new message
const STREAMING_RESPONSE = {
  role: "bot",
  streaming: true,
  time: "now",
  steps: [
    "Understanding request",
    "Querying Workday records",
    "Composing answer",
  ],
};

window.CONVERSATIONS = CONVERSATIONS;
window.STREAMING_RESPONSE = STREAMING_RESPONSE;
