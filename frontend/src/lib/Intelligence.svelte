<script>
    import { onMount, onDestroy } from "svelte";
    import { Shield, Globe, Terminal } from "lucide-svelte";

    let items = [];
    let loading = true;
    let scanning = false;
    let error = null;

    let selectedSource = "All";

    // Log Overlay State
    let showLogs = false;
    let logs = [];
    let logInterval = null;

    // Safe source extraction
    function getSources(data) {
        try {
            if (!Array.isArray(data)) return ["All"];
            const unique = new Set(data.map((i) => i?.source).filter(Boolean));
            return ["All", ...unique];
        } catch (e) {
            console.error("Error extracting sources:", e);
            return ["All"];
        }
    }

    $: sources = getSources(items);

    $: filteredItems =
        selectedSource === "All"
            ? items || []
            : (items || []).filter((item) => item?.source === selectedSource);

    const API_BASE = ""; // Use relative path through proxy

    async function loadData() {
        try {
            loading = true;
            error = null;
            const res = await fetch(`${API_BASE}/api/intelligence`);
            if (!res.ok) throw new Error("Failed to load intelligence");
            const data = await res.json();
            items = Array.isArray(data) ? data : [];
        } catch (e) {
            console.error("Error loading intelligence:", e);
            error = e.message;
        } finally {
            loading = false;
        }
    }

    // Polling Logs
    async function fetchLogs() {
        try {
            const res = await fetch(`${API_BASE}/api/logs`);
            if (res.ok) {
                const data = await res.json();
                logs = data.logs || [];
                // Auto-scroll logic if needed
            }
        } catch (e) {
            console.error("Log fetch failed:", e);
        }
    }

    function startLogPolling() {
        showLogs = true;
        logs = [];
        // Clear backend logs first not strictly needed as endpoint clears log_buffer
        // but nice to have empty UI state
        if (logInterval) clearInterval(logInterval);
        logInterval = setInterval(fetchLogs, 500);
    }

    function stopLogPolling() {
        if (logInterval) clearInterval(logInterval);
        fetchLogs(); // one last fetch
        setTimeout(() => {
            showLogs = false;
        }, 3000); // Hide after delay
    }

    async function runScan() {
        try {
            scanning = true;
            startLogPolling();

            await fetch(`${API_BASE}/api/intelligence/scan`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ force: true }),
            });
            await loadData();
        } finally {
            scanning = false;
            stopLogPolling();
        }
    }

    onMount(loadData);
    onDestroy(() => {
        if (logInterval) clearInterval(logInterval);
    });
</script>

