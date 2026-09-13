document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const toggleAutomationBtn = document.getElementById("toggleAutomationBtn");
    const statusIndicator = document.getElementById("statusIndicator");
    const statusText = document.getElementById("statusText");
    const crawlBtn = document.getElementById("crawlBtn");
    const scanBtn = document.getElementById("scanBtn");
    const fetchMetaLeadsBtn = document.getElementById("fetchMetaLeadsBtn");
    const configForm = document.getElementById("configForm");
    const toastBanner = document.getElementById("toastBanner");

    const statIndexedCount = document.getElementById("statIndexedCount");
    const statTotalLeads = document.getElementById("statTotalLeads");
    const statPostedCount = document.getElementById("statPostedCount");

    const pagesList = document.getElementById("pagesList");
    const leadsContainer = document.getElementById("leadsContainer");

    // Load Initial Data
    fetchConfig();
    fetchSiteIndex();
    fetchLeads();

    // Helper: Show Toast Message on Screen
    function showToast(message, type = "success") {
        if (!toastBanner) return;
        toastBanner.innerText = message;
        toastBanner.className = `toast-banner ${type}`;
        toastBanner.style.display = "block";
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // Toggle Automation
    toggleAutomationBtn.addEventListener("click", async () => {
        const response = await fetch("/api/config");
        const config = await response.json();
        const newStatus = !config.automation_active;

        await fetch("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ automation_active: newStatus })
        });

        updateStatusUI(newStatus);
        showToast(newStatus ? "🟢 24/7 Threads Automation Started Successfully!" : "🟡 Automation Paused.", "success");
    });

    // Crawl Website
    crawlBtn.addEventListener("click", async () => {
        crawlBtn.disabled = true;
        crawlBtn.innerText = "⏳ Crawling Website...";
        try {
            const res = await fetch("/api/crawl", { method: "POST" });
            const data = await res.json();
            if (res.ok && data.status === "success") {
                showToast(`✅ Website Crawl Complete! Indexed ${data.count || 0} pages.`, "success");
            } else {
                showToast(`❌ Crawl Failed: ${data.message || 'Check Target Website URL in settings'}`, "error");
            }
            fetchSiteIndex();
        } catch (e) {
            showToast("❌ Crawl Error: " + e.message, "error");
        } finally {
            crawlBtn.disabled = false;
            crawlBtn.innerText = "🌐 Crawl Website Now";
        }
    });

    // Fetch Live Threads Leads
    if (fetchMetaLeadsBtn) {
        fetchMetaLeadsBtn.addEventListener("click", async () => {
            fetchMetaLeadsBtn.disabled = true;
            fetchMetaLeadsBtn.innerText = "⏳ Scanning Threads posts...";
            try {
                const res = await fetch("/api/fetch-live-leads", { method: "POST" });
                const data = await res.json();
                if (data.status === "success") {
                    const count = data.count || 0;
                    if (count > 0) {
                        showToast(`🎉 Found ${count} REAL live Threads leads! Check Telegram & Live Feed below.`, "success");
                    } else {
                        showToast(data.message || "✅ Scan complete. No new Threads leads this time.", "success");
                    }
                } else {
                    showToast(`⚠️ ${data.message}`, "error");
                }
                fetchLeads();
            } catch (e) {
                showToast("❌ Exception: " + e.message, "error");
            } finally {
                fetchMetaLeadsBtn.disabled = false;
                fetchMetaLeadsBtn.innerText = "🧵 Fetch Live Threads Leads";
            }
        });
    }

    // Run Direct Threads Scan
    if (scanBtn) {
        scanBtn.addEventListener("click", async () => {
            scanBtn.disabled = true;
            scanBtn.innerText = "⏳ Scanning Threads API...";
            try {
                const res = await fetch("/api/scan", { method: "POST" });
                const data = await res.json();
                showToast("⚡ Threads API Scan Completed!", "success");
                fetchLeads();
            } catch (e) {
                showToast("❌ Scan Error: " + e.message, "error");
            } finally {
                scanBtn.disabled = false;
                scanBtn.innerText = "⚡ Run Threads Scan";
            }
        });
    }

    // Config Submit
    configForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const payload = {
            gemini_api_key: document.getElementById("geminiApiKey").value,
            target_website_url: document.getElementById("targetWebsiteUrl").value,
            keywords: document.getElementById("keywords").value.split(",").map(k => k.trim()).filter(k => k),
            telegram: {
                bot_token: document.getElementById("telegramBotToken").value,
                chat_id: document.getElementById("telegramChatId").value
            },
            threads: {
                user_id: document.getElementById("threadsUserId")?.value || "",
                access_token: document.getElementById("threadsAccessToken")?.value || ""
            }
        };

        await fetch("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        showToast("💾 Configuration Saved Successfully!", "success");
    });

    // Fetch Helper Functions
    async function fetchConfig() {
        const res = await fetch("/api/config");
        const config = await res.json();

        document.getElementById("geminiApiKey").value = config.gemini_api_key || "";
        document.getElementById("targetWebsiteUrl").value = config.target_website_url || "";
        document.getElementById("keywords").value = (config.keywords || []).join(", ");

        if (config.telegram) {
            document.getElementById("telegramBotToken").value = config.telegram.bot_token || "";
            document.getElementById("telegramChatId").value = config.telegram.chat_id || "";
        }

        if (config.threads) {
            const tuid = document.getElementById("threadsUserId");
            const tat = document.getElementById("threadsAccessToken");
            if (tuid) tuid.value = config.threads.user_id || "";
            if (tat) tat.value = config.threads.access_token || "";
        }

        updateStatusUI(config.automation_active);
    }

    async function fetchSiteIndex() {
        const res = await fetch("/api/site-index");
        const pages = await res.json();
        statIndexedCount.innerText = pages.length;

        if (pages.length === 0) {
            pagesList.innerHTML = `<p class="text-muted">No website tools indexed yet. Click "Crawl Website Now" to auto-scan your site routes.</p>`;
            return;
        }

        pagesList.innerHTML = pages.map(p => `
            <div class="page-item">
                <h4>${escapeHtml(p.title || 'Untitled Page')}</h4>
                <p><strong>URL:</strong> <a href="${p.url}" target="_blank" style="color: var(--accent-blue)">${p.url}</a></p>
                <p style="margin-top: 4px;">${escapeHtml(p.description || 'No description extracted')}</p>
            </div>
        `).join("");
    }

    let currentLeads = [];

    // Helper: Copy Text to Clipboard
    async function copyTextToClipboard(text, btnElement = null) {
        if (!text) return false;
        try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(text);
            } else {
                const textArea = document.createElement("textarea");
                textArea.value = text;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand("copy");
                document.body.removeChild(textArea);
            }

            showToast("📋 AI Reply Copied to Clipboard!", "success");

            if (btnElement) {
                const originalText = btnElement.innerHTML;
                const originalBg = btnElement.style.background;
                btnElement.innerHTML = "✅ Copied!";
                btnElement.style.background = "#22c55e";
                btnElement.style.color = "#ffffff";
                setTimeout(() => {
                    btnElement.innerHTML = originalText;
                    btnElement.style.background = originalBg;
                    btnElement.style.color = "";
                }, 2000);
            }
            return true;
        } catch (err) {
            showToast("❌ Copy failed: " + err, "error");
            return false;
        }
    }

    async function fetchLeads() {
        const res = await fetch("/api/history");
        currentLeads = await res.json();
        statTotalLeads.innerText = currentLeads.length;
        const posted = currentLeads.filter(l => l.status === "posted_automatically").length;
        statPostedCount.innerText = posted;

        if (currentLeads.length === 0) {
            leadsContainer.innerHTML = `<p class="text-muted">No Threads leads processed yet. Start automation or click "Fetch Live Threads Leads".</p>`;
            return;
        }

        leadsContainer.innerHTML = currentLeads.map((l, idx) => `
            <div class="lead-item">
                <div class="lead-header">
                    <span class="lead-platform">🧵 ${l.platform || 'Threads'}</span>
                    <span class="lead-time">${l.timestamp}</span>
                </div>
                <div class="lead-title">
                    <strong>Post:</strong> <a href="${l.url}" target="_blank" style="color: #fff">${escapeHtml(l.title)}</a>
                </div>
                <p><strong>Intent:</strong> ${escapeHtml(l.intent || 'Needs tool')}</p>
                <div class="lead-reply-box">
                    <strong>AI Generated Reply (${l.status}):</strong><br><br>
                    <code id="reply-text-${idx}" class="clickable-code" data-lead-idx="${idx}" style="display: block; background: #0f172a; padding: 10px; border-radius: 6px; cursor: pointer; border: 1px solid var(--border-color);" title="Click to copy exact reply">${escapeHtml(l.reply_text)}</code>
                    <br>
                    <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                        <button class="btn btn-secondary copy-lead-btn" data-lead-idx="${idx}" style="padding: 6px 14px; font-size: 13px;">📋 Copy AI Reply</button>
                        <button class="btn btn-success copy-open-lead-btn" data-lead-idx="${idx}" style="padding: 6px 14px; font-size: 13px;">🚀 Copy & Open Threads Post</button>
                        <a href="${l.url}" target="_blank" class="btn btn-primary" style="padding: 6px 14px; font-size: 13px; text-decoration: none; display: inline-block;">🔗 Open Threads Post</a>
                    </div>
                    <br>
                    <strong>Target Tool:</strong> <a href="${l.matched_url}" target="_blank" style="color: var(--accent-blue)">${l.matched_url}</a>
                </div>
            </div>
        `).join("");
    }

    // Delegated Click Handlers for Feed Copy Buttons & Clickable Code
    document.addEventListener("click", (e) => {
        const copyBtn = e.target.closest(".copy-lead-btn");
        const copyOpenBtn = e.target.closest(".copy-open-lead-btn");
        const clickableCode = e.target.closest(".clickable-code");

        if (copyBtn) {
            const idx = parseInt(copyBtn.getAttribute("data-lead-idx"), 10);
            if (!isNaN(idx) && currentLeads[idx]) {
                copyTextToClipboard(currentLeads[idx].reply_text, copyBtn);
            }
            return;
        }

        if (copyOpenBtn) {
            const idx = parseInt(copyOpenBtn.getAttribute("data-lead-idx"), 10);
            if (!isNaN(idx) && currentLeads[idx]) {
                copyTextToClipboard(currentLeads[idx].reply_text, copyOpenBtn);
                if (currentLeads[idx].url && currentLeads[idx].url !== "#") {
                    window.open(currentLeads[idx].url, "_blank");
                }
            }
            return;
        }

        if (clickableCode) {
            const idx = parseInt(clickableCode.getAttribute("data-lead-idx"), 10);
            if (!isNaN(idx) && currentLeads[idx]) {
                const parentBox = clickableCode.closest(".lead-reply-box");
                const targetBtn = parentBox ? parentBox.querySelector(".copy-lead-btn") : null;
                copyTextToClipboard(currentLeads[idx].reply_text, targetBtn || clickableCode);
            }
            return;
        }
    });

    function updateStatusUI(isActive) {
        if (isActive) {
            statusIndicator.classList.add("active");
            statusText.innerText = "24/7 Threads Automation ACTIVE";
            toggleAutomationBtn.innerText = "Pause Automation";
            toggleAutomationBtn.className = "btn btn-secondary btn-block";
        } else {
            statusIndicator.classList.remove("active");
            statusText.innerText = "System Standby";
            toggleAutomationBtn.innerText = "Start 24/7 Automation";
            toggleAutomationBtn.className = "btn btn-primary btn-block";
        }
    }

    function escapeHtml(text) {
        if (!text) return "";
        return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    setInterval(fetchLeads, 30000);

    // Browser Login Manager (Threads Dedicated)
    async function loadBrowserStatus() {
        try {
            const res = await fetch("/api/browser-status");
            const data = await res.json();
            if (data.status !== "success") return;
            const info = data.platforms.threads;
            const el = document.getElementById("status-threads");
            const card = document.getElementById("card-threads");
            if (!el || !info) return;

            if (info.logged_in) {
                el.textContent = "✅ Logged In";
                el.style.color = "#4ade80";
                if (card) card.style.borderColor = "#4ade80";
            } else if (info.profile_exists) {
                el.textContent = "⚠️ Session may have expired";
                el.style.color = "#facc15";
                if (card) card.style.borderColor = "#facc15";
            } else {
                el.textContent = "❌ Not logged in";
                el.style.color = "#f87171";
                if (card) card.style.borderColor = "#374151";
            }
        } catch (e) {
            console.log("Browser status load error:", e);
        }
    }

    window.openBrowserLogin = async function(platform = "threads") {
        const el = document.getElementById("status-threads");
        if (el) { el.textContent = "🌐 Opening Chrome window…"; el.style.color = "#60a5fa"; }
        showToast("🌐 Opening Threads login window… Log in, then close Chrome.", "info");
        try {
            const res = await fetch("/api/browser-login/threads", { method: "POST" });
            const data = await res.json();
            showToast(data.message || "Threads login window opened!", data.status === "error" ? "error" : "success");
            setTimeout(() => window.checkBrowserSession("threads"), 20000);
        } catch (e) {
            showToast("❌ Failed to open browser window: " + e.message, "error");
        }
    };

    window.promptCookieImport = async function(platform = "threads") {
        const sessionId = prompt("🔑 Paste your Threads 'sessionid' cookie:\n\n(Find in Chrome F12 -> Application -> Cookies -> threads.net -> sessionid):");
        if (!sessionId) return;
        const dsUserId = prompt("🆔 Optional: Enter your Threads 'ds_user_id' (or click OK to skip):") || "";
        
        try {
            const res = await fetch("/api/browser-cookie/threads", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ session_id: sessionId, ds_user_id: dsUserId })
            });
            const data = await res.json();
            showToast(data.message || "Cookie import finished", data.status === "error" ? "error" : "success");
            window.checkBrowserSession("threads");
        } catch (e) {
            showToast("❌ Cookie import failed: " + e.message, "error");
        }
    };

    window.checkBrowserSession = async function(platform = "threads") {
        const el = document.getElementById("status-threads");
        if (el) { el.textContent = "🔄 Checking session…"; el.style.color = "#60a5fa"; }
        try {
            const res = await fetch("/api/browser-check/threads", { method: "POST" });
            const data = await res.json();
            const card = document.getElementById("card-threads");
            if (data.logged_in) {
                if (el) { el.textContent = "✅ Logged In"; el.style.color = "#4ade80"; }
                if (card) card.style.borderColor = "#4ade80";
                showToast("✅ Meta Threads session is active!", "success");
            } else {
                if (el) { el.textContent = "❌ Not logged in / Expired"; el.style.color = "#f87171"; }
                if (card) card.style.borderColor = "#374151";
                showToast("⚠️ Threads session expired. Please log in again.", "error");
            }
        } catch (e) {
            showToast("❌ Session check failed: " + e.message, "error");
        }
    };

    window.clearBrowserSession = async function(platform = "threads") {
        if (!confirm("Clear saved Meta Threads browser session? You will need to log in again.")) return;
        try {
            const res = await fetch("/api/browser-session/threads", { method: "DELETE" });
            const data = await res.json();
            const el = document.getElementById("status-threads");
            const card = document.getElementById("card-threads");
            if (el) { el.textContent = "❌ Not logged in"; el.style.color = "#f87171"; }
            if (card) card.style.borderColor = "#374151";
            showToast(data.message || "Threads session cleared.", "success");
        } catch (e) {
            showToast("❌ Clear failed: " + e.message, "error");
        }
    };

    loadBrowserStatus();
});
