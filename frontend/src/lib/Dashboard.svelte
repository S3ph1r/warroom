<script>
    import { onMount, tick } from "svelte";
    import Chart from "chart.js/auto";
    import { themeState } from "./stores/theme.js";
    import { BarChart3, PieChart } from "lucide-svelte";
    import AssetTable from "./components/AssetTable.svelte";

    export let refreshTrigger = 0;

    let data = null;
    let error = null;
    let chartInstance = null;
    let assetChartInstance = null;

    // Chart Preference State
    let chartType = "doughnut"; // 'doughnut' | 'bar'
    let selectedBroker = "All";

    const API_BASE = "http://localhost:8000";

    async function fetchData() {
        try {
            error = null;
            const res = await fetch(`${API_BASE}/api/portfolio`);
            if (!res.ok) throw new Error("Failed to fetch portfolio");
            data = await res.json();

            await tick();
            renderCharts();
        } catch (e) {
            error = e.message;
        }
    }

    function renderCharts() {
        if (!data) return;
        if (chartInstance) chartInstance.destroy();
        if (assetChartInstance) assetChartInstance.destroy();

        // Access colors directly from store for immediate reactivity
        const palette = $themeState;
        const colors = [
            palette["--chart-1"],
            palette["--chart-2"],
            palette["--chart-3"],
            palette["--chart-4"],
            palette["--chart-5"],
        ];

        // Fallbacks for base colors if store isn't fully ready (rare) or for static vals
        const labelColor = palette["--text-muted"] || "#8a8f98";
        const borderColor = palette["--bg-card"] || "#141517";

        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            layout: { padding: 20 },
            cutout: chartType === "doughnut" ? "65%" : 0, // Thicker doughnut
            indexAxis: chartType === "bar" ? "y" : "x",
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: "rgba(10,10,10,0.9)",
                    bodyColor: "#ededef",
                    borderColor: "rgba(255,255,255,0.1)",
                    borderWidth: 1,
                    padding: 10,
                    displayColors: true,
                    callbacks: {
                        label: (ctx) =>
                            ` ${ctx.label}: €${ctx.raw.toLocaleString()}`,
                    },
                },
            },
            elements: {
                arc: {
                    borderWidth: 0,
                    hoverOffset: 25, // Explode effect
                    shadowBlur: 10, // Shadow effect (requires custom plugin or compatible context, often ignored by standard Chart.js but harmless)
                    shadowColor: "rgba(0,0,0,0.5)",
                },
                bar: {
                    borderRadius: 4,
                    borderSkipped: false,
                },
            },
            animation: {
                animateScale: true,
                animateRotate: true,
            },
            scales:
                chartType === "bar"
                    ? {
                          y: {
                              ticks: { color: labelColor },
                              grid: { color: borderColor },
                          },
                          x: {
                              ticks: { color: labelColor },
                              grid: { display: false },
                          },
                      }
                    : {},
        };

        // Custom Plugin for Center Text (Doughnut only)
        const centerTextPlugin = {
            id: "centerText",
            beforeDraw: function (chart) {
                if (chart.config.type !== "doughnut") return;
                var width = chart.width,
                    height = chart.height,
                    ctx = chart.ctx;

                ctx.restore();
                var fontSize = (height / 160).toFixed(2);
                ctx.font = "bold " + fontSize + "em sans-serif";
                ctx.textBaseline = "middle";
                const colorVar = getComputedStyle(document.documentElement)
                    .getPropertyValue("--text-main")
                    .trim();
                ctx.fillStyle = colorVar || "#ffffff";

                var text = "€" + (data.total_value / 1000).toFixed(1) + "k",
                    textX = Math.round(
                        (width - ctx.measureText(text).width) / 2,
                    ),
                    textY = height / 2;

                ctx.fillText(text, textX, textY);
                ctx.save();
            },
        };

        // Register plugin locally if possible or just use in options?
        // Svelte-chartjs might need global registration, but we can pass plugins array.
        const plugins = [centerTextPlugin];

        const ctx = document.getElementById("brokerChart");
        if (ctx) {
            const brokers = Object.keys(data.broker_totals);
            const values = Object.values(data.broker_totals).map(
                (b) => b.value,
            );

            chartInstance = new Chart(ctx, {
                type: chartType,
                plugins: plugins,
                data: {
                    labels: brokers,
                    datasets: [
                        {
                            label: "Value",
                            data: values,
                            backgroundColor: colors,
                            borderColor: borderColor,
                            borderWidth: 2,
                            barThickness: 20,
                        },
                    ],
                },
                options: commonOptions,
            });
        }

        const ctx2 = document.getElementById("assetChart");
        if (ctx2) {
            const assets = Object.keys(data.asset_totals);
            const values = Object.values(data.asset_totals);

            assetChartInstance = new Chart(ctx2, {
                type: chartType,
                plugins: plugins,
                data: {
                    labels: assets,
                    datasets: [
                        {
                            label: "Value",
                            data: values,
                            backgroundColor: colors,
                            borderColor: borderColor,
                            borderWidth: 2,
                            barThickness: 20,
                        },
                    ],
                },
                options: commonOptions,
            });
        }
    }

    // Re-render charts when theme changes to update border colors
    $: if ($themeState && data) {
        renderCharts();
    }

    // React to chart type toggle
    $: if (chartType && data) {
        renderCharts();
    }

    $: if (refreshTrigger) fetchData();
    onMount(fetchData);

    // Grouping Logic for AssetTable keys
    $: filteredHoldings = data
        ? selectedBroker === "All"
            ? data.holdings
            : data.holdings.filter((h) => h.broker === selectedBroker)
        : [];

    $: groups = {
        stocks: filteredHoldings.filter((h) => h.asset_type === "STOCK"),
        etfs: filteredHoldings.filter((h) => h.asset_type === "ETF"),
        bonds: filteredHoldings.filter((h) => h.asset_type === "BOND"),
        crypto: filteredHoldings.filter((h) => h.asset_type === "CRYPTO"),
        commodities: filteredHoldings.filter(
            (h) => h.asset_type === "COMMODITY",
        ),
        cash: filteredHoldings.filter((h) => h.asset_type === "CASH"),
    };