<div class="space-y-6 relative h-full">
    <div class="flex flex-col gap-4 pb-4 border-b border-skin-border">
        <div class="flex items-center justify-between">
            <h2 class="text-xl font-medium text-skin-text tracking-tight">
                Intelligence Feed
            </h2>
            <div class="flex gap-2">
                <button
                    on:click={() => (showLogs = !showLogs)}
                    class="p-2 text-skin-muted hover:text-skin-text transition-colors"
                    title="Toggle Logs"
                >
                    <Terminal size={18} />
                </button>
                <button
                    on:click={runScan}
                    disabled={scanning}
                    class="bg-skin-card border border-skin-border hover:border-skin-muted text-skin-text px-3 py-1.5 rounded-md text-sm font-medium transition-all disabled:opacity-50 shadow-sm"
                >
                    {scanning ? "Scanning..." : "Run Analysis"}
                </button>
            </div>
        </div>

        <!-- Source Filters -->
        <div class="flex flex-wrap gap-2 pb-2">
            {#each sources as source}
                <button
                    class="whitespace-nowrap px-3 py-1 rounded-full text-xs font-medium border transition-all {selectedSource ===
                    source
                        ? 'bg-skin-accent text-skin-base border-skin-accent'
                        : 'bg-skin-card border-skin-border text-skin-muted hover:text-skin-text'}"
                    on:click={() => (selectedSource = source)}
                >
                    {source}
                </button>
            {/each}
        </div>
    </div>

    <!-- LOG OVERLAY -->
    {#if showLogs}
        <div
            class="fixed bottom-6 right-6 w-96 max-h-80 bg-black/90 backdrop-blur border border-skin-border rounded-lg shadow-2xl p-4 z-50 overflow-hidden flex flex-col font-mono text-xs"
        >
            <div
                class="flex items-center justify-between border-b border-white/10 pb-2 mb-2"
            >
                <span class="text-green-400 font-bold flex items-center gap-2">
                    {#if scanning}<span class="animate-pulse">●</span>{/if}
                    Execution Logs
                </span>
                <span class="text-white/40 text-[10px]"
                    >{logs.length} lines</span
                >
            </div>
            <div class="overflow-y-auto flex-1 scrollbar-hide space-y-1">
                {#if logs.length === 0}
                    <div class="text-white/30 italic">
                        Waiting for process...
                    </div>
                {/if}
                {#each logs.slice().reverse() as log}
                    <div
                        class="text-gray-300 break-all border-l-2 border-transparent hover:border-white/20 pl-2"
                    >
                        {log}
                    </div>
                {/each}
            </div>
        </div>
    {/if}

    {#if error}
        <div
            class="p-4 bg-skin-neg/10 border border-skin-neg/20 text-skin-neg rounded-md text-sm text-center"
        >
            {error}
        </div>
    {:else if loading && !scanning}
        <div class="flex justify-center py-20">
            <div
                class="w-5 h-5 border-2 border-skin-muted border-t-transparent rounded-full animate-spin"
            ></div>
        </div>
    {:else if items.length === 0}
        <div class="text-center text-skin-muted py-20 font-medium text-sm">
            No intelligence data found. Run a scan.
        </div>
    {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pb-20">
            {#each filteredItems as item}
                <div
                    class="bg-skin-card backdrop-blur-md border border-skin-border rounded-lg p-4 hover:border-skin-muted/50 transition-colors group flex flex-col h-full {item.strategy ||
                        'noise'}"
                >
                    <!-- Header -->
                    <div class="mb-3">
                        <a
                            href={item.link}
                            target="_blank"
                            class="block font-medium text-skin-text leading-snug hover:text-skin-accent transition-colors mb-1"
                        >
                            {#if item.is_video}
                                <span
                                    class="inline-flex items-center gap-2 text-skin-accent"
                                >
                                    <svg
                                        xmlns="http://www.w3.org/2000/svg"
                                        class="w-4 h-4 text-skin-accent"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        stroke="currentColor"
                                    >
                                        <path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            stroke-width="2"
                                            d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                                        />
                                        <path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            stroke-width="2"
                                            d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                        />
                                    </svg>
                                    <span class="hover:underline"
                                        >{item.title.replace(
                                            "[VIDEO] ",
                                            "",
                                        )}</span
                                    >
                                </span>
                            {:else}
                                {item.title}
                            {/if}
                        </a>
                        <div class="flex items-center gap-2 mt-2">
                            <span
                                class="text-xs text-skin-muted font-medium px-2 py-0.5 rounded-full bg-skin-card-highlight border border-skin-border/50"
                            >
                                {item.source}
                            </span>
                            <span class="text-xs text-skin-muted">
                                • {item.published_at
                                    ? item.published_at.substring(0, 10)
                                    : ""}
                            </span>
                        </div>
                    </div>

                    <!-- Scores -->
                    <div class="flex gap-2 mb-3">
                        <div
                            class="flex items-center gap-1 px-1.5 py-0.5 rounded border border-skin-border text-skin-muted text-[10px] font-mono"
                        >
                            <Shield size={10} />
                            R:{item.relevance_score || 0}
                        </div>
                        <div
                            class="flex items-center gap-1 px-1.5 py-0.5 rounded border border-skin-border text-skin-muted text-[10px] font-mono"
                        >
                            <Globe size={10} />
                            M:{item.magnitude_score || 0}
                        </div>
                    </div>

                    <!-- Summary / Reason -->
                    <div
                        class="text-xs text-skin-muted/80 line-clamp-3 flex-1 mb-3 leading-relaxed"
                    >
                        {#if item.is_video}
                            <span
                                class="text-[10px] font-bold text-skin-accent uppercase tracking-wider mr-1"
                                >[AI Summary]</span
                            >
                        {/if}
                        {item.summary ||
                            item.relevance_reason ||
                            item.magnitude_reason}
                    </div>

                    <!-- Tags -->
                    <div
                        class="flex flex-wrap gap-1.5 mt-auto pt-3 border-t border-skin-border"
                    >
                        {#each (item.tags || []).slice(0, 3) as tag}
                            <span
                                class="text-[10px] text-skin-muted font-medium bg-skin-base px-1.5 py-0.5 rounded border border-skin-border"
                                >#{tag}</span
                            >
                        {/each}
                    </div>
                </div>
            {/each}
        </div>
    {/if}
</div>

<style>
    .alpha {
        border-left: 3px solid #10b981;
    }
    .beta {
        border-left: 3px solid #3b82f6;
    }
    .gamma {
        border-left: 3px solid #ef4444;
    }
    .noise {
        border-left: 3px solid #374151;
    }

    /* Scrollbar Hide for Log Window */
    .scrollbar-hide::-webkit-scrollbar {
        display: none;
    }
    .scrollbar-hide {
        -ms-overflow-style: none;
        scrollbar-width: none;
    }
</style>
