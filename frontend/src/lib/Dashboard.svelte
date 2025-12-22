<script>
    import { onMount, tick } from "svelte";
    import Chart from "chart.js/auto";
    import { themeState } from "./stores/theme.js";
    import { BarChart3, PieChart } from "lucide-svelte";

    export let refreshTrigger = 0;

    let data = null;
    let error = null;
    let chartInstance = null;
    let assetChartInstance = null;

    // Chart Preference State
    let chartType = "doughnut"; // 'doughnut' | 'bar'

    const API_BASE = "http://localhost:8200";

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
                    class="text-2xl font-semibold text-skin-text tracking-tight"
                >
                    €{data.total_value.toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                    })}
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
                        class="text-xs font-medium {data.total_pnl >= 0
                            ? 'text-skin-pos/80'
                            : 'text-skin-neg/80'}"
                    >
                        {data.total_pnl >= 0
                            ? "+"
                            : ""}{data.total_pnl_pct.toFixed(2)}%
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
                    class="p-3 bg-skin-card backdrop-blur-sm border border-skin-border rounded-lg hover:border-skin-accent/50 transition-colors"
                >
                    <div
                        class="text-[10px] font-mono text-skin-muted mb-1 truncate"
                        title={broker}
                    >
                        {broker.replace("_", " ")}
                    </div>
                    <div
                        class="text-lg font-semibold text-skin-text tracking-tight"
                    >
                        €{val.value.toLocaleString(undefined, {
                            maximumFractionDigits: 0,
                        })}
                    </div>
                    <div class="text-xs font-medium text-skin-accent">
                        {((val.value / data.total_value) * 100).toFixed(1)}%
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

        <!-- Holdings Table -->
        <div
            class="border border-skin-border rounded-lg overflow-hidden bg-skin-card backdrop-blur-md"
        >
            <div
                class="px-4 py-3 border-b border-skin-border flex justify-between items-center"
            >
                <h3 class="text-sm font-medium text-skin-text">
                    Holdings Details
                </h3>
                <span class="text-xs text-skin-muted">{data.count} items</span>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-left text-sm">
                    <thead
                        class="bg-skin-base/50 text-skin-muted border-b border-skin-border"
                    >
                        <tr>
                            <th
                                class="px-4 py-2 font-medium text-[11px] uppercase tracking-wider"
                                >Ticker</th
                            >
                            <th
                                class="px-4 py-2 font-medium text-[11px] uppercase tracking-wider"
                                >Broker</th
                            >
                            <th
                                class="px-4 py-2 font-medium text-[11px] uppercase tracking-wider text-right"
                                >Qty</th
                            >
                            <th
                                class="px-4 py-2 font-medium text-[11px] uppercase tracking-wider text-right"
                                >Value</th
                            >
                            <th
                                class="px-4 py-2 font-medium text-[11px] uppercase tracking-wider text-right"
                                >P/L</th
                            >
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-skin-border">
                        {#each data.holdings as h}
                            <tr
                                class="hover:bg-skin-base/30 transition-colors group"
                            >
                                <td class="px-4 py-2 font-medium text-skin-text"
                                    >{h.ticker}</td
                                >
                                <td class="px-4 py-2 text-skin-muted text-xs"
                                    >{h.broker.replace("_", " ")}</td
                                >
                                <td
                                    class="px-4 py-2 text-right font-mono text-skin-muted text-xs"
                                    >{h.quantity.toFixed(4)}</td
                                >
                                <td
                                    class="px-4 py-2 text-right font-mono text-skin-text"
                                    >€{h.current_value.toLocaleString(
                                        undefined,
                                        {
                                            minimumFractionDigits: 2,
                                            maximumFractionDigits: 2,
                                        },
                                    )}</td
                                >
                                <td
                                    class="px-4 py-2 text-right font-mono {h.pnl >=
                                    0
                                        ? 'text-skin-pos'
                                        : 'text-skin-neg'}"
                                >
                                    {h.pnl >= 0 ? "+" : ""}€{h.pnl.toFixed(2)}
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
{/if}
