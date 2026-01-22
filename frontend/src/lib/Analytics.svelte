<script>
    import { onMount, onDestroy } from "svelte";
    import {
        BarChart3,
        TrendingUp,
        TrendingDown,
        Activity,
        RefreshCw,
        Calendar,
    } from "lucide-svelte";
    import Chart from "chart.js/auto";
    import CorrelationHeatmap from "./components/CorrelationHeatmap.svelte";
    import AllocationTreemap from "./components/AllocationTreemap.svelte";

    const API_BASE = "";

    let portfolioHistory = [];
    let benchmarks = {};
    let riskMetrics = null;
    let latestSnapshot = null;
    let loading = true;
    let error = null;
    let chartInstance = null;
    let chartCanvas;

    let investedHistory = [];
    let investedChartInstance = null;
    let investedChartCanvas;

    // UI State
    let daysRange = 30;
    let showSP500 = true;
    let showNASDAQ = false;
    let showMSCI = false;

    async function loadAnalytics() {
        loading = true;
        error = null;
        try {
            const [historyRes, benchRes, riskRes, latestRes, investedRes] =
                await Promise.all([
                    fetch(
                        `${API_BASE}/api/analytics/history?days=${daysRange}`,
                    ),
                    fetch(
                        `${API_BASE}/api/analytics/benchmarks?days=${daysRange}`,
                    ),
                    fetch(`${API_BASE}/api/analytics/risk-metrics`),
                    fetch(`${API_BASE}/api/analytics/latest`),
                    fetch(`${API_BASE}/api/analytics/invested-history`),
                ]);

            portfolioHistory = await historyRes.json();
            benchmarks = await benchRes.json();
            riskMetrics = await riskRes.json();
            latestSnapshot = await latestRes.json();
            investedHistory = await investedRes.json();

            renderChart();
            renderInvestedChart();
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    }

    async function saveSnapshot() {
        try {
            const res = await fetch(`${API_BASE}/api/analytics/snapshot`, {
                method: "POST",
            });
            const data = await res.json();
            if (data.status === "saved") {
                await loadAnalytics();
            }
        } catch (e) {
            error = e.message;
        }
    }

    function renderChart() {
        if (!chartCanvas) return;
        if (chartInstance) chartInstance.destroy();

        const datasets = [];

        // Portfolio line
        if (portfolioHistory.length > 0) {
            const firstValue = portfolioHistory[0]?.value || 1;
            datasets.push({
                label: "Portfolio",
                data: portfolioHistory.map((p) => ({
                    x: p.date,
                    y: (p.value / firstValue - 1) * 100,
                })),
                borderColor: "rgb(99, 102, 241)",
                backgroundColor: "rgba(99, 102, 241, 0.1)",
                borderWidth: 2,
                fill: true,
                tension: 0.3,
            });
        }

        // Benchmarks
        const benchmarkColors = {
            SP500: { border: "rgb(234, 179, 8)", bg: "rgba(234, 179, 8, 0.1)" },
            NASDAQ100: {
                border: "rgb(34, 197, 94)",
                bg: "rgba(34, 197, 94, 0.1)",
            },
            MSCI_WORLD: {
                border: "rgb(168, 85, 247)",
                bg: "rgba(168, 85, 247, 0.1)",
            },
        };

        if (showSP500 && benchmarks.SP500) {
            datasets.push({
                label: "S&P 500",
                data: benchmarks.SP500.map((b) => ({
                    x: b.date,
                    y: b.pct_change,
                })),
                borderColor: benchmarkColors.SP500.border,
                borderWidth: 1.5,
                borderDash: [5, 5],
                fill: false,
                tension: 0.3,
            });
        }

        if (showNASDAQ && benchmarks.NASDAQ100) {
            datasets.push({
                label: "NASDAQ 100",
                data: benchmarks.NASDAQ100.map((b) => ({
                    x: b.date,
                    y: b.pct_change,
                })),
                borderColor: benchmarkColors.NASDAQ100.border,
                borderWidth: 1.5,
                borderDash: [5, 5],
                fill: false,
                tension: 0.3,
            });
        }

        if (showMSCI && benchmarks.MSCI_WORLD) {
            datasets.push({
                label: "MSCI World",
                data: benchmarks.MSCI_WORLD.map((b) => ({
                    x: b.date,
                    y: b.pct_change,
                })),
                borderColor: benchmarkColors.MSCI_WORLD.border,
                borderWidth: 1.5,
                borderDash: [5, 5],
                fill: false,
                tension: 0.3,
            });
        }

        chartInstance = new Chart(chartCanvas, {
            type: "line",
            data: { datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { intersect: false, mode: "index" },
                plugins: {
                    legend: {
                        display: true,
                        labels: {
                            color: "rgba(255,255,255,0.7)",
                            font: { size: 11 },
                        },
                    },
                    tooltip: {
                        callbacks: {
                            label: (ctx) =>
                                `${ctx.dataset.label}: ${ctx.parsed.y?.toFixed(2)}%`,
                        },
                    },
                },
                scales: {
                    x: {
                        type: "category",
                        ticks: {
                            color: "rgba(255,255,255,0.5)",
                            maxTicksLimit: 8,
                        },
                        grid: { color: "rgba(255,255,255,0.05)" },
                    },
                    y: {
                        ticks: {
                            color: "rgba(255,255,255,0.5)",
                            callback: (v) => `${v}%`,
                        },
                        grid: { color: "rgba(255,255,255,0.05)" },
                    },
                },
            },
        });
    }

    function renderInvestedChart() {
        if (!investedChartCanvas) return;
        if (investedChartInstance) investedChartInstance.destroy();

        // 1. Prepare Data
        // X-Axis: All dates from invested history
        // Invested Line: The cumulative values

        // Optimize: If history is huge (>100 points), dampen it?
        // Chart.js handles it okay, but let's see.

        const labels = investedHistory.map((d) => d.date);
        const dataInvested = investedHistory.map((d) => d.invested);

        // Portfolio Value logic:
        // We only have snapshots for recent days.
        // We can try to align them.
        // Create a map of Date -> Value from portfolioHistory
        const valueMap = {};
        portfolioHistory.forEach((p) => {
            valueMap[p.date] = p.value;
        });

        const dataValue = labels.map((d) => valueMap[d] || null); // Null for missing points

        investedChartInstance = new Chart(investedChartCanvas, {
            type: "line",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Net Invested Capital",
                        data: dataInvested,
                        borderColor: "rgba(255, 99, 132, 0.8)",
                        backgroundColor: "rgba(255, 99, 132, 0.1)",
                        borderWidth: 2,
                        borderDash: [5, 5],
                        fill: false,
                        pointRadius: 0,
                        tension: 0.1,
                    },
                    {
                        label: "Portfolio Value",
                        data: dataValue,
                        borderColor: "rgba(75, 192, 192, 1)",
                        backgroundColor: "rgba(75, 192, 192, 0.2)",
                        borderWidth: 2,
                        fill: true,
                        pointRadius: 3,
                        tension: 0.2,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { intersect: false, mode: "index" },
                plugins: {
                    legend: {
                        labels: { color: "rgba(255,255,255,0.7)" },
                    },
                    tooltip: {
                        callbacks: {
                            label: (ctx) =>
                                `${ctx.dataset.label}: €${ctx.parsed.y.toLocaleString()}`,
                        },
                    },
                },
                scales: {
                    x: {
                        display: true, // Hide x labels if too many?
                        ticks: {
                            color: "rgba(255,255,255,0.5)",
                            maxTicksLimit: 10,
                        },
                        grid: { color: "rgba(255,255,255,0.05)" },
                    },
                    y: {
                        ticks: { color: "rgba(255,255,255,0.5)" },
                        grid: { color: "rgba(255,255,255,0.05)" },
                    },
                },
            },
        });
    }

    function safeLoad() {
        if (!loading && chartCanvas) {
            loadAnalytics();
        }
    }

    // Trigger update when parameters change (but don't react to 'loading' changes)
    $: {
        daysRange;
        showSP500;
        showNASDAQ;
        showMSCI;
        safeLoad();
    }

    onMount(loadAnalytics);
    onDestroy(() => {
        if (chartInstance) chartInstance.destroy();
        if (investedChartInstance) investedChartInstance.destroy();
    });
