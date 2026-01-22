<script>
    import { onMount } from "svelte";
    import {
        Bell,
        Plus,
        Trash2,
        TrendingUp,
        TrendingDown,
        RefreshCw,
    } from "lucide-svelte";

    const API_BASE = "";

    let alerts = [];
    let loading = true;
    let error = null;
    let showForm = false;

    // Form state
    let newTicker = "";
    let newPrice = "";
    let newDirection = "above";
    let creating = false;

    async function loadAlerts() {
        loading = true;
        error = null;
        try {
            const res = await fetch(`${API_BASE}/api/alerts`);
            if (!res.ok) throw new Error("Failed to load alerts");
            alerts = await res.json();
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    }

    async function createAlert() {
        if (!newTicker || !newPrice) return;

        creating = true;
        try {
            const res = await fetch(`${API_BASE}/api/alerts`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    ticker: newTicker.toUpperCase(),
                    target_price: parseFloat(newPrice),
                    direction: newDirection,
                    notify_telegram: true,
                }),
            });

            if (!res.ok) throw new Error("Failed to create alert");

            // Reset form and reload
            newTicker = "";
            newPrice = "";
            newDirection = "above";
            showForm = false;
            await loadAlerts();
        } catch (e) {
            error = e.message;
        } finally {
            creating = false;
        }
    }

    async function deleteAlert(id) {
        try {
            const res = await fetch(`${API_BASE}/api/alerts/${id}`, {
                method: "DELETE",
            });
            if (!res.ok) throw new Error("Failed to delete alert");
            await loadAlerts();
        } catch (e) {
            error = e.message;
        }
    }

    async function checkAlertsNow() {
        try {
            const res = await fetch(`${API_BASE}/api/alerts/check`, {
                method: "POST",
            });
            const data = await res.json();
            if (data.triggered && data.triggered.length > 0) {
                alert(`${data.triggered.length} alert(s) triggered!`);
            }
            await loadAlerts();
        } catch (e) {
            error = e.message;
        }
    }

    onMount(loadAlerts);
</script>

<div class="space-y-4">
    <!-- Header -->
    <div
        class="flex items-center justify-between pb-3 border-b border-skin-border"
    >
        <div class="flex items-center gap-2">
            <Bell size={20} class="text-skin-accent" />
            <h2 class="text-lg font-medium text-skin-text">Price Alerts</h2>
            <span
                class="text-xs text-skin-muted bg-skin-base px-2 py-0.5 rounded-full"
            >
                {alerts.length} active
            </span>
        </div>
        <div class="flex items-center gap-2">
            <button
                on:click={checkAlertsNow}
                class="p-1.5 text-skin-muted hover:text-skin-text hover:bg-skin-card rounded border border-skin-border transition-colors"
                title="Check alerts now"
            >
                <RefreshCw size={14} />
            </button>
            <button
                on:click={() => (showForm = !showForm)}
                class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-skin-accent text-white rounded hover:bg-skin-accent/80 transition-colors"
            >
                <Plus size={14} />
                New Alert
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

    <!-- Create Alert Form -->
    {#if showForm}
        <div
            class="p-4 bg-skin-card border border-skin-border rounded-lg space-y-3 animate-in slide-in-from-top-2 duration-200"
        >
            <div class="grid grid-cols-3 gap-3">
                <div>
                    <label
                        class="block text-[10px] uppercase text-skin-muted mb-1"
                        >Ticker</label
                    >
                    <input
                        type="text"
                        bind:value={newTicker}
                        placeholder="AAPL"
                        class="w-full px-3 py-2 bg-skin-base border border-skin-border rounded text-sm text-skin-text placeholder:text-skin-muted/50 focus:outline-none focus:border-skin-accent"
                    />
                </div>
                <div>
                    <label
                        class="block text-[10px] uppercase text-skin-muted mb-1"
                        >Target Price ($)</label
                    >
                    <input
                        type="number"
                        bind:value={newPrice}
                        placeholder="200.00"
                        step="0.01"
                        class="w-full px-3 py-2 bg-skin-base border border-skin-border rounded text-sm text-skin-text placeholder:text-skin-muted/50 focus:outline-none focus:border-skin-accent"
                    />
                </div>
                <div>
                    <label
                        class="block text-[10px] uppercase text-skin-muted mb-1"
                        >Direction</label
                    >
                    <select
                        bind:value={newDirection}
                        class="w-full px-3 py-2 bg-skin-base border border-skin-border rounded text-sm text-skin-text focus:outline-none focus:border-skin-accent"
                    >
                        <option value="above">Above ↑</option>
                        <option value="below">Below ↓</option>
                    </select>
                </div>
            </div>
            <div class="flex justify-end gap-2">
                <button
                    on:click={() => (showForm = false)}
                    class="px-3 py-1.5 text-xs text-skin-muted hover:text-skin-text transition-colors"
                >
                    Cancel
                </button>
                <button
                    on:click={createAlert}
                    disabled={creating || !newTicker || !newPrice}
                    class="px-4 py-1.5 text-xs font-medium bg-skin-pos text-white rounded hover:bg-skin-pos/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                    {creating ? "Creating..." : "Create Alert"}
                </button>
            </div>
        </div>
    {/if}

    <!-- Alerts List -->
    {#if loading}
        <div
            class="flex items-center justify-center py-8 text-skin-muted text-sm"
        >
            Loading alerts...
        </div>
    {:else if alerts.length === 0}
        <div
            class="flex flex-col items-center justify-center py-12 text-skin-muted"
        >
            <Bell size={32} class="mb-2 opacity-50" />
            <p class="text-sm">No active alerts</p>
            <p class="text-xs mt-1">
                Create an alert to get notified when prices cross your targets
            </p>
        </div>
    {:else}
        <div class="space-y-2">
            {#each alerts as alert}
                <div
                    class="flex items-center justify-between p-3 bg-skin-card border border-skin-border rounded-lg hover:border-skin-accent/30 transition-colors"
                >
                    <div class="flex items-center gap-3">
                        <div
                            class="p-2 rounded-full {alert.direction === 'above'
                                ? 'bg-skin-pos/10 text-skin-pos'
                                : 'bg-skin-neg/10 text-skin-neg'}"
                        >
                            {#if alert.direction === "above"}
                                <TrendingUp size={16} />
                            {:else}
                                <TrendingDown size={16} />
                            {/if}
                        </div>
                        <div>
                            <div class="flex items-center gap-2">
                                <span
                                    class="font-mono font-semibold text-skin-text"
                                    >{alert.ticker}</span
                                >
                                <span class="text-xs text-skin-muted">
                                    {alert.direction === "above" ? "≥" : "≤"} ${alert.target_price.toFixed(
                                        2,
                                    )}
                                </span>
                            </div>
                            <div class="text-[10px] text-skin-muted mt-0.5">
                                Created {new Date(
                                    alert.created_at,
                                ).toLocaleDateString()}
                                {#if alert.notify_telegram}
                                    • Telegram ✓
                                {/if}
                            </div>
                        </div>
                    </div>
                    <button
                        on:click={() => deleteAlert(alert.id)}
                        class="p-2 text-skin-muted hover:text-skin-neg hover:bg-skin-neg/10 rounded transition-colors"
                        title="Delete alert"
                    >
                        <Trash2 size={14} />
                    </button>
                </div>
            {/each}
        </div>
    {/if}
</div>
