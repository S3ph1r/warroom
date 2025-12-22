<script>
  import { createEventDispatcher } from "svelte";
  import {
    LayoutDashboard,
    BrainCircuit,
    RefreshCw,
    Plus,
    Youtube,
    Palette,
    Monitor,
    Globe,
  } from "lucide-svelte";
  import {
    currentBase,
    currentPalette,
    currentScene,
    bases,
    palettes,
    scenes,
  } from "./stores/theme.js";

  export let activeView = "portfolio";

  const dispatch = createEventDispatcher();
  const API_BASE = "http://localhost:8200";

  let sourcesExpanded = true;
  let newChannel = "";
  let channels = [];
  let loadingSources = false;

  async function fetchSources() {
    try {
      const res = await fetch(`${API_BASE}/api/sources`);
      if (res.ok) {
        const data = await res.json();
        console.log("Sidebar loaded sources:", data);
        channels = data.youtube_channels || [];
        console.log("Sidebar processed channels:", channels.length);
      }
    } catch (e) {
      console.error("Failed to load sources", e);
    }
  }

  async function addSource() {
    if (!newChannel) return;
    try {
      loadingSources = true;
      await fetch(`${API_BASE}/api/sources`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ handle: newChannel }),
      });
      newChannel = "";
      fetchSources();
    } catch (e) {
      console.error("Failed to add source", e);
    } finally {
      loadingSources = false;
    }
  }

  function triggerRefresh() {
    dispatch("refresh");
  }

  // Load sources only when intelligence view is active
  $: if (activeView === "intelligence" && channels.length === 0) {
    console.log("Sidebar: activeView became intelligence, loading sources...");
    fetchSources();
  }

  $: console.log("Sidebar activeView:", activeView);
</script>

<aside
  class="w-64 h-full border-r border-skin-border bg-skin-sidebar flex flex-col shrink-0 z-20 transition-colors duration-300 backdrop-blur-md"
