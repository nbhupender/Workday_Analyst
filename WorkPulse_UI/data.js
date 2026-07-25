// Mock data for WorkPulse ERP chat

window.CONVERSATIONS = [
  {
    id: 'c1',
    title: 'Q1 headcount by department',
    group: 'Today',
    time: '2:14 PM',
    pinned: true,
    messages: [
      { role: 'user', text: 'Show me headcount by department for Q1, and flag any that grew more than 10%.' },
      {
        role: 'assistant',
        blocks: [
          { type: 'text', text: "Here's Q1 headcount across your 6 active departments. **Engineering** and **Customer Success** both grew more than 10% — flagged below." },
          {
            type: 'chart',
            variant: 'bar',
            title: 'Headcount by department — Q1 2026',
            subtitle: 'Source: Worker records · Active employees',
            data: [
              { label: 'Engineering', value: 184, prev: 162, flag: true },
              { label: 'Sales', value: 142, prev: 138 },
              { label: 'Customer Success', value: 96, prev: 84, flag: true },
              { label: 'Finance', value: 48, prev: 47 },
              { label: 'People Ops', value: 31, prev: 30 },
              { label: 'Legal', value: 18, prev: 18 },
            ],
          },
          { type: 'text', text: 'Two departments exceeded the 10% growth threshold:' },
          {
            type: 'records',
            items: [
              { kind: 'dept', name: 'Engineering', meta: '184 workers · +13.6% QoQ', sub: 'Lead: Priya Natarajan', delta: '+22' },
              { kind: 'dept', name: 'Customer Success', meta: '96 workers · +14.3% QoQ', sub: 'Lead: Marcus Holloway', delta: '+12' },
            ],
          },
          { type: 'followup', prompts: ['Break Engineering down by team', 'Show attrition for these teams', 'Compare to budgeted headcount'] },
        ],
      },
    ],
  },
  {
    id: 'c2',
    title: 'Approve PO-48291 for Dell laptops',
    group: 'Today',
    time: '11:02 AM',
    messages: [
      { role: 'user', text: "What's PO-48291 and should I approve it?" },
      {
        role: 'assistant',
        blocks: [
          { type: 'text', text: 'PO-48291 is a pending purchase order from IT Procurement. Summary below — it sits within your approval threshold ($50k).' },
          {
            type: 'po',
            id: 'PO-48291',
            vendor: 'Dell Technologies',
            amount: '$42,180.00',
            items: '24× Latitude 7450 laptops',
            requester: 'Jordan Chen · IT Hardware',
            costCenter: 'CC-2104 · IT Operations',
            needed: 'Apr 28, 2026',
            status: 'pending-approval',
          },
          { type: 'text', text: 'Vendor is on your preferred list. Spend is within IT Hardware budget (73% utilized YTD). Would you like to approve?' },
          {
            type: 'approval',
            recordId: 'PO-48291',
            approveLabel: 'Approve PO-48291',
            declineLabel: 'Decline',
            commentPlaceholder: 'Add an optional comment…',
          },
        ],
      },
    ],
  },
  {
    id: 'c3',
    title: 'Time off balance for Alex Rivera',
    group: 'Today',
    time: '9:48 AM',
    messages: [
      { role: 'user', text: 'How much PTO does Alex Rivera have left this year?' },
      {
        role: 'assistant',
        blocks: [
          { type: 'text', text: 'Alex Rivera (Sr. Product Designer) has the following balances as of today:' },
          {
            type: 'records',
            items: [
              { kind: 'balance', name: 'Vacation', meta: '14.5 days remaining', sub: '24 accrued · 9.5 used', delta: '14.5d' },
              { kind: 'balance', name: 'Sick leave', meta: '10.0 days remaining', sub: '10 accrued · 0 used', delta: '10.0d' },
              { kind: 'balance', name: 'Personal', meta: '2.0 days remaining', sub: '3 accrued · 1 used', delta: '2.0d' },
            ],
          },
          { type: 'followup', prompts: ['Submit a vacation request for Alex', 'Show pending requests on the team', 'Forecast balance at year-end'] },
        ],
      },
    ],
  },
  {
    id: 'c4',
    title: 'AP aging summary — April',
    group: 'Yesterday',
    time: 'Yesterday',
    messages: [
      { role: 'user', text: "What's our accounts payable aging look like this month?" },
      {
        role: 'assistant',
        blocks: [
          { type: 'text', text: "Here's April AP aging. Total outstanding is **$2.41M** across 312 invoices. The 60+ day bucket doubled vs last month — worth a look." },
          {
            type: 'chart',
            variant: 'line',
            title: 'AP aging trend — last 6 months',
            subtitle: 'Total outstanding by bucket',
            series: [
              { name: 'Current', color: 'accent', points: [1.8, 1.9, 2.0, 2.1, 2.0, 1.94] },
              { name: '30–60 days', color: 'muted', points: [0.3, 0.35, 0.32, 0.28, 0.3, 0.34] },
              { name: '60+ days', color: 'danger', points: [0.06, 0.05, 0.07, 0.06, 0.07, 0.13] },
            ],
            xLabels: ['Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr'],
          },
          {
            type: 'records',
            items: [
              { kind: 'invoice', name: 'INV-77812 · Acme Logistics', meta: '$84,200.00 · 74 days overdue', sub: 'Due Feb 4, 2026', delta: 'Overdue', danger: true },
              { kind: 'invoice', name: 'INV-78044 · Northwind Cloud', meta: '$31,450.00 · 62 days overdue', sub: 'Due Feb 16, 2026', delta: 'Overdue', danger: true },
            ],
          },
        ],
      },
    ],
  },
  {
    id: 'c5',
    title: 'Expense report flagged for review',
    group: 'Yesterday',
    time: 'Yesterday',
    error: true,
    messages: [
      { role: 'user', text: 'Approve expense report EXP-9911 for Sam Patel.' },
      {
        role: 'assistant',
        blocks: [
          {
            type: 'error',
            title: 'Permission required',
            body: "You don't have approval rights for expense reports above $2,500. EXP-9911 totals **$3,840.12** and needs VP Finance approval.",
            actions: ['Request approval from Dana Liu (VP Finance)', 'View report details'],
          },
        ],
      },
    ],
  },
  {
    id: 'c6',
    title: 'Revenue forecast vs plan',
    group: 'Last 7 days',
    time: 'Apr 15',
    messages: [{ role: 'user', text: 'placeholder' }],
  },
  {
    id: 'c7',
    title: 'New hire onboarding checklist — Mia Ford',
    group: 'Last 7 days',
    time: 'Apr 14',
    messages: [{ role: 'user', text: 'placeholder' }],
  },
  {
    id: 'c8',
    title: 'Top 10 vendors by spend FY26',
    group: 'Last 7 days',
    time: 'Apr 13',
    messages: [{ role: 'user', text: 'placeholder' }],
  },
  {
    id: 'c9',
    title: 'Journal entry JE-22041 explain',
    group: 'Last 7 days',
    time: 'Apr 12',
    messages: [{ role: 'user', text: 'placeholder' }],
  },
  {
    id: 'c10',
    title: 'Requisition for standing desks',
    group: 'Earlier',
    time: 'Apr 7',
    messages: [{ role: 'user', text: 'placeholder' }],
  },
  {
    id: 'c11',
    title: 'Pending approvals queue',
    group: 'Earlier',
    time: 'Apr 3',
    messages: [{ role: 'user', text: 'placeholder' }],
  },
  {
    id: 'c12',
    title: 'Close checklist — March period',
    group: 'Earlier',
    time: 'Mar 31',
    messages: [{ role: 'user', text: 'placeholder' }],
  },
];

window.SUGGESTED_PROMPTS = [
  { icon: 'chart', title: 'Headcount report', sub: 'by department, with QoQ change' },
  { icon: 'approve', title: 'Review pending approvals', sub: 'POs, expenses, and time off' },
  { icon: 'invoice', title: 'AP aging summary', sub: 'overdue invoices this period' },
  { icon: 'person', title: 'Find an employee', sub: 'by name, team, or manager' },
  { icon: 'create', title: 'Submit a request', sub: 'time off, expense, or purchase' },
  { icon: 'forecast', title: 'Revenue vs plan', sub: 'FY26 actuals against budget' },
];