</script>

{#if error}
    <div
        class="p-4 bg-skin-neg/10 border border-skin-neg/20 text-skin-neg rounded-md text-sm"
    >
        Error: {error}
    </div>
{:else if !data}
    <div
        class="animate-pulse flex items-center justify-center h-64 text-skin-muted text-sm font-medium"
    >
        Loading Data...
    </div>
{:else}
    <div class="space-y-6 animate-in fade-in duration-300">
        <!-- Header -->
        <div
            class="flex items-center justify-between pb-4 border-b border-skin-border"
        >
            <h1 class="text-xl font-medium text-skin-text tracking-tight">
                Portfolio Overview
            </h1>
            <div class="flex items-center gap-4">
                <div
                    class="flex items-center gap-2 text-xs text-skin-muted bg-skin-card px-2 py-1 rounded border border-skin-border"
                >
                    <div
                        class="w-1.5 h-1.5 rounded-full bg-skin-pos animate-pulse"
                    ></div>
                    Live
                </div>
            </div>
        </div>

        <!-- KPIs Grid -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <!-- Total Value -->
            <div
                class="p-4 bg-skin-card backdrop-blur-md border border-skin-border rounded-lg shadow-sm hover:border-skin-muted/50 transition-colors"
            >
                <div
                    class="text-[11px] font-medium text-skin-muted uppercase tracking-wider mb-1"
                >
                    Total Value
                </div>
                <div
                    class="text-2xl font-semibold text-skin-text tracking-tight mb-2"
                >
                    €{data.total_value.toLocaleString(undefined, {
                        minimumFractionDigits: 0,
                        maximumFractionDigits: 0,
                    })}
                </div>
                <!-- Mini P&L info -->
                <div class="flex items-center gap-3 text-xs font-medium">
                    <div
                        class={(data.total_day_pl || 0) >= 0
                            ? "text-skin-pos"
                            : "text-skin-neg"}
                    >
                        1D: {(data.total_day_change_pct || 0) >= 0 ? "+" : ""}{(
                            data.total_day_change_pct || 0
                        ).toFixed(2)}%
                    </div>
                    <div
                        class={(data.total_pnl || 0) >= 0
                            ? "text-skin-pos"
                            : "text-skin-neg"}
                    >
                        Net: {(data.total_pnl_pct || 0) >= 0 ? "+" : ""}{(
                            data.total_pnl_pct || 0
                        ).toFixed(2)}%
                    </div>
                </div>
            </div>

            <!-- Total P/L -->
            <div
                class="p-4 bg-skin-card backdrop-blur-md border border-skin-border rounded-lg shadow-sm hover:border-skin-muted/50 transition-colors"
            >
                <div
                    class="text-[11px] font-medium text-skin-muted uppercase tracking-wider mb-1"
                >
                    Total P/L
                </div>
                <div class="flex items-baseline gap-2">
                    <div
                        class="text-2xl font-semibold tracking-tight {data.total_pnl >=
                        0
                            ? 'text-skin-pos'
                            : 'text-skin-neg'}"
                    >
                        {data.total_pnl >= 0 ? "+" : ""}€{Math.abs(
                            data.total_pnl,
                        ).toLocaleString(undefined, {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                        })}
                    </div>
                    <span
                        class={(data.total_pnl || 0) >= 0
                            ? "text-skin-pos/80"
                            : "text-skin-neg/80"}
                    >
                        {(data.total_pnl || 0) >= 0 ? "+" : ""}{(
                            data.total_pnl_pct || 0
                        ).toFixed(2)}%
                    </span>
                </div>
            </div>

            <!-- Holdings Count -->
            <div
                class="p-4 bg-skin-card backdrop-blur-md border border-skin-border rounded-lg shadow-sm hover:border-skin-muted/50 transition-colors"
            >
                <div
                    class="text-[11px] font-medium text-skin-muted uppercase tracking-wider mb-1"
                >
                    Holdings
                </div>
                <div
                    class="text-2xl font-semibold text-skin-text tracking-tight"
                >
                    {data.count}
                </div>
            </div>

            <!-- Brokers Count -->
            <div
                class="p-4 bg-skin-card backdrop-blur-md border border-skin-border rounded-lg shadow-sm hover:border-skin-muted/50 transition-colors"
            >
                <div
                    class="text-[11px] font-medium text-skin-muted uppercase tracking-wider mb-1"
                >
                    Brokers
                </div>
                <div
                    class="text-2xl font-semibold text-skin-text tracking-tight"
                >
                    {Object.keys(data.broker_totals).length}
                </div>
            </div>
        </div>

        <!-- Broker Breakdown Tiles -->
        <h2
            class="text-sm font-medium text-skin-muted uppercase tracking-wider"
        >
            Allocation by Broker
        </h2>
        <!-- Tiles Loop -->
        <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {#each Object.entries(data.broker_totals).sort((a, b) => b[1].value - a[1].value) as [broker, val]}
                <div
                    class="p-3 bg-skin-card backdrop-blur-sm border border-skin-border rounded-lg {selectedBroker ===
                    broker
                        ? 'border-skin-accent ring-1 ring-skin-accent/20'
                        : 'hover:border-skin-accent/50'} transition-all cursor-pointer"
                    on:click={() => (selectedBroker = broker)}
                >
                    <div
                        class="text-[10px] font-mono text-skin-muted mb-1 truncate"
                        title={broker}
                    >
                        {broker.replace("_", " ")}
                    </div>
                    <div class="flex items-end justify-between gap-2">
                        <div
                            class="text-lg font-semibold text-skin-text tracking-tight leading-none"
                        >
                            €{val.value.toLocaleString(undefined, {
                                maximumFractionDigits: 0,
                            })}
                        </div>
                        <!-- Mini P&L Metrics next to total -->
                        <div class="flex flex-col text-right leading-tight">
                            <div
                                class="text-[9px] font-bold {(val.day_change_pct ||
                                    0) >= 0
                                    ? 'text-skin-pos'
                                    : 'text-skin-neg'}"
                            >
                                {(val.day_change_pct || 0) >= 0 ? "+" : ""}{(
                                    val.day_change_pct || 0
                                ).toFixed(1)}%
                            </div>
                            <div
                                class="text-[9px] font-bold {(val.pnl_pct ||
                                    0) >= 0
                                    ? 'text-skin-pos'
                                    : 'text-skin-neg'}"
                            >
                                {(val.pnl_pct || 0) >= 0 ? "+" : ""}{(
                                    val.pnl_pct || 0
                                ).toFixed(1)}%
                            </div>
                        </div>
                    </div>
                    <!-- Allocation % below -->
                    <div
                        class="text-[10px] text-skin-muted/70 mt-1.5 font-medium"
                    >
                        {((val.value / data.total_value) * 100).toFixed(1)}% of
                        total
                    </div>
                </div>
            {/each}
        </div>

        <!-- Charts Section -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div
                class="p-4 bg-skin-card backdrop-blur-md border border-skin-border rounded-lg"
            >
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-sm font-medium text-skin-text">
                        Allocation by Broker
                    </h3>
                    <div
                        class="flex bg-skin-base/50 p-0.5 rounded-md border border-skin-border"
                    >
                        <button
                            class="p-1 rounded {chartType === 'doughnut'
                                ? 'bg-skin-card shadow-sm text-skin-text'
                                : 'text-skin-muted hover:text-skin-text'}"
                            on:click={() => (chartType = "doughnut")}
                            ><PieChart size={14} /></button
                        >
                        <button
                            class="p-1 rounded {chartType === 'bar'
                                ? 'bg-skin-card shadow-sm text-skin-text'
                                : 'text-skin-muted hover:text-skin-text'}"
                            on:click={() => (chartType = "bar")}
                            ><BarChart3 size={14} /></button
                        >
                    </div>
                </div>
                <div class="h-64 w-full flex justify-center">
                    <canvas id="brokerChart"></canvas>
                </div>
            </div>
            <div
                class="p-4 bg-skin-card backdrop-blur-md border border-skin-border rounded-lg"
            >
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-sm font-medium text-skin-text">
                        Allocation by Asset
                    </h3>
                    <div
                        class="flex bg-skin-base/50 p-0.5 rounded-md border border-skin-border"
                    >
                        <button
                            class="p-1 rounded {chartType === 'doughnut'
                                ? 'bg-skin-card shadow-sm text-skin-text'
                                : 'text-skin-muted hover:text-skin-text'}"
                            on:click={() => (chartType = "doughnut")}
                            ><PieChart size={14} /></button
                        >
                        <button
                            class="p-1 rounded {chartType === 'bar'
                                ? 'bg-skin-card shadow-sm text-skin-text'
                                : 'text-skin-muted hover:text-skin-text'}"
                            on:click={() => (chartType = "bar")}
                            ><BarChart3 size={14} /></button
                        >
                    </div>
                </div>
                <div class="h-64 w-full flex justify-center">
                    <canvas id="assetChart"></canvas>
                </div>
            </div>
        </div>

        <!-- HOLDINGS GRID (6 TILES) -->
        <div class="flex items-center justify-between mt-8 mb-2">
            <h2
                class="text-sm font-medium text-skin-muted uppercase tracking-wider"
            >
                Portfolio Holdings
            </h2>

            <!-- BROKER FILTER BAR -->
            <div
                class="flex items-center gap-1 bg-skin-base/30 p-1 rounded-md border border-skin-border"
            >
                <button
                    class="px-2 py-1 text-[11px] font-medium rounded {selectedBroker ===
                    'All'
                        ? 'bg-skin-card text-skin-text shadow-sm'
                        : 'text-skin-muted hover:text-skin-text'}"
                    on:click={() => (selectedBroker = "All")}
                >
                    All
                </button>
                {#each Object.keys(data.broker_totals).sort() as broker}
                    <button
                        class="px-2 py-1 text-[11px] font-medium rounded {selectedBroker ===
                        broker
                            ? 'bg-skin-card text-skin-text shadow-sm'
                            : 'text-skin-muted hover:text-skin-text'}"
                        on:click={() => (selectedBroker = broker)}
                    >
                        {broker.replace("_", " ")}
                    </button>
                {/each}
            </div>
        </div>

        <div class="grid grid-cols-1 gap-6">
            <AssetTable
                title="Stocks"
                items={groups.stocks}
                color="text-skin-accent"
            />
            <AssetTable
                title="ETFs"
                items={groups.etfs}
                color="text-skin-pos"
            />
            <AssetTable
                title="Bonds"
                items={groups.bonds}
                color="text-yellow-400"
            />
            <AssetTable
                title="Crypto"
                items={groups.crypto}
                color="text-purple-400"
            />
            <AssetTable
                title="Commodities"
                items={groups.commodities}
                color="text-orange-400"
            />
            <AssetTable
                title="Cash"
                items={groups.cash}
                color="text-skin-muted"
            />
        </div>
    </div>
{/if}
