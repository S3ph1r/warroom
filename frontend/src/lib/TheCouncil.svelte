<script>
    import { onMount } from "svelte";
    import {
        Brain,
        Scroll,
        TrendingUp,
        AlertTriangle,
        Globe,
        RefreshCw,
        History,
        Cpu,
        Terminal,
        X,
        Calendar,
    } from "lucide-svelte";

    let loading = false;
    let opinions = null;
    let error = null;
    let userQuery = "";

    // History State
    let historyDates = [];
    let selectedDate = ""; // "" means Today (Live)

    // AI Model State
    let availableModels = [];
    let selectedModel = "mistral-nemo:latest"; // Default

    // Track loading state for individual items
    let refreshingItems = {}; // { 'consensus': true, 'google_historian': false }

    // Log Overlay State
    let showLogs = false;
    let logs = [];
    let logInterval = null;

    // Auto-load session if exists
    onMount(async () => {
        // 1. Load available models
        await loadAvailableModels();
        // 2. Load History Dates
        await loadHistoryDates();
        // 3. Load cached or live session
        callTheCouncil(false);
    });

    async function loadAvailableModels() {
        try {
            const res = await fetch("/api/council/models");
            if (res.ok) {
                const models = await res.json();
                availableModels = models;
                // Auto-select mistral-nemo if available, else first one
                if (!models.includes(selectedModel) && models.length > 0) {
                    selectedModel = models[0];
                }
            }
        } catch (e) {
            console.error("Failed to load models:", e);
        }
    }

    async function loadHistoryDates() {
        try {
            const res = await fetch("/api/council/history");
            if (res.ok) {
                historyDates = await res.json();
            }
        } catch (e) {
            console.error("Failed to load history:", e);
        }
    }

    async function loadSessionByDate(date) {
        if (!date) {
            // Selected "Today"
            selectedDate = "";
            callTheCouncil(false);
            return;
        }

        selectedDate = date;
        loading = true;
        error = null;
        try {
            const res = await fetch(`/api/council/session/${date}`);
            if (!res.ok) throw new Error("Could not load archived session");
            opinions = await res.json();
        } catch (e) {
            error = e.message;
            opinions = null;
        } finally {
            loading = false;
        }
    }

    async function callTheCouncil(force = true) {
        // If we are viewing history, force switch back to today first
        if (selectedDate !== "") {
            selectedDate = "";
        }

        loading = true;
        error = null;

        // Start polling logs
        if (force) startLogPolling();

        try {
            const res = await fetch("/api/council/consult", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    query: userQuery,
                    force_refresh: force,
                    model: selectedModel,
                }),
            });
            if (!res.ok) throw new Error("Council connection failed");
            opinions = await res.json();
            console.log("DEBUG: Council Opinions Received:", opinions);

            // Refresh history list if we just created a new session
            if (!force) loadHistoryDates();

            // Update selected model to what was returned (in case cache was used)
            if (opinions && opinions.consensus_model) {
                selectedModel = opinions.consensus_model;
            }
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
            // Stop polling after a small delay to catch final logs
            if (force) setTimeout(stopLogPolling, 2000);
        }
    }

    async function fetchLogs() {
        try {
            const res = await fetch("/api/logs");
            if (res.ok) {
                const data = await res.json();
                logs = data.logs;
            }
        } catch (e) {
            console.error("Log fetch failed", e);
        }
    }

    function startLogPolling() {
        showLogs = true;
        fetchLogs();
        if (logInterval) clearInterval(logInterval);
        logInterval = setInterval(fetchLogs, 1500);
    }

    function stopLogPolling() {
        // We keep the window open so user can read, but stop traffic
        if (logInterval) {
            clearInterval(logInterval);
            logInterval = null;
        }
    }

    function toggleLogs() {
        showLogs = !showLogs;
        if (showLogs) {
            fetchLogs();
        } else {
            stopLogPolling();
        }
    }

    async function refreshItem(itemId) {
        if (selectedDate !== "") {
            alert("Cannot refresh items in historical view.");
            return;
        }
        refreshingItems[itemId] = true;
        try {
            const res = await fetch("/api/council/refresh-item", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ item_id: itemId }),
            });
            if (!res.ok) throw new Error("Refresh failed");
            const result = await res.json();

            // Update local state selectively
            if (result.type === "consensus") {
                // The API returns a raw JSON string for consensus usually, but here 'data' parsed
                let parsed = result.data;
                if (typeof parsed === "string") parsed = JSON.parse(parsed);
                opinions.consensus = parsed;
            } else if (result.type === "advisor") {
                opinions.responses[result.id] = result.data;
                opinions.responses = { ...opinions.responses }; // Trigger reactivity
            }
        } catch (e) {
            console.error(e);
            alert("Failed to refresh item: " + e.message);
        } finally {
            refreshingItems[itemId] = false;
        }
    }

    // Helper to group by model
    function getGroupedOpinions(responses) {
        if (!responses) return {};
        const grouped = {};
        // Initialize keys for order
        ["google", "anthropic", "deepseek", "qwen"].forEach(
            (k) => (grouped[k] = []),
        );

        Object.entries(responses).forEach(([role_id, data]) => {
            const [model, persona] = role_id.split("_");
            if (!grouped[model]) grouped[model] = [];
            grouped[model].push({ ...data, persona, id: role_id });
        });
        return grouped;
    }
