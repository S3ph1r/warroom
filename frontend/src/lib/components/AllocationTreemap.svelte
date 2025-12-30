<script>
    import { onMount } from "svelte";
    import Chart from "chart.js/auto";
    import { TreemapController, TreemapElement } from "chartjs-chart-treemap";

    // Register Treemap components
    Chart.register(TreemapController, TreemapElement);

    let chartCanvas;
    let chartInstance = null;
    let loading = true;
    let error = null;

    const API_BASE = "";

    // Color palette for Brokers
    const baseColors = [
        "#3b82f6", // Blue
        "#10b981", // Emerald
        "#8b5cf6", // Violet
        "#f59e0b", // Amber
        "#ec4899", // Pink
        "#6366f1", // Indigo
    ];

    function colorFromContext(ctx) {
        if (ctx.type !== "data") return "transparent";
        const item = ctx.raw;
        // Assign color based on top-level group (Broker) index
        // We need to find the unique index of the broker
        // Or simpler: hash the name string to an index

        let label = "";
        // Level 0: Root, Level 1: Broker, Level 2: Type, Level 3: Ticker
        // chartjs-chart-treemap groups: ['broker', 'asset_type', 'ticker']

        // If leaf node (ticker)
        if (item.l === 2) {
            // 0-based depth? Usually l is depth
            // Use parent's color (Asset Type)
            return "#1e293b"; // Dark for leaves, or use opacity
        }

        // Use a simple hash for consistent colors
        const str = item.g || item.v?.ticker || "";
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            hash = str.charCodeAt(i) + ((hash << 5) - hash);
        }
        const c = baseColors[Math.abs(hash) % baseColors.length];

        // Adjust opacity based on value/depth
        return c;
    }

    async function fetchData() {
        try {
            const res = await fetch(`${API_BASE}/api/portfolio`);
            if (!res.ok) throw new Error("Failed to fetch holdings");
            const rawData = await res.json();
            const holdings = rawData.holdings;

            // Format for Treemap
            // We need a flat array of objects
            // [ { broker: 'IBKR', asset_type: 'STOCK', ticker: 'AAPL', value: 1500 }, ... ]

            renderChart(holdings);
            loading = false;
        } catch (e) {
            error = e.message;
            loading = false;
        }
    }

    function renderChart(data) {
        if (chartInstance) chartInstance.destroy();

        chartInstance = new Chart(chartCanvas, {
            type: "treemap",
            data: {
                datasets: [
                    {
                        tree: data,
                        key: "current_value",
                        groups: ["broker", "asset_type", "ticker"],
                        backgroundColor: (ctx) => {
                            // Custom color logic
                            if (ctx.type !== "data") return "transparent";
                            // Different alpha for depth
                            const depth =
                                ctx.raw._data.children.length > 0 ? 0.3 : 0.8;

                            // Use broker from the data path if accessible, or simple cycle
                            // Chart.js treemap is tricky with colors. Let's stick to a solid default with opacity.

                            return "rgba(59, 130, 246, 0.6)";
                        },
                        labels: {
                            display: true,
                            formatter: (ctx) => {
                                // Show Ticker + Value for leaves
                                if (!ctx.raw) return "";
                                const item = ctx.raw;
                                // Only show label if box is big enough? handled by chart.js usually
                                let label = item.g; // Group name (Broker, Type, or Ticker)
                                if (!label && item.v) label = item.v.ticker; // Leaf

                                return [label]; // Return array for multiline
                            },
                            color: "white",
                            font: { size: 10, weight: "bold" },
                        },
                        captions: {
                            display: true,
                            color: "rgba(255,255,255,0.5)",
                            font: { size: 12 },
                        },
                        borderWidth: 1,
                        borderColor: "#0f172a", // Dark border
                        spacing: 1,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title: (items) => {
                                const item = items[0].raw;
                                return (
                                    item.g ||
                                    (item.v ? item.v.ticker : "Portfolio")
                                );
                            },
                            label: (item) => {
                                const val = item.raw.v;
                                return `Value: €${parseFloat(val).toLocaleString()}`;
                            },
                        },
                    },
                },
            },
        });
    }

    onMount(() => {
        fetchData();
    });
</script>

<div
    class="bg-skin-card border border-skin-border rounded-lg p-4 shadow-sm h-[400px]"
>
    <h3 class="text-sm font-medium text-skin-text mb-4">
        Portfolio Allocation (Treemap)
    </h3>

    {#if error}
        <div
            class="h-full flex items-center justify-center text-skin-neg text-xs"
        >
            {error}
        </div>
    {:else}
        <div class="relative w-full h-[320px]">
            <canvas bind:this={chartCanvas}></canvas>
        </div>
    {/if}
</div>
