<script>
    import { ChevronUp, ChevronDown } from "lucide-svelte";
    import { createEventDispatcher } from "svelte";

    const dispatch = createEventDispatcher();

    export let title = "Holdings";
    export let items = [];
    export let color = "text-skin-text";

    let sortKey = "current_value"; // Default sort
    let sortDir = -1; // -1 for desc, 1 for asc

    function toggleSort(key) {
        if (sortKey === key) {
            sortDir = sortDir * -1;
        } else {
            sortKey = key;
            sortDir = -1; // Default to desc for new keys (usually what users want for portfolio metrics)
        }
    }

    $: sortedItems = [...items].sort((a, b) => {
        let aVal = a[sortKey];
        let bVal = b[sortKey];

        // Special handling for calculated fields if needed
        if (sortKey === "avg_price") {
            aVal = a.cost_basis / (a.quantity || 1);
            bVal = b.cost_basis / (b.quantity || 1);
        }

        if (typeof aVal === "string") {
            return aVal.localeCompare(bVal) * sortDir;
        }
        return ((aVal || 0) - (bVal || 0)) * sortDir;
    });
</script>

<div
    class="border border-skin-border rounded-lg overflow-hidden bg-skin-card backdrop-blur-md h-full flex flex-col"
>
    <div
        class="px-3 py-2 border-b border-skin-border flex justify-between items-center bg-skin-base/30"
    >
        <h3 class="text-xs font-semibold uppercase tracking-wider {color}">
            {title}
        </h3>
        <span class="text-[10px] text-skin-muted font-mono"
            >{items.length} items</span
        >
    </div>

    <div class="overflow-x-auto flex-1">
        {#if items.length === 0}
            <div class="p-4 text-center text-xs text-skin-muted">
                No holdings
            </div>
        {:else}
            <table class="w-full text-left text-xs">
                <thead
                    class="bg-skin-base/50 text-skin-muted border-b border-skin-border sticky top-0 z-10 backdrop-blur-sm"
                >
                    <tr>
                        <th
                            class="px-1.5 py-1 font-medium tracking-tight cursor-pointer hover:text-skin-text transition-colors"
                            on:click={() => toggleSort("ticker")}
                        >
                            <div class="flex items-center gap-0.5">
                                Ticker
                                {#if sortKey === "ticker"}
                                    {sortDir === 1 ? "↑" : "↓"}
                                {/if}
                            </div>
                        </th>
                        <th
                            class="px-1.5 py-1 font-medium tracking-tight cursor-pointer hover:text-skin-text transition-colors"
                            on:click={() => toggleSort("isin")}
                        >
                            <div class="flex items-center gap-0.5">
                                ISIN
                                {#if sortKey === "isin"}
                                    {sortDir === 1 ? "↑" : "↓"}
                                {/if}
                            </div>
                        </th>
                        <th
                            class="px-1.5 py-1 font-medium tracking-tight cursor-pointer hover:text-skin-text transition-colors"
                            on:click={() => toggleSort("name")}
                        >
                            <div class="flex items-center gap-0.5">
                                Name
                                {#if sortKey === "name"}
                                    {sortDir === 1 ? "↑" : "↓"}
                                {/if}
                            </div>
                        </th>
                        <th
                            class="px-1.5 py-1 font-medium tracking-tight cursor-pointer hover:text-skin-text transition-colors"
                            on:click={() => toggleSort("broker")}
                        >
                            <div class="flex items-center gap-0.5">
                                Broker
                                {#if sortKey === "broker"}
                                    {sortDir === 1 ? "↑" : "↓"}
                                {/if}
                            </div>
                        </th>
                        <th
                            class="px-1.5 py-1 font-medium tracking-tight cursor-pointer hover:text-skin-text transition-colors"
                            on:click={() => toggleSort("currency")}
                        >
                            <div class="flex items-center gap-0.5">
                                Cur
                                {#if sortKey === "currency"}
                                    {sortDir === 1 ? "↑" : "↓"}
                                {/if}
                            </div>
                        </th>
                        <th
                            class="px-1.5 py-1 font-medium tracking-tight text-right cursor-pointer hover:text-skin-text transition-colors"
                            on:click={() => toggleSort("quantity")}
                        >
                            <div class="flex items-center justify-end gap-0.5">
                                {#if sortKey === "quantity"}
                                    {sortDir === 1 ? "↑" : "↓"}
                                {/if}
                                Qty
                            </div>
                        </th>
                        <th
                            class="px-1.5 py-1 font-medium tracking-tight text-right cursor-pointer hover:text-skin-text transition-colors"
                            on:click={() => toggleSort("avg_price")}
                        >
                            <div class="flex items-center justify-end gap-0.5">
                                {#if sortKey === "avg_price"}
                                    {sortDir === 1 ? "↑" : "↓"}
                                {/if}
                                Avg
                            </div>
                        </th>
                        <th
                            class="px-1.5 py-1 font-medium tracking-tight text-right cursor-pointer hover:text-skin-text transition-colors"
                            on:click={() => toggleSort("live_price")}
                        >
                            <div class="flex items-center justify-end gap-0.5">
                                {#if sortKey === "live_price"}
                                    {sortDir === 1 ? "↑" : "↓"}
                                {/if}
                                Now
                            </div>
                        </th>

                        <!-- NEW COLUMNS -->
                        <th
                            class="px-1.5 py-1 font-medium tracking-tight text-right cursor-pointer hover:text-skin-text transition-colors"
                            on:click={() => toggleSort("day_change_pct")}
                        >
                            <div class="flex items-center justify-end gap-0.5">
                                {#if sortKey === "day_change_pct"}
                                    {sortDir === 1 ? "↑" : "↓"}
                                {/if}
                                1D%
                            </div>
                        </th>
                        <th
                            class="px-1.5 py-1 font-medium tracking-tight text-right cursor-pointer hover:text-skin-text transition-colors"
                            on:click={() => toggleSort("pnl_pct")}
                        >
                            <div class="flex items-center justify-end gap-0.5">
                                {#if sortKey === "pnl_pct"}
                                    {sortDir === 1 ? "↑" : "↓"}
                                {/if}
                                Net%
                            </div>
                        </th>

                        <!-- NEW: Net P&L (Value) Header -->
                        <th
                            class="px-1.5 py-1 font-medium tracking-tight text-right cursor-pointer hover:text-skin-text transition-colors"
                            on:click={() => toggleSort("pnl")}
                        >
                            <div class="flex items-center justify-end gap-0.5">
                                {#if sortKey === "pnl"}
                                    {sortDir === 1 ? "↑" : "↓"}
                                {/if}
                                Net
                            </div>
                        </th>

                        <th
                            class="px-1.5 py-1 font-medium tracking-tight text-right cursor-pointer hover:text-skin-text transition-colors"
                            on:click={() => toggleSort("current_value")}
                        >
                            <div class="flex items-center justify-end gap-0.5">
                                {#if sortKey === "current_value"}
                                    {sortDir === 1 ? "↑" : "↓"}
                                {/if}
                                Value
                            </div>
                        </th>
                        <th
                            class="px-1.5 py-1 font-medium tracking-tight text-right cursor-pointer hover:text-skin-text transition-colors"
                            on:click={() => toggleSort("day_pl")}
                        >
                            <div class="flex items-center justify-end gap-0.5">
                                {#if sortKey === "day_pl"}
                                    {sortDir === 1 ? "↑" : "↓"}
                                {/if}
                                1D±
                            </div>
                        </th>

                        <!-- NEW: Actions Header -->
                        <th
                            class="px-1.5 py-1 font-medium tracking-tight text-right text-skin-muted/50"
                        >
                            Act
                        </th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-skin-border">
                    {#each sortedItems as h}
                        <tr
                            class="hover:bg-skin-base/30 transition-colors group"
                        >
                            <!-- Ticker -->
                            <td
                                class="px-1.5 py-1 font-semibold text-skin-text font-mono text-[10px] whitespace-nowrap"
                            >
                                {h.ticker}
                            </td>

                            <!-- ISIN -->
                            <td
                                class="px-1.5 py-1 text-skin-muted font-mono text-[9px] whitespace-nowrap select-all"
                                title={h.isin}
                            >
                                {h.isin || "-"}
                            </td>

                            <!-- Name (Description) -->
                            <td
                                class="px-1.5 py-1 text-skin-muted text-[10px] max-w-[100px] truncate"
                                title={h.name}
                            >
                                {h.name}
                            </td>

                            <!-- Broker -->
                            <td
                                class="px-1.5 py-1 text-skin-muted text-[10px] whitespace-nowrap"
                            >
                                {h.broker.replace("_", " ")}
                            </td>

                            <!-- Currency -->
                            <td
                                class="px-1.5 py-1 text-skin-muted text-[10px] whitespace-nowrap font-mono"
                            >
                                {h.currency || "?"}
                            </td>

                            <!-- Quantity -->
                            <td
                                class="px-1.5 py-1 text-right font-mono text-skin-muted text-[10px]"
                            >
                                {#if h.quantity < 1 && h.quantity > 0}
                                    {(h.quantity || 0).toFixed(4)}
                                {:else}
                                    {(h.quantity || 0).toLocaleString()}
                                {/if}
                            </td>

                            <!-- Avg Price -->
                            <td
                                class="px-1.5 py-1 text-right font-mono text-skin-muted text-[10px]"
                            >
                                {(h.cost_basis && h.quantity
                                    ? h.cost_basis / h.quantity
                                    : 0
                                ).toLocaleString(undefined, {
                                    maximumFractionDigits: 1,
                                })}
                            </td>

                            <!-- Current Price -->
                            <td
                                class="px-1.5 py-1 text-right font-mono text-skin-text text-[10px]"
                            >
                                {(h.live_price || 0).toLocaleString(undefined, {
                                    maximumFractionDigits: 1,
                                })}
                            </td>

                            <!-- % 1D -->
                            <td
                                class="px-1.5 py-1 text-right font-mono text-[10px] {(h.day_change_pct ||
                                    0) >= 0
                                    ? 'text-skin-pos'
                                    : 'text-skin-neg'}"
                            >
                                {(h.day_change_pct || 0) > 0 ? "+" : ""}{(
                                    h.day_change_pct || 0
                                ).toFixed(1)}%
                            </td>

                            <!-- % Net (Total P&L %) -->
                            <td
                                class="px-1.5 py-1 text-right font-mono text-[10px] {(h.pnl_pct ||
                                    0) >= 0
                                    ? 'text-skin-pos'
                                    : 'text-skin-neg'}"
                            >
                                {(h.pnl_pct || 0) > 0 ? "+" : ""}{(
                                    h.pnl_pct || 0
                                ).toFixed(1)}%
                            </td>

                            <!-- NEW: Net P&L (Value) -->
                            <td
                                class="px-1.5 py-1 text-right font-mono text-[10px] {(h.pnl ||
                                    0) >= 0
                                    ? 'text-skin-pos'
                                    : 'text-skin-neg'}"
                            >
                                {(h.pnl || 0) > 0 ? "+" : ""}{(
                                    h.pnl || 0
                                ).toLocaleString(undefined, {
                                    maximumFractionDigits: 0,
                                })}
                            </td>

                            <!-- Market Value -->
                            <td
                                class="px-1.5 py-1 text-right font-mono text-skin-text font-medium text-[10px]"
                            >
                                {(h.current_value || 0).toLocaleString(
                                    undefined,
                                    {
                                        maximumFractionDigits: 0,
                                    },
                                )}
                            </td>

                            <!-- P&L 1D -->
                            <td
                                class="px-1.5 py-1 text-right font-mono text-[10px] {(h.day_pl ||
                                    0) >= 0
                                    ? 'text-skin-pos'
                                    : 'text-skin-neg'}"
                            >
                                {(h.day_pl || 0) > 0 ? "+" : ""}{Math.abs(
                                    h.day_pl || 0,
                                ).toLocaleString(undefined, {
                                    maximumFractionDigits: 0,
                                })}
                            </td>

                            <!-- NEW: Actions -->
                            <td class="px-1.5 py-1 text-right">
                                <div class="flex justify-end gap-1">
                                    <button
                                        class="px-1.5 py-0.5 rounded text-[9px] font-bold bg-green-500/20 text-green-400 hover:bg-green-500/30 transition-colors"
                                        title="Buy"
                                        on:click|stopPropagation={() =>
                                            dispatch("buy", h)}>B</button
                                    >
                                    <button
                                        class="px-1.5 py-0.5 rounded text-[9px] font-bold bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"
                                        title="Sell"
                                        on:click|stopPropagation={() =>
                                            dispatch("sell", h)}>S</button
                                    >
                                </div>
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        {/if}
    </div>
</div>
