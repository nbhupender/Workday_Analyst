document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const chatForm = document.getElementById("chat-form");
    const queryInput = document.getElementById("query-input");
    const chatMessages = document.getElementById("chat-messages");
    const typingIndicator = document.getElementById("typing-indicator");
    const debugToggle = document.getElementById("debug-toggle");
    const historyList = document.getElementById("history-list");
    const newChatBtn = document.getElementById("new-chat-btn");
    
    // Debug panel elements
    const tabButtons = document.querySelectorAll(".tab-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");
    const planGoal = document.getElementById("plan-goal");
    const planStepsList = document.getElementById("plan-steps-list");
    const ragRoutesList = document.getElementById("rag-routes-list");
    const rawJsonViewer = document.getElementById("raw-json-viewer");

    // State Variables
    let currentConversation = [];
    let queryLogs = [];

    // Initialize SPA
    init();

    function init() {
        // Load history logs
        loadHistory();

        // Form Submit Handler
        chatForm.addEventListener("submit", handleFormSubmit);

        // Input textarea auto-grow
        queryInput.addEventListener("input", autoGrowInput);

        // Tab click handler
        tabButtons.forEach(btn => {
            btn.addEventListener("click", () => switchTab(btn.dataset.tab));
        });

        // New Chat Button Handler
        newChatBtn.addEventListener("click", startNewChat);

        // Suggested Queries click handler
        document.querySelectorAll(".suggest-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                queryInput.value = btn.innerText;
                queryInput.focus();
                autoGrowInput();
            });
        });
    }

    // ================= HISTORY MANAGEMENT =================
    async function loadHistory() {
        try {
            const resp = await fetch("/api/history");
            if (!resp.ok) throw new Error("Failed to load logs");
            
            queryLogs = await resp.json();
            renderHistoryList();
        } catch (err) {
            console.error("Error loading query history:", err);
            historyList.innerHTML = `<div class="history-placeholder">Failed to load history</div>`;
        }
    }

    function renderHistoryList() {
        if (queryLogs.length === 0) {
            historyList.innerHTML = `<div class="history-placeholder">No queries logged yet</div>`;
            return;
        }

        historyList.innerHTML = "";
        queryLogs.forEach((log, index) => {
            const date = new Date(log.timestamp * 1000);
            const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            
            const card = document.createElement("div");
            card.className = "history-card";
            card.dataset.index = index;
            card.innerHTML = `
                <span class="history-card-query">${escapeHtml(log.query)}</span>
                <div class="history-card-meta">
                    <span>${log.error ? "⚠️ Failed" : "✓ Executed"}</span>
                    <span>${timeStr}</span>
                </div>
            `;
            
            card.addEventListener("click", () => loadHistoryEntry(log, card));
            historyList.appendChild(card);
        });
    }

    function loadHistoryEntry(log, cardElement) {
        // Clear active class from all cards
        document.querySelectorAll(".history-card").forEach(c => c.classList.remove("active"));
        if (cardElement) cardElement.classList.add("active");

        // Clear chat area and load history message
        chatMessages.innerHTML = "";
        
        // Add User message
        appendMessage("user", log.query, log.timestamp);
        
        // Add Assistant message
        if (log.error) {
            appendMessage("assistant", `**Execution Error:** ${log.error}`, log.timestamp);
        } else {
            appendMessage("assistant", formatAnswer(log.answer), log.timestamp);
        }

        // Render debug tabs for this log entry
        populateDebugInfo(log.plan, log.rag_matches, log.answer, log.error);
    }

    // ================= CHAT ACTIONS =================
    function startNewChat() {
        chatMessages.innerHTML = `
            <div class="system-welcome card glass">
                <h3>Welcome to the Workday AI Router Playground!</h3>
                <p>Ask questions or perform actions in plain English. The supervisor will decompose your query, fetch resources, and synthesize the result.</p>
                <div class="suggested-queries">
                    <button class="suggest-btn">Who reports to employee 21431?</button>
                    <button class="suggest-btn">What is the job title of Betty Liu?</button>
                    <button class="suggest-btn">List all workers in the London office.</button>
                </div>
            </div>
        `;
        
        // Bind click handler for suggest buttons in new chat greeting
        chatMessages.querySelectorAll(".suggest-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                queryInput.value = btn.innerText;
                queryInput.focus();
                autoGrowInput();
            });
        });

        // Reset debug views
        planGoal.innerText = "No active execution plan loaded.";
        planStepsList.innerHTML = `<div class="debug-placeholder">Plan steps will appear here when you execute a query.</div>`;
        ragRoutesList.innerHTML = `<div class="debug-placeholder">RAG vector matches and confidence scores will appear here.</div>`;
        rawJsonViewer.innerText = "Select a step or query to view raw API execution contexts.";
        
        document.querySelectorAll(".history-card").forEach(c => c.classList.remove("active"));
        queryInput.value = "";
        autoGrowInput();
    }

    async function handleFormSubmit(e) {
        e.preventDefault();
        const query = queryInput.value.trim();
        if (!query) return;

        // Reset input field
        queryInput.value = "";
        autoGrowInput();

        // 1. Append User Message
        appendMessage("user", query);

        // 2. Show running/typing loader
        typingIndicator.style.display = "flex";
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            // Call FastAPI /ask endpoint
            const debugMode = debugToggle.checked;
            const resp = await fetch(`/ask?query=${encodeURIComponent(query)}&debug=true`);
            
            typingIndicator.style.display = "none";

            if (!resp.ok) {
                const errorData = await resp.json().catch(() => ({}));
                const errorMsg = errorData.detail || "Request failed with HTTP status " + resp.status;
                throw new Error(errorMsg);
            }

            const data = await resp.json();
            
            // 3. Append Assistant Message
            appendMessage("assistant", formatAnswer(data.answer));

            // 4. Update debugging dashboards
            // Fetch the plan and raw_context since debug=true was supplied
            populateDebugInfo(data.plan, data.rag_matches, data.answer, null, data.raw_context);

            // 5. Reload history logs to show this run
            loadHistory();

        } catch (err) {
            typingIndicator.style.display = "none";
            appendMessage("assistant", `❌ **Error running query:** ${err.message}`);
            
            // Populate error in debug panels
            populateDebugInfo(null, null, null, err.message);
        }

        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function appendMessage(sender, content, timestampVal = null) {
        const bubble = document.createElement("div");
        bubble.className = `message-bubble message-${sender} glass`;
        
        // Render content
        if (typeof content === "string") {
            bubble.innerHTML = renderMarkdown(content);
        } else {
            bubble.appendChild(content);
        }

        const date = timestampVal ? new Date(timestampVal * 1000) : new Date();
        const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        const meta = document.createElement("span");
        meta.className = "message-meta";
        meta.innerText = timeStr;
        bubble.appendChild(meta);

        chatMessages.appendChild(bubble);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // ================= FORMATTERS =================
    function renderMarkdown(text) {
        if (!text) return "";
        let html = escapeHtml(text);
        
        // Bold tags: **text**
        html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        
        // Bullet lists: \n- item
        html = html.replace(/\n-\s(.*)/g, "<br>• $1");
        
        // Newlines to breaks
        html = html.replace(/\n/g, "<br>");
        return html;
    }

    function formatAnswer(answer) {
        // If the synthesized answer is structured JSON containing objects/arrays, format it as a table
        if (answer && typeof answer === "object") {
            // Check if it's list of items
            if (Array.isArray(answer.items)) {
                return renderJSONTable(answer.items);
            } else if (Array.isArray(answer.data)) {
                return renderJSONTable(answer.data);
            } else if (Array.isArray(answer)) {
                return renderJSONTable(answer);
            } else {
                // Return nested details lists
                return renderJSONCard(answer);
            }
        }
        
        return String(answer || "No response received.");
    }

    function renderJSONTable(items) {
        if (!items || items.length === 0) {
            return document.createTextNode("Empty result list.");
        }

        const container = document.createElement("div");
        container.className = "workday-table-container";

        const table = document.createElement("table");
        table.className = "workday-table";

        // Get headers from first item keys
        const headers = Object.keys(items[0]).filter(k => typeof items[0][k] !== "object");
        if (headers.length === 0) {
            // Fallback: dump stringified keys
            return document.createTextNode(JSON.stringify(items));
        }

        const thead = document.createElement("thead");
        const trHeader = document.createElement("tr");
        headers.forEach(h => {
            const th = document.createElement("th");
            th.innerText = cleanHeaderName(h);
            trHeader.appendChild(th);
        });
        thead.appendChild(trHeader);
        table.appendChild(thead);

        const tbody = document.createElement("tbody");
        items.forEach(item => {
            const tr = document.createElement("tr");
            headers.forEach(h => {
                const td = document.createElement("td");
                td.innerText = item[h] !== null ? item[h] : "-";
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        container.appendChild(table);

        return container;
    }

    function renderJSONCard(obj) {
        const card = document.createElement("div");
        card.style.display = "flex";
        card.style.flexDirection = "column";
        card.style.gap = "4px";
        card.style.fontSize = "0.9rem";

        for (const [key, val] of Object.entries(obj)) {
            if (val === null || typeof val === "object") continue;
            
            const row = document.createElement("div");
            row.innerHTML = `<strong>${cleanHeaderName(key)}:</strong> ${escapeHtml(String(val))}`;
            card.appendChild(row);
        }

        if (card.children.length === 0) {
            return document.createTextNode(JSON.stringify(obj, null, 2));
        }
        return card;
    }

    function cleanHeaderName(name) {
        // e.g. "worker_id" -> "Worker ID" or "primaryWorkEmail" -> "Primary Work Email"
        return name
            .replace(/_/g, ' ')
            .replace(/([A-Z])/g, ' $1')
            .trim()
            .replace(/^\w/, c => c.toUpperCase());
    }

    // ================= DEBUG DATA BINDING =================
    function populateDebugInfo(plan, ragMatches, answer, errorMsg, rawContext = null) {
        // 1. Tab: PLAN
        if (plan) {
            planGoal.innerText = plan.goal || "Goal unspecified.";
            
            if (plan.steps && plan.steps.length > 0) {
                planStepsList.innerHTML = "";
                plan.steps.forEach(step => {
                    const card = document.createElement("div");
                    card.className = "step-card";
                    
                    const isSoap = step.api_type === "soap";
                    const badgeClass = isSoap ? "badge-purple" : "badge-blue";
                    
                    card.innerHTML = `
                        <div class="step-num">${step.id}</div>
                        <div class="step-details">
                            <span class="step-intent">${escapeHtml(step.intent)}</span>
                            <div class="step-meta">
                                <span class="badge ${badgeClass}">${step.api_type.toUpperCase()}</span>
                                ${step.service ? `<span class="badge badge-purple">${step.service}</span>` : ""}
                                ${step.api_hint ? `<span class="badge badge-blue">Hint: "${escapeHtml(step.api_hint)}"</span>` : ""}
                            </div>
                        </div>
                    `;
                    planStepsList.appendChild(card);
                });
            } else {
                planStepsList.innerHTML = `<div class="debug-placeholder">No steps found in the plan.</div>`;
            }
        } else {
            planGoal.innerText = "No active execution plan loaded.";
            planStepsList.innerHTML = `<div class="debug-placeholder">No plan data available for this query.</div>`;
        }

        // 2. Tab: RAG ROUTING
        if (ragMatches && ragMatches.length > 0) {
            ragRoutesList.innerHTML = "";
            ragMatches.forEach(match => {
                const card = document.createElement("div");
                card.className = "rag-card";
                
                const score = match.confidence_score !== null ? (match.confidence_score * 100).toFixed(1) + "%" : "N/A";
                const scoreBadge = match.confidence_score !== null && match.confidence_score >= 0.75 ? "badge-green" : "badge-orange";
                
                let candidatesHtml = "";
                if (match.top_k_candidates && match.top_k_candidates.length > 0) {
                    candidatesHtml = `
                        <div class="candidates-list">
                            <span class="candidates-title">Top Candidates (Pinecone)</span>
                            ${match.top_k_candidates.map(cand => {
                                const isWinner = cand.route === match.matched_route || cand.api_name === match.api_name;
                                return `
                                    <div class="candidate-item ${isWinner ? 'winner' : ''}">
                                        <span class="candidate-route">${escapeHtml(cand.route || cand.api_name)}</span>
                                        <span class="candidate-score">${(cand.confidence_score * 100).toFixed(1)}%</span>
                                    </div>
                                `;
                            }).join("")}
                        </div>
                    `;
                }

                card.innerHTML = `
                    <div class="rag-card-header">
                        <span class="rag-card-title">${cleanHeaderName(match.step)} Match Details</span>
                        <span class="badge ${scoreBadge}">Match: ${score}</span>
                    </div>
                    <div class="rag-card-body">
                        <div><strong>Target Route:</strong> ${escapeHtml(match.matched_route || match.api_name)}</div>
                        ${match.executed_url ? `<div><strong>Executed Endpoint URL:</strong></div><div class="rag-url">${escapeHtml(match.executed_url)}</div>` : ""}
                        ${candidatesHtml}
                    </div>
                `;
                ragRoutesList.appendChild(card);
            });
        } else {
            ragRoutesList.innerHTML = `<div class="debug-placeholder">No RAG routing occurred for this request.</div>`;
        }

        // 3. Tab: RAW OUTPUT
        if (errorMsg) {
            rawJsonViewer.innerText = `Error State:\n${errorMsg}`;
        } else if (rawContext) {
            rawJsonViewer.innerText = JSON.stringify(rawContext, null, 2);
        } else if (answer) {
            rawJsonViewer.innerText = JSON.stringify({
                status: "success",
                result_answer: answer
            }, null, 2);
        } else {
            rawJsonViewer.innerText = "Select a step or query to view raw API execution contexts.";
        }
    }

    // ================= TAB SWITCHING =================
    function switchTab(tabId) {
        tabButtons.forEach(btn => {
            btn.classList.toggle("active", btn.dataset.tab === tabId);
        });
        tabPanes.forEach(pane => {
            pane.classList.toggle("active", pane.id === tabId);
        });
    }

    // ================= HELPERS =================
    function autoGrowInput() {
        queryInput.style.height = "auto";
        queryInput.style.height = (queryInput.scrollHeight) + "px";
    }

    function escapeHtml(text) {
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
