<script>
    import { onMount } from "svelte";

    let data = null;
    let loading = true;
    let error = null;

    const API_BASE = "";

    async function fetchCorrelation() {
        try {
            loading = true;
            const res = await fetch(`${API_BASE}/api/analytics/correlation`);
            if (!res.ok) throw new Error("Failed to fetch correlation matrix");
            data = await res.json();

            // Check for error in response payload
            if (data.error) throw new Error(data.error);
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    }

    onMount(() => {
        fetchCorrelation();
    });

    function getColor(value) {
        // -1 (Red) -> 0 (White/Gray) -> 1 (Green)
        // Adjust for dark mode aesthetics
        if (value === 1) return "rgba(16, 185, 129, 0.9)"; // Strong Green

        if (value > 0) {
            return `rgba(16, 185, 129, ${value})`; // Green opacity
        } else {
            return `rgba(239, 68, 68, ${Math.abs(value)})`; // Red opacity
        }
    }

    function getTextColor(value) {
        if (Math.abs(value) > 0.5) return "white";
        return "#a1a1aa"; // zinc-400
    }
</script>

<div class="bg-skin-card border border-skin-border rounded-lg p-4 shadow-sm">
    <div class="flex items-center justify-between mb-4">
        <h3 class="text-sm font-medium text-skin-text">
            Asset Correlation Matrix (Top 15)
        </h3>
        <button
            on:click={fetchCorrelation}
            class="text-xs text-skin-muted hover:text-skin-text transition-colors"
        >
            ↻ Refresh
        </button>
    </div>

    {#if loading}
        <div
            class="h-64 flex items-center justify-center text-skin-muted text-xs animate-pulse"
        >
            Calculating correlations...
        </div>
    {:else if error}
        <div
            class="h-64 flex items-center justify-center text-skin-neg text-xs"
        >
            {error}
        </div>
    {:else if !data || !data.tickers || data.tickers.length === 0}
        <div
            class="h-64 flex items-center justify-center text-skin-muted text-xs"
        >
            Not enough data to generate matrix.
        </div>
    {:else}
        <div class="overflow-x-auto">
            <div class="inline-block min-w-full">
                <!-- Grid Container -->
                <div
                    class="grid"
                    style="grid-template-columns: 80px repeat({data.tickers
                        .length}, minmax(40px, 1fr));"
                >
                    <!-- Header Row -->
                    <div class="sticky left-0 bg-skin-card z-10"></div>
                    <!-- Top-Left Corner -->
                    {#each data.tickers as ticker}
                        <div
                            class="p-2 text-[10px] font-bold text-center text-skin-muted truncate"
                            title={ticker}
                        >
                            {ticker}
                        </div>
                    {/each}

                    <!-- Data Rows -->
                    {#each data.tickers as rowTicker, rIdx}
                        <!-- Row Label -->
                        <div
                            class="sticky left-0 bg-skin-card z-10 p-2 text-[10px] font-bold text-skin-muted flex items-center truncate"
                            title={rowTicker}
                        >
                            {rowTicker}
                        </div>

                        <!-- Cells -->
                        {#each data.matrix[rIdx] as value, cIdx}
                            <div
                                class="aspect-square flex items-center justify-center text-[9px] font-medium transition-transform hover:scale-110 hover:z-20 border border-skin-card/10 cursor-default"
                                style="background-color: {getColor(
                                    value,
                                )}; color: {getTextColor(value)};"
                                title="{rowTicker} vs {data.tickers[
                                    cIdx
                                ]}: {value}"
                            >
                                {value.toFixed(2)}
                            </div>
                        {/each}
                    {/each}
                </div>
            </div>
        </div>
        <div class="mt-2 text-[9px] text-skin-muted text-right">
            Based on 1-year daily returns (Yahoo Finance)
        </div>
    {/if}
</div>
