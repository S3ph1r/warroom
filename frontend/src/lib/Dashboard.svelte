<script>
    import { onMount, tick } from "svelte";
    import Chart from "chart.js/auto";
    import { themeState } from "./stores/theme.js";
    import {
        BarChart3,
        PieChart,
        Download,
        FileText,
        Plus,
        Database,
    } from "lucide-svelte";
    import AssetTable from "./components/AssetTable.svelte";
    import TransactionModal from "./components/TransactionModal.svelte";

    export let refreshTrigger = 0;

    let data = null;
    let error = null;
    let chartInstance = null;
    let assetChartInstance = null;

    // Modal State
    let showModal = false;
    let modalMode = "BUY";
    let modalData = null;

    function openNewTransaction() {
        modalMode = "BUY";
        modalData = null;
        showModal = true;
    }

    function handleBuy(event) {
        const holding = event.detail;
        if (holding.asset_type === "CASH") {
            modalMode = "DEPOSIT";
        } else {
            modalMode = "BUY";
        }
        modalData = holding;
        showModal = true;
    }

    function handleSell(event) {
        const holding = event.detail;
        if (holding.asset_type === "CASH") {
            modalMode = "WITHDRAW";
        } else {
            modalMode = "SELL";
        }
        modalData = holding;
        showModal = true;
    }

    async function handleSaveTransaction(event) {
        const { mode, data } = event.detail;
        console.log("Saving Transaction:", mode, data);

        try {
            const payload = {
                mode,
                broker: data.broker,
                ticker:
                    data.ticker ||
                    (["DEPOSIT", "WITHDRAW"].includes(mode)
                        ? data.currency
                        : ""),
                isin: data.isin || "",
                asset_type: data.asset_type || "STOCK",
                quantity: parseFloat(data.quantity),
                price: parseFloat(data.price || 1),
                currency: data.currency,
                date: data.date,
                fees: 0,
            };

            const res = await fetch(`${API_BASE}/api/transactions`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Transaction failed");
            }

            // Success
            showModal = false;
            // Refresh Data to see new Cash/Holdings
            await fetchData();
            // Optional: trigger check alerts
        } catch (e) {
            alert("Error saving transaction: " + e.message);
        }
    }

    // Chart Preference State
    let chartType = "doughnut"; // 'doughnut' | 'bar'
    // Broker Filter State
    let selectedBroker = "All";

    // Currency State
    let selectedCurrency = "EUR";
    $: currencySymbol = selectedCurrency === "USD" ? "$" : "€";
    $: fxRate =
        data && data.fx_rates ? data.fx_rates[selectedCurrency] || 1.0 : 1.0;

    // Derived Display Data (converted by FX Rate)
    $: displayData = convertData(data, fxRate);

    function convertData(sourceData, rate) {
        // ... (convertData logic same as before, no changes needed inside) ...
        if (!sourceData) return null;
        if (rate === 1.0) return sourceData;
        const d = { ...sourceData };
        d.total_value = (sourceData.total_value || 0) * rate;
        d.total_cost = (sourceData.total_cost || 0) * rate;
        d.total_pnl = (sourceData.total_pnl || 0) * rate;
        d.total_day_pl = (sourceData.total_day_pl || 0) * rate;

        d.broker_totals = {};
        for (const [k, v] of Object.entries(sourceData.broker_totals)) {
            d.broker_totals[k] = {
                ...v,
                value: v.value * rate,
                cost: v.cost * rate,
                day_pl: v.day_pl * rate,
            };
        }
        d.asset_totals = {};
        for (const [k, v] of Object.entries(sourceData.asset_totals)) {
            d.asset_totals[k] = v * rate;
        }
        d.holdings = sourceData.holdings.map((h) => ({
            ...h,
            current_value: h.current_value * rate,
            cost_basis: h.cost_basis * rate,
            live_price: (h.live_price || 0) * rate,
            day_pl: h.day_pl * rate,
            pnl: h.pnl * rate,
        }));
        return d;
    }

    const API_BASE = ""; // Use relative path through proxy

    async function fetchData() {
        try {
            error = null;
            const res = await fetch(`${API_BASE}/api/portfolio`);
            if (!res.ok) throw new Error("Failed to fetch portfolio");
            data = await res.json();
            await tick();
            renderCharts();

            // Auto-Poll if stale
            checkStalenessAndPoll();
        } catch (e) {
            error = e.message;
        }
    }

    let pollInterval;
    let autoRefreshInterval;

    function checkStalenessAndPoll() {
        if (!data || !data.last_updated) return;

        const lastUpdate = new Date(data.last_updated);
        const now = new Date();
        const diffMinutes = (now - lastUpdate) / 1000 / 60;

        // If data is older than 2 minutes, verify if background refresh is done by polling
        if (diffMinutes > 2) {
            if (!pollInterval) {
                console.log("⏳ Data is stale, starting auto-poll...");
                pollInterval = setInterval(async () => {
                    console.log("🔄 Polling for fresh data...");
                    await fetchData();
                }, 5000); // Check every 5 seconds
            }
        } else {
            // Data is fresh, stop polling
            if (pollInterval) {
                console.log("✅ Data is fresh! Stopping poll.");
                clearInterval(pollInterval);
                pollInterval = null;
            }
        }
    }

    import { onDestroy } from "svelte";
    onDestroy(() => {
        if (pollInterval) clearInterval(pollInterval);
        if (autoRefreshInterval) clearInterval(autoRefreshInterval);
    });

    function exportCSV() {
        window.open(`${API_BASE}/api/portfolio/export-csv`, "_blank");
    }

    function exportPDF() {
        window.open(`${API_BASE}/api/reports/pdf`, "_blank");
    }

    async function handleIngest() {
        if (
            !confirm(
                "⚠️ ATTENZIONE ⚠️\n\nQuesta operazione AZZERERÀ il database (Holdings & Transazioni) e ricaricherà tutto dai file processati.\n\nSei sicuro di voler procedere?",
            )
        ) {
            return;
        }
        try {
            const res = await fetch(`${API_BASE}/api/ingest/run`, {
                method: "POST",
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Ingestion Failed");
            }
            const result = await res.json();
            alert("✅ Ingestion Completa!\n\nDati ricaricati con successo.");
            await fetchData();
        } catch (e) {
            alert("❌ Errore Ingestion: " + e.message);
        }
    }

    // ... (rest of functions) ...

    function renderCharts() {
        if (!displayData) return;
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
                            ` ${ctx.label}: ${currencySymbol}${ctx.raw.toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
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

                // Calculate filtered total based on selectedBroker
                let totalValue = displayData.total_value;
                if (
                    selectedBroker !== "All" &&
                    displayData.broker_totals[selectedBroker]
                ) {
                    totalValue =
                        displayData.broker_totals[selectedBroker].value;
                }

                var text =
                        currencySymbol + (totalValue / 1000).toFixed(1) + "k",
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
            let brokers, values;
            if (selectedBroker === "All") {
                // Show all brokers
                brokers = Object.keys(displayData.broker_totals);
                values = Object.values(displayData.broker_totals).map(
                    (b) => b.value,
                );
            } else {
                // Show only selected broker (single bar/slice)
                brokers = [selectedBroker];
                values = [
                    displayData.broker_totals[selectedBroker]?.value || 0,
                ];
            }

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
            // Compute asset totals from filteredHoldings
            const assetTotals = {};
            const holdings =
                selectedBroker === "All"
                    ? displayData.holdings
                    : displayData.holdings.filter(
                          (h) => h.broker === selectedBroker,
                      );

            for (const h of holdings) {
                const type = h.asset_type || "OTHER";
                assetTotals[type] =
                    (assetTotals[type] || 0) + (h.current_value || 0);
            }

            const assets = Object.keys(assetTotals);
            const values = Object.values(assetTotals);

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
    $: if ($themeState && displayData) {
        renderCharts();
    }

    // React to chart type toggle
    $: if (chartType && displayData) {
        renderCharts();
    }

    // React to data or currency change
    $: if (displayData) {
        renderCharts();
    }

    // React to broker filter change - explicit dependency tracking
    $: selectedBroker,
        displayData,
        (() => {
            if (displayData) renderCharts();
        })();

    $: if (refreshTrigger) fetchData();
    onMount(fetchData);

    // Grouping Logic for AssetTable keys
    $: filteredHoldings = displayData
        ? selectedBroker === "All"
            ? displayData.holdings
            : displayData.holdings.filter((h) => h.broker === selectedBroker)
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

    // Auto-refresh: Initialize on component mount

    onMount(() => {
        // Initial fetch
        fetchData();

        // Setup periodic refresh (60 seconds)
        autoRefreshInterval = setInterval(() => {
            console.log("🔄 Auto-refresh: Fetching updated prices...");
            fetchData();
        }, 60000); // 60 seconds

        return () => {
            // Cleanup on unmount
            if (autoRefreshInterval) clearInterval(autoRefreshInterval);
        };
    });

    // Manual refresh trigger from parent
    $: if (refreshTrigger > 0) {
        fetchData();
    }
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
            <div class="flex items-center gap-2">
                <!-- Ingest Button -->
                <button
                    on:click={handleIngest}
                    class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-red-600 text-white hover:bg-red-700 transition-all shadow-lg shadow-red-900/20 text-xs font-bold uppercase tracking-wider mr-2"
                    title="Reset DB & Reload Data"
                >
                    <Database size={14} />
                    Reset DB
                </button>

                <!-- New Transaction Button -->
                <button
                    on:click={openNewTransaction}
                    class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-skin-primary text-skin-inverted hover:opacity-90 transition-all shadow-lg shadow-skin-primary/20 text-xs font-bold uppercase tracking-wider"
                >
                    <Plus size={14} />
                    New
                </button>

                <!-- Currency Toggle -->
                <div
                    class="flex bg-skin-card border border-skin-border rounded overflow-hidden"
                >
                    <button
                        class="px-2 py-1 text-xs font-medium transition-colors {selectedCurrency ===
                        'EUR'
                            ? 'bg-skin-text text-skin-bg'
                            : 'text-skin-muted hover:text-skin-text'}"
                        on:click={() => (selectedCurrency = "EUR")}>EUR</button
                    >
                    <button
                        class="px-2 py-1 text-xs font-medium transition-colors {selectedCurrency ===
                        'USD'
                            ? 'bg-skin-text text-skin-bg'
                            : 'text-skin-muted hover:text-skin-text'}"
                        on:click={() => (selectedCurrency = "USD")}>USD</button
                    >
                </div>

                <!-- Export PDF Button -->
                <button
                    on:click={exportPDF}
                    class="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-skin-muted bg-skin-card border border-skin-border rounded hover:text-skin-text hover:border-skin-accent/50 transition-colors"
                    title="Export to PDF"
                >
                    <FileText size={14} />
                    PDF
                </button>

                <!-- Export CSV Button -->
                <button
                    on:click={exportCSV}
                    class="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-skin-muted bg-skin-card border border-skin-border rounded hover:text-skin-text hover:border-skin-accent/50 transition-colors"
                    title="Export to CSV"
                >
                    <Download size={14} />
                    Export
                </button>
                <div
                    class="flex items-center gap-2 text-xs text-skin-muted bg-skin-card px-2 py-1 rounded border border-skin-border"
                >
                    <div
                        class="w-1.5 h-1.5 rounded-full {data.last_updated &&
                        new Date() - new Date(data.last_updated) < 120000
                            ? 'bg-skin-pos animate-pulse'
                            : 'bg-yellow-500'}"
                    ></div>
                    <span class="font-mono">
                        {data.last_updated
                            ? data.last_updated.split(" ")[1].slice(0, 5)
                            : "Live"}
                    </span>
                </div>
            </div>
        </div>

        <!-- KPIs Grid -->
        <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
            <!-- Total Value -->
            <div
                class="p-4 bg-skin-card backdrop-blur-md border border-skin-border rounded-lg shadow-sm hover:border-skin-muted/50 transition-colors cursor-pointer group"
                on:click={() => (selectedBroker = "All")}
                on:keydown={(e) =>
                    e.key === "Enter" && (selectedBroker = "All")}
                role="button"
                tabindex="0"
                title="Reset Filter (Show All)"
            >
                <div
                    class="text-[11px] font-medium text-skin-muted uppercase tracking-wider mb-1"
                >
                    Total Value
                </div>
                <div
                    class="text-2xl font-semibold text-skin-text tracking-tight mb-2"
                >
                    {currencySymbol}{displayData.total_value.toLocaleString(
                        undefined,
                        {
                            minimumFractionDigits: 0,
                            maximumFractionDigits: 0,
                        },
                    )}
                </div>
                <!-- Mini P&L info -->
                <div class="flex items-center gap-3 text-xs font-medium">
                    <div
                        class={(displayData.total_day_pl || 0) >= 0
                            ? "text-skin-pos"
                            : "text-skin-neg"}
                    >
                        1D: {(displayData.total_day_change_pct || 0) >= 0
                            ? "+"
                            : ""}{(
                            displayData.total_day_change_pct || 0
                        ).toFixed(2)}%
                    </div>
                </div>
            </div>

            <!-- Liquidity (New) -->
            <div
                class="p-4 bg-skin-card backdrop-blur-md border border-skin-border rounded-lg shadow-sm hover:border-skin-muted/50 transition-colors"
            >
                <div
                    class="text-[11px] font-medium text-skin-muted uppercase tracking-wider mb-1"
                >
                    Liquidity
                </div>
                <div
                    class="text-2xl font-semibold text-skin-text tracking-tight mb-2"
                >
                    {currencySymbol}{groups.cash
                        .reduce((sum, h) => sum + h.current_value, 0)
                        .toLocaleString(undefined, {
                            minimumFractionDigits: 0,
                            maximumFractionDigits: 0,
                        })}
                </div>
                <div class="text-xs text-skin-muted font-medium">
                    {(
                        (groups.cash.reduce(
                            (sum, h) => sum + h.current_value,
                            0,
                        ) /
                            (displayData.total_value || 1)) *
                        100
                    ).toFixed(1)}% of Portfolio
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
                        class="text-2xl font-semibold tracking-tight {displayData.total_pnl >=
                        0
                            ? 'text-skin-pos'
                            : 'text-skin-neg'}"
                    >
                        {displayData.total_pnl >= 0
                            ? "+"
                            : ""}{currencySymbol}{Math.abs(
                            displayData.total_pnl,
                        ).toLocaleString(undefined, {
                            minimumFractionDigits: 0,
                            maximumFractionDigits: 0,
                        })}
                    </div>
                </div>
                <!-- Net Invested Display -->
                <div class="text-[10px] text-skin-muted font-medium mt-0.5">
                    Net Invested: {currencySymbol}{displayData.total_cost.toLocaleString(
                        undefined,
                        { maximumFractionDigits: 0 },
                    )}
                </div>
                <!-- 1D P/L Row -->
                <div class="flex items-center gap-2 mt-1 text-sm font-medium">
                    <span
                        class="text-skin-muted text-[10px] uppercase tracking-wider"
                        >1D:</span
                    >
                    <span
                        class={(displayData.total_day_pl || 0) >= 0
                            ? "text-skin-pos"
                            : "text-skin-neg"}
                    >
                        {(displayData.total_day_pl || 0) >= 0
                            ? "+"
                            : "-"}{currencySymbol}{Math.abs(
                            displayData.total_day_pl || 0,
                        ).toLocaleString(undefined, {
                            maximumFractionDigits: 0,
                        })}
                        ({(displayData.total_day_change_pct || 0) >= 0
                            ? "+"
                            : ""}{(
                            displayData.total_day_change_pct || 0
                        ).toFixed(2)}%)
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
                    {displayData.count}
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
                    {Object.keys(displayData.broker_totals).length}
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
            {#each Object.entries(displayData.broker_totals).sort((a, b) => b[1].value - a[1].value) as [broker, val]}
                <div
                    class="p-3 bg-skin-card backdrop-blur-sm border border-skin-border rounded-lg {selectedBroker ===
                    broker
                        ? 'border-skin-accent ring-1 ring-skin-accent/20'
                        : 'hover:border-skin-accent/50'} transition-all cursor-pointer"
                    on:click={() =>
                        (selectedBroker =
                            selectedBroker === broker ? "All" : broker)}
                    on:keydown={(e) =>
                        e.key === "Enter" &&
                        (selectedBroker =
                            selectedBroker === broker ? "All" : broker)}
                    role="button"
                    tabindex="0"
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
                            {currencySymbol}{val.value.toLocaleString(
                                undefined,
                                {
                                    maximumFractionDigits: 0,
                                },
                            )}
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
                        {((val.value / displayData.total_value) * 100).toFixed(
                            1,
                        )}% of total
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
            <div class="flex items-center gap-2">
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
                    {#each Object.keys(displayData.broker_totals).sort() as broker}
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

                <!-- Quick New Asset Button -->
                <button
                    on:click={openNewTransaction}
                    class="p-1.5 rounded-md bg-skin-primary/10 text-skin-primary hover:bg-skin-primary/20 border border-skin-primary/20 transition-colors"
                    title="Add New Asset"
                >
                    <Plus size={16} />
                </button>
            </div>
        </div>

        <div class="grid grid-cols-1 gap-6">
            <AssetTable
                title="Stocks"
                items={groups.stocks}
                color="text-skin-accent"
                on:buy={handleBuy}
                on:sell={handleSell}
            />
            <AssetTable
                title="ETFs"
                items={groups.etfs}
                color="text-skin-pos"
                on:buy={handleBuy}
                on:sell={handleSell}
            />
            <AssetTable
                title="Bonds"
                items={groups.bonds}
                color="text-yellow-400"
                on:buy={handleBuy}
                on:sell={handleSell}
            />
            <AssetTable
                title="Crypto"
                items={groups.crypto}
                color="text-purple-400"
                on:buy={handleBuy}
                on:sell={handleSell}
            />
            <AssetTable
                title="Commodities"
                items={groups.commodities}
                color="text-orange-400"
                on:buy={handleBuy}
                on:sell={handleSell}
            />
            <AssetTable
                title="Cash"
                items={groups.cash}
                color="text-skin-muted"
                on:buy={handleBuy}
                on:sell={handleSell}
            />
        </div>
    </div>

    <TransactionModal
        isOpen={showModal}
        mode={modalMode}
        initialData={modalData}
        fxRates={data?.fx_rates}
        availableBrokers={data?.broker_totals
            ? Object.keys(data.broker_totals)
            : []}
        on:close={() => (showModal = false)}
        on:save={handleSaveTransaction}
    />
{/if}