</script>

<div class="space-y-8 pb-12">
    <!-- Header Controls -->
    <div
        class="flex flex-col md:flex-row md:items-center justify-between border-b border-skin-border pb-4 gap-4"
    >
        <div>
            <h2
                class="text-xl font-medium text-skin-text tracking-tight flex items-center gap-2"
            >
                <Brain class="w-5 h-5 text-purple-400" />
                The Council (Matrix)
                {#if selectedDate}
                    <span
                        class="text-sm font-normal text-skin-muted bg-skin-base px-2 py-0.5 rounded border border-skin-border ml-2 flex items-center gap-1"
                    >
                        <History class="w-3 h-3" /> Archive: {selectedDate}
                    </span>
                {/if}
            </h2>
            <p class="text-sm text-skin-muted hidden sm:block">
                8-Core Strategic Analysis & Consensus Engine.
            </p>
        </div>

        <div class="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
            <!-- Model Selector -->
            <div class="relative group min-w-[160px]">
                <Cpu
                    class="w-4 h-4 text-skin-muted absolute left-2.5 top-2.5 pointer-events-none"
                />
                <select
                    class="appearance-none bg-skin-card border border-skin-border rounded-lg pl-9 pr-8 py-2 text-sm w-full focus:outline-none focus:border-purple-500/50 cursor-pointer text-skin-muted hover:text-skin-text transition-colors"
                    bind:value={selectedModel}
                    on:change={() => callTheCouncil(false)}
                    disabled={selectedDate !== ""}
                >
                    {#each availableModels as model}
                        <option value={model}>{model}</option>
                    {/each}
                </select>
                <div
                    class="absolute right-2.5 top-2.5 pointer-events-none text-skin-muted text-xs"
                >
                    ▼
                </div>
            </div>

            <!-- Time Travel Dropdown -->
            <div class="relative group">
                <select
                    class="appearance-none bg-skin-card border border-skin-border rounded-lg px-3 py-2 pr-8 text-sm w-full focus:outline-none focus:border-purple-500/50 cursor-pointer text-skin-muted hover:text-skin-text transition-colors"
                    on:change={(e) => loadSessionByDate(e.target.value)}
                    value={selectedDate}
                >
                    <option value="">Live Session (Today)</option>
                    {#each historyDates as date}
                        <option value={date}>{date}</option>
                    {/each}
                </select>
                <History
                    class="w-4 h-4 text-skin-muted absolute right-2.5 top-2.5 pointer-events-none"
                />
            </div>

            <div class="h-6 w-px bg-skin-border hidden sm:block mx-1"></div>

            <input
                type="text"
                bind:value={userQuery}
                disabled={selectedDate !== ""}
                placeholder={selectedDate
                    ? "Read-only mode"
                    : "Specific question..."}
                class="bg-skin-card border border-skin-border rounded-lg px-3 py-2 text-sm w-full sm:w-64 focus:outline-none focus:border-purple-500/50 transition-all placeholder:text-skin-muted disabled:opacity-50 disabled:cursor-not-allowed"
            />

            <button
                on:click={() => callTheCouncil(true)}
                disabled={loading || selectedDate !== ""}
                class="bg-purple-600/20 hover:bg-purple-600/30 border border-purple-500/50 text-purple-300 px-4 py-2 rounded-lg text-sm font-medium transition-all disabled:opacity-50 shadow-sm flex items-center justify-center gap-2"
            >
                {#if loading}
                    <div
                        class="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full"
                    ></div>
                    Summoning...
                {:else}
                    Convene Council
                {/if}
            </button>

            <!-- Log Toggle Button -->
            <button
                on:click={toggleLogs}
                class="p-2 rounded-lg border border-skin-border hover:bg-skin-card text-skin-muted hover:text-skin-text transition-all relative"
                title="View AI Logs"
            >
                <Terminal class="w-5 h-5" />
                {#if logInterval}
                    <span
                        class="absolute top-1 right-1 w-2 h-2 bg-green-500 rounded-full animate-pulse"
                    ></span>
                {/if}
            </button>
        </div>
    </div>

    {#if error}
        <div
            class="p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm"
        >
            {error}
        </div>
    {/if}

    {#if opinions}
        <!-- 1. PRESIDENT (CONSENSUS) CARD -->
        <div
            class="bg-skin-card border border-purple-500/40 rounded-xl p-6 shadow-md relative overflow-hidden group/pres"
        >
            <div
                class="absolute top-0 right-0 p-4 opacity-10 pointer-events-none"
            >
                <Brain class="w-24 h-24 text-purple-500" />
            </div>

            <!-- Refresh Button for President -->
            <button
                on:click={() => refreshItem("consensus")}
                disabled={refreshingItems["consensus"]}
                class="absolute top-4 right-4 p-2 rounded-full bg-skin-base/50 hover:bg-skin-base text-skin-muted hover:text-purple-400 transition-colors z-20"
                title="Regenerate Consensus"
            >
                <RefreshCw
                    class="w-4 h-4 {refreshingItems['consensus']
                        ? 'animate-spin text-purple-400'
                        : ''}"
                />
            </button>

            <h3
                class="text-lg font-medium text-purple-300 mb-2 flex items-center gap-2"
            >
                <Brain class="w-5 h-5" />
                President's Consensus
            </h3>

            <!-- Session Metadata -->
            <div
                class="flex items-center gap-3 text-xs text-skin-muted mb-4 pb-4 border-b border-skin-border/30"
            >
                <div class="flex items-center gap-1">
                    <Calendar class="w-3 h-3" />
                    Session: {new Date(opinions.timestamp).toLocaleString()}
                    {#if opinions.from_cache}<span class="text-skin-muted/70"
                            >(Cached)</span
                        >{/if}
                </div>
                <div
                    class="flex items-center gap-1 px-2 py-0.5 rounded bg-skin-base/50 border border-skin-border/50"
                >
                    <Cpu class="w-3 h-3" />
                    Model:
                    <span class="text-purple-300"
                        >{opinions.consensus_model || "Unknown"}</span
                    >
                </div>
            </div>

            {#if opinions.consensus}
                {@const consensus =
                    typeof opinions.consensus === "string"
                        ? JSON.parse(opinions.consensus)
                        : opinions.consensus}

                <div
                    class="prose prose-invert prose-sm max-w-none text-skin-text mb-6"
                >
                    <p class="whitespace-pre-line leading-relaxed">
                        {consensus.summary}
                    </p>
                </div>

                <!-- Model Scores -->
                <div
                    class="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-skin-border/50"
                >
                    {#each Object.entries(consensus.scores || {}) as [model, score]}
                        <div class="bg-skin-base/30 rounded-lg p-3 text-center">
                            <div
                                class="text-xs text-skin-muted uppercase font-bold tracking-wider mb-1"
                            >
                                {model}
                            </div>
                            <div
                                class="text-xl font-bold {score >= 8
                                    ? 'text-green-400'
                                    : score >= 6
                                      ? 'text-yellow-400'
                                      : 'text-red-400'}"
                            >
                                {score}/10
                            </div>
                        </div>
                    {/each}
                </div>
            {:else}
                <div
                    class="flex flex-col items-center justify-center py-6 text-skin-muted opacity-70"
                >
                    <p class="italic mb-4">Consensus not yet formed.</p>
                    <button
                        on:click={() => refreshItem("consensus")}
                        disabled={refreshingItems["consensus"]}
                        class="px-4 py-2 rounded bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 text-sm font-medium flex items-center gap-2"
                    >
                        {#if refreshingItems["consensus"]}
                            <div
                                class="animate-spin h-3 w-3 border-2 border-current border-t-transparent rounded-full"
                            ></div>
                        {:else}
                            <Brain class="w-4 h-4" />
                        {/if}
                        Generate Consensus
                    </button>
                </div>
            {/if}
        </div>

        <!-- 2. MATRIX ROWS (4 Models x 2 Opinions) -->
        <div class="space-y-4">
            {#each Object.entries(getGroupedOpinions(opinions.responses)) as [model, items]}
                <div
                    class="bg-skin-card/50 border border-skin-border rounded-xl p-4"
                >
                    <!-- Model Header -->
                    <div
                        class="flex items-center gap-2 mb-4 border-b border-skin-border/30 pb-2"
                    >
                        <div
                            class="w-2 h-8 bg-purple-500/50 rounded-full"
                        ></div>
                        <h3
                            class="text-lg font-medium text-skin-text uppercase tracking-wider"
                        >
                            {model}
                        </h3>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {#each items as advice}
                            <!-- Stylize Persona -->
                            {@const style =
                                advice.persona === "historian"
                                    ? {
                                          color: "text-amber-400",
                                          border: "border-amber-500/30",
                                          bg: "bg-amber-500/10",
                                          icon: Scroll,
                                      }
                                    : advice.persona === "strategist"
                                      ? {
                                            color: "text-rose-400",
                                            border: "border-rose-500/30",
                                            bg: "bg-rose-500/10",
                                            icon: AlertTriangle,
                                        }
                                      : advice.persona === "quant"
                                        ? {
                                              color: "text-emerald-400",
                                              border: "border-emerald-500/30",
                                              bg: "bg-emerald-500/10",
                                              icon: TrendingUp,
                                          }
                                        : advice.persona === "insider"
                                          ? {
                                                color: "text-cyan-400",
                                                border: "border-cyan-500/30",
                                                bg: "bg-cyan-500/10",
                                                icon: Globe,
                                            }
                                          : {
                                                color: "text-gray-400",
                                                border: "border-gray-500/30",
                                                bg: "bg-gray-500/10",
                                                icon: Brain,
                                            }}

                            <div
                                class="bg-skin-base border {style.border} rounded-lg p-4 relative overflow-hidden group hover:bg-skin-base/80 transition-all"
                            >
                                <!-- Refresh Button (Individual) -->
                                <button
                                    on:click={() => refreshItem(advice.id)}
                                    disabled={refreshingItems[advice.id]}
                                    class="absolute top-2 right-2 p-1.5 rounded-full bg-skin-card hover:bg-skin-base text-skin-muted hover:text-{style.color.split(
                                        '-',
                                    )[1]}-400 opacity-0 group-hover:opacity-100 transition-all z-20"
                                    title="Regenerate this specific opinion"
                                >
                                    <RefreshCw
                                        class="w-3.5 h-3.5 {refreshingItems[
                                            advice.id
                                        ]
                                            ? 'animate-spin'
                                            : ''}"
                                    />
                                </button>

                                <!-- Watermark Icon -->
                                <div
                                    class="absolute top-2 right-2 opacity-10 scale-150 rotate-12 pointer-events-none"
                                >
                                    <svelte:component
                                        this={style.icon}
                                        class="w-12 h-12 {style.color}"
                                    />
                                </div>

                                <div
                                    class="flex items-center gap-2 mb-2 relative z-10"
                                >
                                    <svelte:component
                                        this={style.icon}
                                        class="w-4 h-4 {style.color}"
                                    />
                                    <span
                                        class="text-sm font-bold {style.color} uppercase tracking-tight"
                                        >{advice.persona}</span
                                    >
                                    <span
                                        class="ml-auto text-xs font-mono px-2 py-0.5 rounded bg-skin-card border border-skin-border text-skin-text/80"
                                    >
                                        {advice.verdict || "N/A"}
                                    </span>
                                </div>

                                <div
                                    class="relative z-10 text-sm text-skin-muted leading-relaxed min-h-[80px]"
                                >
                                    {advice.reasoning ||
                                        advice.error ||
                                        "No response"}
                                </div>

                                {#if advice.actionable_advice}
                                    <div
                                        class="relative z-10 mt-3 pt-2 border-t border-skin-border/30"
                                    >
                                        <p
                                            class="text-xs font-medium text-skin-text flex gap-2"
                                        >
                                            <span class="text-purple-400"
                                                >➤</span
                                            >
                                            {advice.actionable_advice}
                                        </p>
                                    </div>
                                {/if}
                            </div>
                        {/each}
                    </div>
                </div>
            {/each}
        </div>
    {/if}

    <!-- LOG OVERLAY TERMINAL -->
    {#if showLogs}
        <div
            class="fixed bottom-6 right-6 w-[450px] max-w-[90vw] h-[300px] bg-[#0d1117] border border-skin-border rounded-xl shadow-2xl flex flex-col z-[100] overflow-hidden antialiased"
        >
            <!-- Terminal Header -->
            <div
                class="flex items-center justify-between px-4 py-2 bg-skin-card/50 border-b border-skin-border"
            >
                <div class="flex items-center gap-2">
                    <Terminal class="w-4 h-4 text-green-400" />
                    <span class="text-xs font-mono font-bold text-skin-text/80"
                        >LLM_ADVISOR_LOGS</span
                    >
                </div>
                <button
                    on:click={() => (showLogs = false)}
                    class="text-skin-muted hover:text-white"
                >
                    <X class="w-4 h-4" />
                </button>
            </div>

            <!-- Terminal Body -->
            <div
                class="flex-1 overflow-y-auto p-3 font-mono text-[11px] leading-relaxed text-green-400/90 scrollbar-thin scrollbar-thumb-skin-border"
            >
                {#if logs.length === 0}
                    <div class="text-skin-muted opacity-50 italic">
                        Waiting for logs...
                    </div>
                {:else}
                    {#each logs as line}
                        <div class="mb-1">
                            <span class="text-blue-400 opacity-70">>></span>
                            {line}
                        </div>
                    {/each}
                {/if}
            </div>

            <!-- Terminal Footer -->
            <div
                class="px-3 py-1 bg-skin-card/30 border-t border-skin-border text-[10px] text-skin-muted flex justify-between items-center"
            >
                <span>Polling: {logInterval ? "ACTIVE" : "IDLE"}</span>
                <span class="flex items-center gap-1">
                    <div
                        class="w-1.5 h-1.5 rounded-full {logInterval
                            ? 'bg-green-500 animate-pulse'
                            : 'bg-red-500'}"
                    ></div>
                    {logInterval ? "Listening" : "Paused"}
                </span>
            </div>
        </div>
    {/if}
</div>
