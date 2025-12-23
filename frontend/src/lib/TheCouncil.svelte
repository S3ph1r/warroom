<script>
    import { onMount } from "svelte";
    import {
        Brain,
        Scroll,
        TrendingUp,
        AlertTriangle,
        Globe,
        RefreshCw,
    } from "lucide-svelte";

    let loading = false;
    let opinions = null;
    let error = null;
    let userQuery = "";

    // Track loading state for individual items
    let refreshingItems = {}; // { 'consensus': true, 'google_historian': false }

    // Auto-load session if exists
    onMount(() => {
        callTheCouncil(false); // Default: check cache
    });

    async function callTheCouncil(force = true) {
        loading = true;
        error = null;
        try {
            const res = await fetch(
                "http://localhost:8000/api/council/consult",
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        query: userQuery,
                        force_refresh: force,
                    }),
                },
            );
            if (!res.ok) throw new Error("Council connection failed");
            opinions = await res.json();
            console.log(opinions);
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    }

    async function refreshItem(itemId) {
        refreshingItems[itemId] = true;
        try {
            const res = await fetch(
                "http://localhost:8000/api/council/refresh-item",
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ item_id: itemId }),
                },
            );
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
        class="flex items-center justify-between border-b border-skin-border pb-4"
    >
        <div>
            <h2
                class="text-xl font-medium text-skin-text tracking-tight flex items-center gap-2"
            >
                <Brain class="w-5 h-5 text-purple-400" />
                The Council (Matrix)
            </h2>
            <p class="text-sm text-skin-muted hidden sm:block">
                8-Core Strategic Analysis & Consensus Engine.
            </p>
        </div>

        <div class="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
            <input
                type="text"
                bind:value={userQuery}
                placeholder="Specific question... (Force refresh)"
                class="bg-skin-card border border-skin-border rounded-lg px-3 py-2 text-sm w-full sm:w-64 focus:outline-none focus:border-purple-500/50 transition-all placeholder:text-skin-muted"
            />
            <button
                on:click={() => callTheCouncil(true)}
                disabled={loading}
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
                class="text-lg font-medium text-purple-300 mb-4 flex items-center gap-2"
            >
                <Brain class="w-5 h-5" />
                President's Consensus
            </h3>

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
                    {#each Object.entries(consensus.scores) as [model, score]}
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
            <div class="mt-2 text-xs text-skin-muted text-right">
                Session: {new Date(opinions.timestamp).toLocaleString()}
                {#if opinions.from_cache}(Cached){/if}
            </div>
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
    {:else if !loading}
        <div
            class="text-center py-12 text-skin-muted bg-skin-card/50 rounded-xl border border-dashed border-skin-border"
        >
            <Brain class="w-12 h-12 mx-auto mb-3 opacity-20" />
            <p>The Council is waiting to be summoned.</p>
        </div>
    {/if}
</div>
