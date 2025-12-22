<script>
    import { onMount } from "svelte";
    import { Shield, Globe } from "lucide-svelte";

    let items = [];
    let loading = true;
    let scanning = false;
    let error = null;

    let selectedSource = "All";

    // Safe source extraction
    function getSources(data) {
        try {
            if (!Array.isArray(data)) return ["All"];
            const unique = new Set(
                data.map((i) => i?.metadata?.source).filter(Boolean),
            );
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
            : (items || []).filter(
                  (item) => item?.metadata?.source === selectedSource,
              );

    const API_BASE = "http://localhost:8200";

    async function loadData() {
        try {
            loading = true;
            error = null;
            const res = await fetch(`${API_BASE}/api/intelligence`);
            if (!res.ok) throw new Error("Failed to load intelligence");
            const data = await res.json();
            console.log("Intelligence RAW payload:", data); // DEBUG
            items = Array.isArray(data)
                ? data.filter((i) => i && i.metadata)
                : [];
            console.log("Intelligence Items count:", items.length); // DEBUG
        } catch (e) {
            console.error("Error loading intelligence:", e);
            error = e.message;
        } finally {
            loading = false;
        }
    }

    async function runScan() {
        try {
            scanning = true;
            await fetch(`${API_BASE}/api/intelligence/scan`, {
                method: "POST",
                body: JSON.stringify({ force: true }),
            });
            await loadData();
        } finally {
            scanning = false;
        }
    }

    onMount(loadData);
</script>

<div class="space-y-6">
    <div class="flex flex-col gap-4 pb-4 border-b border-skin-border">
        <div class="flex items-center justify-between">
            <h2 class="text-xl font-medium text-skin-text tracking-tight">
                Intelligence Feed
            </h2>
            <button
                on:click={runScan}
                disabled={scanning}
                class="bg-skin-card border border-skin-border hover:border-skin-muted text-skin-text px-3 py-1.5 rounded-md text-sm font-medium transition-all disabled:opacity-50 shadow-sm"
            >
                {scanning ? "Scanning..." : "Run Analysis"}
            </button>
        </div>

        <!-- Source Filters -->
        <div class="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
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

    {#if error}
        <div
            class="p-4 bg-skin-neg/10 border border-skin-neg/20 text-skin-neg rounded-md text-sm text-center"
        >
            {error}
        </div>
    {:else if loading}
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
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {#each filteredItems as item}
                <div
                    class="bg-skin-card backdrop-blur-md border border-skin-border rounded-lg p-4 hover:border-skin-muted/50 transition-colors group flex flex-col h-full {item
                        .metadata.strategy || 'noise'}"
                >
                    <!-- Header -->
                    <div class="flex justify-between items-start mb-2 gap-3">
                        <a
                            href={item.metadata.link}
                            target="_blank"
                            class="font-medium text-skin-text leading-snug hover:text-skin-accent transition-colors line-clamp-2 text-sm"
                        >
                            {item.metadata.title}
                        </a>
                        {#if item.metadata.link.includes("youtube")}
                            <span
                                class="bg-skin-neg/10 text-skin-neg text-[10px] font-medium px-1.5 py-0.5 rounded flex shrink-0"
                                >Video</span
                            >
                        {/if}
                    </div>

                    <!-- Context -->
                    <div class="text-[11px] text-skin-muted mb-3 flex gap-2">
                        <span>{item.metadata.source}</span>
                        <span>•</span>
                        <span
                            >{item.metadata.published_at
                                ? item.metadata.published_at.substring(0, 10)
                                : ""}</span
                        >
                    </div>

                    <!-- Scores -->
                    <div class="flex gap-2 mb-3">
                        <div
                            class="flex items-center gap-1 px-1.5 py-0.5 rounded border border-skin-border text-skin-muted text-[10px] font-mono"
                        >
                            <Shield size={10} />
                            R:{item.metadata.relevance_score || 0}
                        </div>
                        <div
                            class="flex items-center gap-1 px-1.5 py-0.5 rounded border border-skin-border text-skin-muted text-[10px] font-mono"
                        >
                            <Globe size={10} />
                            M:{item.metadata.magnitude_score || 0}
                        </div>
                    </div>

                    <!-- Reason -->
                    <div
                        class="text-xs text-skin-muted/80 line-clamp-3 flex-1 mb-3 leading-relaxed"
                    >
                        {item.metadata.relevance_reason ||
                            item.metadata.magnitude_reason}
                    </div>

                    <!-- Tags -->
                    <div
                        class="flex flex-wrap gap-1.5 mt-auto pt-3 border-t border-skin-border"
                    >
                        {#each (item.metadata.tags || []).slice(0, 3) as tag}
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
</style>