</script>

<div class="space-y-6">
    <!-- Header -->
    <div
        class="flex items-center justify-between pb-4 border-b border-skin-border"
    >
        <div class="flex items-center gap-3">
            <BarChart3 size={24} class="text-skin-accent" />
            <h1 class="text-xl font-semibold text-skin-text">
                Analytics & Performance
            </h1>
        </div>
        <div class="flex items-center gap-2">
            <button
                on:click={saveSnapshot}
                class="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-skin-card border border-skin-border rounded hover:border-skin-accent transition-colors"
            >
                <Calendar size={14} />
                Save Snapshot
            </button>
            <button
                on:click={loadAnalytics}
                class="p-2 text-skin-muted hover:text-skin-text hover:bg-skin-card rounded transition-colors"
            >
                <RefreshCw size={16} />
            </button>
        </div>
    </div>

    <!-- Error Message -->
    {#if error}
        <div
            class="p-3 bg-skin-neg/10 border border-skin-neg/20 text-skin-neg rounded text-sm"
        >
            {error}
        </div>
    {/if}

    <!-- Risk Metrics Cards -->
    <div class="grid grid-cols-4 gap-4">
        <div class="p-4 bg-skin-card border border-skin-border rounded-lg">
            <div class="text-xs text-skin-muted uppercase mb-1">Net Worth</div>
            <div class="text-2xl font-bold text-skin-text">
                {#if latestSnapshot?.total_value}
                    €{latestSnapshot.total_value.toLocaleString("de-DE", {
                        minimumFractionDigits: 0,
                    })}
                {:else}
                    --
                {/if}
            </div>
            <div class="text-xs text-skin-muted mt-1">
                {latestSnapshot?.date || "No snapshot"}
            </div>
        </div>

        <div class="p-4 bg-skin-card border border-skin-border rounded-lg">
            <div class="text-xs text-skin-muted uppercase mb-1">
                Sharpe Ratio
            </div>
            <div
                class="text-2xl font-bold {riskMetrics?.sharpe_ratio > 0
                    ? 'text-skin-pos'
                    : 'text-skin-neg'}"
            >
                {riskMetrics?.sharpe_ratio ?? "--"}
            </div>
            <div class="text-xs text-skin-muted mt-1">Risk-adjusted return</div>
        </div>

        <div class="p-4 bg-skin-card border border-skin-border rounded-lg">
            <div class="text-xs text-skin-muted uppercase mb-1">Volatility</div>
            <div class="text-2xl font-bold text-skin-text">
                {riskMetrics?.volatility ? `${riskMetrics.volatility}%` : "--"}
            </div>
            <div class="text-xs text-skin-muted mt-1">Annualized</div>
        </div>

        <div class="p-4 bg-skin-card border border-skin-border rounded-lg">
            <div class="text-xs text-skin-muted uppercase mb-1">
                Max Drawdown
            </div>
            <div class="text-2xl font-bold text-skin-neg">
                {riskMetrics?.max_drawdown
                    ? `-${riskMetrics.max_drawdown}%`
                    : "--"}
            </div>
            <div class="text-xs text-skin-muted mt-1">Peak to trough</div>
        </div>
    </div>

    <!-- Chart Controls -->
    <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
            <span class="text-xs text-skin-muted uppercase">Period:</span>
            {#each [7, 30, 90, 365] as days}
                <button
                    on:click={() => (daysRange = days)}
                    class="px-3 py-1 text-xs rounded {daysRange === days
                        ? 'bg-skin-accent text-white'
                        : 'bg-skin-card border border-skin-border text-skin-muted hover:text-skin-text'}"
                >
                    {days === 365 ? "1Y" : `${days}D`}
                </button>
            {/each}
        </div>

        <div class="flex items-center gap-3">
            <span class="text-xs text-skin-muted uppercase">Benchmarks:</span>
            <label
                class="flex items-center gap-1.5 text-xs text-skin-muted cursor-pointer"
            >
                <input
                    type="checkbox"
                    bind:checked={showSP500}
                    class="accent-yellow-500"
                />
                S&P 500
            </label>
            <label
                class="flex items-center gap-1.5 text-xs text-skin-muted cursor-pointer"
            >
                <input
                    type="checkbox"
                    bind:checked={showNASDAQ}
                    class="accent-green-500"
                />
                NASDAQ
            </label>
            <label
                class="flex items-center gap-1.5 text-xs text-skin-muted cursor-pointer"
            >
                <input
                    type="checkbox"
                    bind:checked={showMSCI}
                    class="accent-purple-500"
                />
                MSCI World
            </label>
        </div>
    </div>

    <!-- NEW: Invested vs Value Chart (Full Width) -->
    <div class="p-4 bg-skin-card border border-skin-border rounded-lg mt-6">
        <h3 class="text-sm font-medium text-skin-text mb-4">
            Capital Growth (Invested vs Value)
        </h3>
        <div class="h-80">
            <canvas bind:this={investedChartCanvas}></canvas>
        </div>
    </div>

    <!-- Performance Chart -->
    <div class="p-4 bg-skin-card border border-skin-border rounded-lg mt-6">
        <h3 class="text-sm font-medium text-skin-text mb-4">
            Recent Performance vs Benchmarks
        </h3>
        {#if loading}
            <div class="h-80 flex items-center justify-center text-skin-muted">
                Loading chart data...
            </div>
        {:else if portfolioHistory.length === 0}
            <div
                class="h-80 flex flex-col items-center justify-center text-skin-muted"
            >
                <Activity size={40} class="mb-3 opacity-50" />
                <p>No recent history yet</p>
                <p class="text-xs mt-1">Snapshot required</p>
            </div>
        {:else}
            <div class="h-80">
                <canvas bind:this={chartCanvas}></canvas>
            </div>
        {/if}
    </div>

    <!-- Data Info -->
    {#if riskMetrics?.data_points}
        <div class="text-xs text-skin-muted text-center">
            Based on {riskMetrics.data_points} data points over {riskMetrics.period_days}
            days
        </div>
    {/if}

    <!-- Advanced Analytics Grid -->
    <div
        class="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-4 border-t border-skin-border mt-6"
    >
        <!-- Correlation Heatmap -->
        <CorrelationHeatmap />

        <!-- Allocation Treemap -->
        <AllocationTreemap />
    </div>
</div>