>
  <div class="px-5 py-6">
    <div class="flex items-center gap-2 mb-8">
      <!-- Simplified Logo/Brand -->
      <div
        class="w-5 h-5 bg-skin-accent rounded-sm shadow-sm transition-colors"
      ></div>
      <span class="font-medium text-skin-text tracking-tight transition-colors"
        >War Room</span
      >
    </div>

    <div
      class="text-[11px] font-medium text-skin-muted uppercase tracking-wider mb-2 px-2 transition-colors"
    >
      Navigation
    </div>
    <nav class="space-y-0.5">
      <button
        class="w-full flex items-center gap-3 px-3 py-1.5 rounded-md text-sm transition-all duration-200 font-medium {activeView ===
        'portfolio'
          ? 'bg-skin-card text-skin-text border border-skin-border shadow-sm'
          : 'text-skin-muted hover:text-skin-text hover:bg-skin-card/50'}"
        on:click={() => dispatch("navigate", "portfolio")}
      >
        <LayoutDashboard size={14} />
        <span>Portfolio</span>
      </button>

      <button
        class="w-full flex items-center gap-3 px-3 py-1.5 rounded-md text-sm transition-all duration-200 font-medium {activeView ===
        'intelligence'
          ? 'bg-skin-card text-skin-text border border-skin-border shadow-sm'
          : 'text-skin-muted hover:text-skin-text hover:bg-skin-card/50'}"
        on:click={() => dispatch("navigate", "intelligence")}
      >
        <BrainCircuit size={14} />
        <span>Intelligence</span>
      </button>

      <button
        class="w-full flex items-center gap-3 px-3 py-1.5 rounded-md text-sm transition-all duration-200 font-medium {activeView ===
        'council'
          ? 'bg-skin-card text-skin-text border border-skin-border shadow-sm'
          : 'text-skin-muted hover:text-skin-text hover:bg-skin-card/50'}"
        on:click={() => dispatch("navigate", "council")}
      >
        <div class="flex items-center gap-2">
          <!-- Icon placeholder if Lucide icon not available or reuse BrainCircuit -->
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="lucide lucide-users"
            ><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle
              cx="9"
              cy="7"
              r="4"
            /><path d="M22 21v-2a4 4 0 0 0-3-3.87" /><path
              d="M16 3.13a4 4 0 0 1 0 7.75"
            /></svg
          >
          <span>The Council</span>
        </div>
      </button>
    </nav>
  </div>

  <div class="px-5 flex-1 overflow-y-auto">
    <div class="pt-4 border-t border-skin-border">
      <!-- DYNAMIC CONTENT AREA -->

      {#if activeView === "portfolio"}
        <!-- PORTFOLIO / DASHBOARD CONTROLS -->
        <div
          class="space-y-6 animate-in slide-in-from-left-2 fade-in duration-300"
        >
          <!-- Interface Style (Structure) -->
          <div>
            <div
              class="flex items-center gap-2 text-[11px] font-medium text-skin-muted uppercase tracking-wider mb-2 px-2"
            >
              <Monitor size={12} />
              <span>Layout Base</span>
            </div>
            <div class="grid grid-cols-1 gap-1">
              {#each Object.entries(bases) as [key, val]}
                <button
                  class="text-left px-3 py-1.5 rounded-md text-xs font-medium transition-all {$currentBase ===
                  key
                    ? 'bg-skin-card text-skin-text border border-skin-border shadow-sm'
                    : 'text-skin-muted hover:text-skin-text'}"
                  on:click={() => currentBase.set(key)}
                >
                  {val.name}
                </button>
              {/each}
            </div>
          </div>

          <!-- Background Scene -->
          <div>
            <div
              class="flex items-center gap-2 text-[11px] font-medium text-skin-muted uppercase tracking-wider mb-2 px-2"
            >
              <Globe size={12} />
              <span>Scene</span>
            </div>
            <div class="grid grid-cols-2 gap-1.5 px-1">
              {#each Object.entries(scenes) as [key, val]}
                <button
                  class="text-xs px-2 py-1.5 rounded border border-skin-border transition-all text-center
                  {$currentScene === key
                    ? 'bg-skin-accent/10 border-skin-accent text-skin-accent shadow-[0_0_10px_rgba(var(--accent-primary),0.2)]'
                    : 'bg-skin-card/50 text-skin-muted hover:text-skin-text hover:border-skin-muted'}"
                  on:click={() => currentScene.set(key)}
                >
                  {val.name}
                </button>
              {/each}
            </div>
          </div>

          <!-- Color Palette -->
          <div>
            <div
              class="flex items-center gap-2 text-[11px] font-medium text-skin-muted uppercase tracking-wider mb-2 px-2"
            >
              <Palette size={12} />
              <span>Palette</span>
            </div>
            <div class="flex flex-wrap gap-2 px-2">
              {#each Object.entries(palettes) as [key, val]}
                <button
                  class="w-6 h-6 rounded-full border border-skin-border transition-transform hover:scale-110 {$currentPalette ===
                  key
                    ? 'ring-2 ring-skin-text ring-offset-2 ring-offset-skin-base'
                    : ''}"
                  style="background-color: {val.colors['--chart-1']}"
                  on:click={() => currentPalette.set(key)}
                  title={val.name}
                ></button>
              {/each}
            </div>
          </div>
        </div>
      {:else if activeView === "intelligence"}
        <!-- INTELLIGENCE CONTROLS -->
        <div class="animate-in slide-in-from-left-2 fade-in duration-300">
          <button
            class="flex items-center justify-between w-full text-[11px] font-medium text-skin-muted uppercase tracking-wider mb-2 px-2 hover:text-skin-text transition-colors"
            on:click={() => (sourcesExpanded = !sourcesExpanded)}
          >
            <span>Manage Sources</span>
            <Plus
              size={12}
              class="transition-transform duration-200 {sourcesExpanded
                ? 'rotate-45'
                : ''}"
            />
          </button>

          {#if sourcesExpanded}
            <div class="space-y-2 mb-6">
              <div class="flex gap-2">
                <input
                  type="text"
                  bind:value={newChannel}
                  placeholder="@Handle"
                  class="bg-skin-card border border-skin-border rounded px-2 py-1 text-xs w-full focus:outline-none focus:border-skin-accent/50 transition-all font-mono text-skin-text placeholder:text-skin-muted"
                />
                <button
                  on:click={addSource}
                  disabled={!newChannel || loadingSources}
                  class="bg-skin-card border border-skin-border rounded px-2 hover:bg-skin-card hover:border-skin-muted transition-all disabled:opacity-50 text-skin-text"
                >
                  <Plus size={12} />
                </button>
              </div>

              <div class="space-y-0.5 max-h-48 overflow-y-auto scrollbar-hide">
                {#each channels as channel}
                  <div
                    class="flex items-center gap-2 text-xs text-skin-muted px-2 py-1 hover:text-skin-text transition-colors"
                  >
                    <Youtube size={12} />
                    <span>
                      {typeof channel === "string"
                        ? channel
                        : channel.handle +
                          (channel.filter_keyword
                            ? ` [${channel.filter_keyword}]`
                            : "")}
                    </span>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
        </div>
      {/if}
    </div>
  </div>

  <div class="p-4 border-t border-skin-border mt-auto bg-skin-sidebar/50">
    <button
      on:click={triggerRefresh}
      class="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md bg-skin-card border border-skin-border hover:border-skin-muted text-skin-text text-xs font-medium tracking-wide transition-all shadow-sm group"
    >
      <RefreshCw
        size={12}
        class="group-hover:rotate-180 transition-transform duration-500"
      />
      Refresh Data
    </button>
  </div>
</aside>
