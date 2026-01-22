<script>
    import { createEventDispatcher } from "svelte";
    import { X, Search as SearchIcon, Info } from "lucide-svelte";
    import { fade, slide } from "svelte/transition";

    // Props
    export let isOpen = false;
    export let mode = "BUY"; // BUY, SELL, DEPOSIT, WITHDRAW
    export let initialData = null; // Holding object
    export let fxRates = {}; // Exchange rates
    export let availableBrokers = []; // From DB

    const dispatch = createEventDispatcher();
    const API_BASE = "";

    // Form State
    let formData = {
        broker: "",
        ticker: "",
        asset_type: "STOCK",
        quantity: 0,
        price: 0,
        currency: "EUR",
        date: new Date().toISOString().split("T")[0],
    };

    // View State
    let searchResults = [];
    let showResults = false;
    let searchTimer = null;
    let isFetchingDetails = false;

    // Initialize form
    // Track open state to trigger init only once
    let wasOpen = false;

    $: if (isOpen && !wasOpen) {
        wasOpen = true;
        // logic when modal opens
        if (initialData) {
            formData = {
                ...formData,
                broker: initialData.broker,
                ticker: initialData.ticker,
                asset_type: initialData.asset_type || "STOCK",
                price: initialData.live_price || initialData.current_price || 0,
                currency: initialData.currency || "EUR",
            };
        } else {
            // Reset for "New Asset" flow
            formData = {
                broker: "",
                ticker: "",
                asset_type: "STOCK",
                quantity: 0,
                price: 0,
                currency: "EUR",
                date: new Date().toISOString().split("T")[0],
            };
        }
    } else if (!isOpen && wasOpen) {
        wasOpen = false;
    }

    $: totalValue = (formData.quantity * formData.price).toFixed(2);

    function close() {
        showResults = false;
        dispatch("close");
    }

    async function save() {
        if (!formData.ticker && mode !== "DEPOSIT" && mode !== "WITHDRAW") {
            alert("Please select an asset");
            return;
        }
        if (!formData.broker || !formData.quantity) {
            alert("Please fill all required fields");
            return;
        }
        if (formData.quantity <= 0) {
            alert("Quantity must be greater than 0");
            return;
        }
        dispatch("save", { mode, data: formData });
    }

    // SEARCH LOGIC
    async function handleSearchInput() {
        // State is already updated via bind:value
        const query = formData.ticker;

        if (searchTimer) clearTimeout(searchTimer);

        if (!query || query.length < 2) {
            searchResults = [];
            showResults = false;
            return;
        }

        searchTimer = setTimeout(async () => {
            try {
                const res = await fetch(
                    `${API_BASE}/api/market/search?q=${query}`,
                );
                if (res.ok) {
                    searchResults = await res.json();
                    showResults = true;
                }
            } catch (err) {
                console.error("Search failed", err);
            }
        }, 300); // 300ms debounce
    }

    async function selectAsset(asset) {
        if (searchTimer) clearTimeout(searchTimer); // Stop any pending search

        // Update form state (Input bound to ticker will update automatically)
        formData = {
            ...formData,
            ticker: asset.ticker,
        };
        showResults = false;

        // Auto-fetch details (Price, Currency)
        isFetchingDetails = true;
        try {
            const res = await fetch(
                `${API_BASE}/api/market/details?ticker=${asset.ticker}`,
            );
            if (res.ok) {
                const details = await res.json();
                if (details) {
                    formData = {
                        ...formData,
                        price: details.price || 0,
                        currency: details.currency || "EUR",
                        asset_type: mapType(asset.type),
                    };
                }
            } else {
                console.error("Failed to fetch details");
            }
        } catch (e) {
            console.error("Error fetching details", e);
        } finally {
            isFetchingDetails = false;
        }
    }

    function mapType(yType) {
        if (!yType) return "STOCK";
        const t = yType.toUpperCase();
        if (t.includes("ETF")) return "ETF";
        if (t === "CRYPTOCURRENCY") return "CRYPTO";
        if (t === "FUTURE") return "COMMODITY";
        return "STOCK";
    }

    // Mock Brokers
    const BROKERS = [
        "Interactive Brokers",
        "BG SAXO",
        "Trading 212",
        "Binance",
        "Revolut",
        "SCALABLE_CAPITAL",
        "Trade_Repubblic",
    ];
    const CURRENCIES = ["EUR", "USD", "GBP", "CHF"];
</script>

{#if isOpen}
    <div
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
    >
        <!-- Modal Card -->
        <div
            class="w-full max-w-md bg-skin-card border border-skin-border rounded-xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden animate-in fade-in zoom-in-95 duration-200"
            on:click={() => (showResults = false)}
        >
            <!-- Header -->
            <div
                class="px-5 py-4 border-b border-skin-border flex justify-between items-center bg-skin-base/40"
            >
                <h2 class="text-lg font-semibold text-skin-text tracking-tight">
                    {mode === "DEPOSIT"
                        ? "Deposit Cash"
                        : mode === "WITHDRAW"
                          ? "Withdraw Cash"
                          : "Record Transaction"}
                </h2>
                <button
                    on:click={close}
                    class="text-skin-muted hover:text-skin-text transition-colors"
                >
                    <X size={20} />
                </button>
            </div>

            <!-- Tabs (Mode Switch) -->
            <div
                class="flex p-1 bg-skin-base/30 m-5 mb-0 rounded-lg border border-skin-border/50"
            >
                {#each ["BUY", "SELL", "DEPOSIT", "WITHDRAW"] as m}
                    <button
                        class="flex-1 py-1.5 text-xs font-medium rounded-md transition-all duration-200
                        {mode === m
                            ? m === 'BUY' || m === 'DEPOSIT'
                                ? 'bg-skin-pos/20 text-skin-pos shadow-sm border border-skin-pos/30'
                                : 'bg-skin-neg/20 text-skin-neg shadow-sm border border-skin-neg/30'
                            : 'text-skin-muted hover:text-skin-text hover:bg-white/5'}"
                        on:click={() => (mode = m)}
                    >
                        {m}
                    </button>
                {/each}
            </div>

            <!-- Body -->
            <div class="p-5 space-y-4 flex-1 overflow-y-auto scrollbar-hide">
                <!-- NEW: Info Panel (Context) -->
                {#if initialData && (mode === "BUY" || mode === "SELL")}
                    <div
                        class="bg-skin-base/40 rounded-lg p-3 text-xs border border-skin-border flex flex-col gap-1.5 shadow-sm"
                    >
                        <div
                            class="flex items-center gap-2 text-skin-primary font-bold border-b border-skin-border pb-1 mb-0.5"
                        >
                            <Info size={12} /> Current Position
                        </div>
                        <div class="flex justify-between font-mono">
                            <span class="text-skin-muted">Avg Price:</span>
                            <span class="text-skin-text font-medium">
                                {(
                                    initialData.cost_basis /
                                    (initialData.quantity || 1)
                                ).toLocaleString(undefined, {
                                    maximumFractionDigits: 2,
                                })}
                                {initialData.currency}
                            </span>
                        </div>
                        <div class="flex justify-between font-mono">
                            <span class="text-skin-muted">Net Value:</span>
                            <span class="text-skin-text font-medium"
                                >{(
                                    initialData.current_value || 0
                                ).toLocaleString(undefined, {
                                    maximumFractionDigits: 0,
                                })}
                                {initialData.currency}</span
                            >
                        </div>
                        {#if initialData.isin}
                            <div class="flex justify-between font-mono">
                                <span class="text-skin-muted">ISIN:</span>
                                <span
                                    class="text-skin-muted select-all bg-skin-base px-1 rounded"
                                    >{initialData.isin}</span
                                >
                            </div>
                        {/if}
                    </div>
                {/if}

                <!-- Broker Selection -->
                <div class="space-y-1">
                    <label
                        class="text-[10px] uppercase font-bold text-skin-muted tracking-wider"
                        >Broker</label
                    >
                    <select
                        bind:value={formData.broker}
                        class="w-full bg-skin-base border border-skin-border rounded-lg px-3 py-2 text-sm text-skin-text focus:outline-none focus:border-skin-primary transition-colors"
                    >
                        <option value="" disabled selected>Select Broker</option
                        >
                        {#if availableBrokers && availableBrokers.length > 0}
                            {#each availableBrokers as b}
                                <option value={b}>{b.replace(/_/g, " ")}</option
                                >
                            {/each}
                        {:else}
                            {#each BROKERS as b}
                                <option value={b}>{b}</option>
                            {/each}
                        {/if}
                    </select>
                </div>

                {#if mode === "BUY" || mode === "SELL"}
                    <!-- Asset Input (Search/Ticker) -->
                    <div class="space-y-1 relative" on:click|stopPropagation>
                        <label
                            class="text-[10px] uppercase font-bold text-skin-muted tracking-wider"
                            >Asset</label
                        >
                        <div class="relative">
                            {#if initialData && initialData.ticker}
                                <div
                                    class="w-full bg-skin-base/50 border border-skin-border rounded-lg px-3 py-2 text-sm text-skin-text font-mono flex items-center gap-2 overflow-hidden"
                                >
                                    {#if formData.ticker === initialData.isin}
                                        <!-- Ticker IS the ISIN, so show Name instead -->
                                        <span
                                            class="font-bold truncate max-w-[200px]"
                                            title={initialData.name}
                                            >{initialData.name ||
                                                formData.ticker}</span
                                        >
                                    {:else}
                                        <span class="font-bold"
                                            >{formData.ticker}</span
                                        >
                                    {/if}

                                    {#if initialData.isin}
                                        <span
                                            class="text-skin-muted flex-shrink-0"
                                            >/</span
                                        >
                                        <span
                                            class="text-xs text-skin-muted flex-shrink-0"
                                            >{initialData.isin}</span
                                        >
                                    {/if}
                                </div>
                            {:else}
                                <input
                                    type="text"
                                    bind:value={formData.ticker}
                                    on:input={handleSearchInput}
                                    on:focus={() => {
                                        if (formData.ticker.length >= 2)
                                            showResults = true;
                                    }}
                                    placeholder="Ticker or ISIN (Search Online)"
                                    class="w-full bg-skin-base border border-skin-border rounded-lg pl-9 pr-3 py-2 text-sm text-skin-text focus:outline-none focus:border-skin-primary transition-colors font-mono"
                                />
                                <SearchIcon
                                    size={14}
                                    class="absolute left-3 top-1/2 -translate-y-1/2 {isFetchingDetails
                                        ? 'text-skin-primary animate-spin'
                                        : 'text-skin-muted'}"
                                />
                            {/if}
                        </div>

                        <!-- Search Dropdown -->
                        {#if showResults && searchResults.length > 0}
                            <div
                                class="absolute z-50 w-full mt-1 bg-neutral-900 border border-skin-border rounded-lg shadow-2xl max-h-60 overflow-y-auto ring-1 ring-black/5"
                                transition:slide|local
                            >
                                {#each searchResults as item}
                                    <button
                                        type="button"
                                        class="w-full text-left px-3 py-2.5 hover:bg-white/5 border-b border-white/5 last:border-0 transition-colors flex justify-between items-center group"
                                        on:click={() => selectAsset(item)}
                                    >
                                        <div class="flex flex-col gap-0.5">
                                            <div
                                                class="flex items-center gap-2"
                                            >
                                                <span
                                                    class="font-bold text-sm text-skin-text"
                                                    >{item.ticker}</span
                                                >
                                                <span
                                                    class="text-[10px] px-1.5 py-0.5 rounded bg-skin-primary/20 text-skin-primary font-bold tracking-wider"
                                                >
                                                    {item.exchange}
                                                </span>
                                            </div>
                                            <div
                                                class="text-[11px] text-skin-muted truncate max-w-[200px]"
                                            >
                                                {item.name}
                                            </div>
                                        </div>
                                    </button>
                                {/each}
                            </div>
                        {/if}
                    </div>

                    <!-- Qty & Price Row -->
                    <div class="grid grid-cols-2 gap-4">
                        <div class="space-y-1">
                            <label
                                class="text-[10px] uppercase font-bold text-skin-muted tracking-wider"
                                >Quantity</label
                            >
                            <input
                                type="number"
                                step="any"
                                min="0"
                                bind:value={formData.quantity}
                                class="w-full bg-skin-base border border-skin-border rounded-lg px-3 py-2 text-sm text-skin-text focus:outline-none focus:border-skin-primary transition-colors font-mono"
                            />
                        </div>
                        <div class="space-y-1">
                            <label
                                class="text-[10px] uppercase font-bold text-skin-muted tracking-wider"
                                >Price</label
                            >
                            <div class="flex gap-2">
                                <input
                                    type="number"
                                    step="any"
                                    min="0"
                                    bind:value={formData.price}
                                    class="w-full bg-skin-base border border-skin-border rounded-lg px-3 py-2 text-sm text-skin-text focus:outline-none focus:border-skin-primary transition-colors font-mono"
                                />
                                <select
                                    bind:value={formData.currency}
                                    class="w-20 bg-skin-base border border-skin-border rounded-lg px-2 py-2 text-xs text-skin-text"
                                >
                                    {#each CURRENCIES as c}
                                        <option value={c}>{c}</option>
                                    {/each}
                                </select>
                            </div>
                        </div>
                    </div>
                {:else}
                    <!-- Deposit/Withdraw Amount -->
                    <div class="space-y-1">
                        <label
                            class="text-[10px] uppercase font-bold text-skin-muted tracking-wider"
                            >Amount</label
                        >
                        <div class="flex gap-2">
                            <input
                                type="number"
                                step="0.01"
                                min="0"
                                bind:value={formData.quantity}
                                class="w-full bg-skin-base border border-skin-border rounded-lg px-3 py-2 text-sm text-skin-text focus:outline-none focus:border-skin-primary transition-colors font-mono"
                            />
                            <select
                                bind:value={formData.currency}
                                class="w-20 bg-skin-base border border-skin-border rounded-lg px-2 py-2 text-xs text-skin-text"
                            >
                                {#each CURRENCIES as c}
                                    <option value={c}>{c}</option>
                                {/each}
                            </select>
                        </div>
                    </div>
                {/if}

                <!-- Date -->
                <div class="space-y-1">
                    <label
                        class="text-[10px] uppercase font-bold text-skin-muted tracking-wider"
                        >Date</label
                    >
                    <input
                        type="date"
                        bind:value={formData.date}
                        class="w-full bg-skin-base border border-skin-border rounded-lg px-3 py-2 text-sm text-skin-text focus:outline-none focus:border-skin-primary transition-colors font-mono"
                    />
                </div>

                <!-- Total Display -->
                <div
                    class="mt-4 pt-4 border-t border-skin-border flex justify-between items-center"
                >
                    <span
                        class="text-xs text-skin-muted uppercase tracking-wider font-bold"
                        >Total Estimated</span
                    >

                    <div
                        class="text-lg font-bold {mode === 'BUY' ||
                        mode === 'WITHDRAW'
                            ? 'text-skin-neg'
                            : 'text-skin-pos'} font-mono ml-4 text-right"
                    >
                        {mode === "BUY" || mode === "WITHDRAW"
                            ? "-"
                            : "+"}{totalValue}
                        {formData.currency}

                        {#if fxRates && (formData.currency === "EUR" || formData.currency === "USD")}
                            <span
                                class="text-skin-muted text-lg font-normal mx-2"
                                >/</span
                            >
                            {#if formData.currency === "EUR"}
                                {(
                                    parseFloat(totalValue) *
                                    (fxRates["USD"] || 1.1)
                                ).toLocaleString(undefined, {
                                    maximumFractionDigits: 2,
                                })} USD
                            {:else if formData.currency === "USD"}
                                {(
                                    parseFloat(totalValue) /
                                    (fxRates["USD"] || 1.1)
                                ).toLocaleString(undefined, {
                                    maximumFractionDigits: 2,
                                })} EUR
                            {/if}
                        {/if}
                    </div>
                </div>
            </div>

            <!-- Actions -->
            <div class="p-5 pt-0 flex gap-3">
                <button
                    on:click={close}
                    class="flex-1 px-4 py-2 rounded-lg border border-skin-border text-skin-muted hover:text-skin-text hover:bg-skin-base transition-colors text-sm font-medium"
                >
                    Cancel
                </button>
                <button
                    on:click={save}
                    class="flex-1 px-4 py-2 rounded-lg bg-skin-primary text-skin-inverted hover:opacity-90 transition-opacity text-sm font-medium shadow-lg shadow-skin-primary/20"
                >
                    Confirm Transaction
                </button>
            </div>
        </div>
    </div>
{/if}

<style>
    /* Utility to hide scrollbar but keep functionality */
    .scrollbar-hide::-webkit-scrollbar {
        display: none;
    }
    .scrollbar-hide {
        -ms-overflow-style: none; /* IE and Edge */
        scrollbar-width: none; /* Firefox */
    }
</style>
