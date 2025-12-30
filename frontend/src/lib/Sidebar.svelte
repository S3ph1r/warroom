<script>
  import { createEventDispatcher } from "svelte";

  // Sidebar visibility state
  let sidebarOpen = true;
  import {
    LayoutDashboard,
    BrainCircuit,
    RefreshCw,
    Plus,
    Youtube,
    Palette,
    Monitor,
    Globe,
    Minus,
    Bell,
    BarChart3,
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
  const API_BASE = "";

  let sourcesExpanded = true;
  let newChannel = "";
  let channels = [];
  let rssFeeds = [];
  let loadingSources = false;

  // Hover state for categories
  let youtubeExpanded = false;
  let rssExpanded = false;

  async function fetchSources() {
    try {
      const res = await fetch(`${API_BASE}/api/sources`);
      if (res.ok) {
        const data = await res.json();
        channels = data.youtube_channels || [];
        rssFeeds = data.rss_feeds || [];
        console.log("Sources loaded:", channels.length, rssFeeds.length);
      }
    } catch (e) {
      console.error("Failed to load sources", e);
    }
  }

  async function removeSource(handle) {
    if (!confirm(`Are you sure you want to remove ${handle}?`)) return;
    try {
      const res = await fetch(
        `${API_BASE}/api/sources?handle=${encodeURIComponent(handle)}`,
        {
          method: "DELETE",
        },
      );
      if (res.ok) {
        fetchSources();
      }
    } catch (e) {
      console.error("Failed to delete", e);
    }
  }

  async function addSource() {
    if (!newChannel) return;
    try {
      loadingSources = true;
      const payload = {};
      if (
        newChannel.includes("youtube.com") ||
        newChannel.includes("youtu.be")
      ) {
        payload.url = newChannel;
      } else {
        payload.handle = newChannel;
      }

      await fetch(`${API_BASE}/api/sources`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
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

<div
  class="fixed top-1/2 -translate-y-1/2 z-50 transition-all duration-300 {sidebarOpen
    ? 'left-64'
    : 'left-0'}"
>
  <button
    class="p-2 bg-skin-card border border-skin-border rounded-r-md shadow-md text-skin-text hover:bg-skin-accent/10"
    on:click={() => (sidebarOpen = !sidebarOpen)}
    >{sidebarOpen ? "←" : "→"}</button
  >
</div>

<aside
  class="{sidebarOpen
    ? 'w-64'
    : 'w-0'} h-full border-r border-skin-border bg-skin-sidebar flex flex-col shrink-0 z-20 transition-all duration-300 overflow-hidden backdrop-blur-md"
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

      <button
        class="w-full flex items-center gap-3 px-3 py-1.5 rounded-md text-sm transition-all duration-200 font-medium {activeView ===
        'alerts'
          ? 'bg-skin-card text-skin-text border border-skin-border shadow-sm'
          : 'text-skin-muted hover:text-skin-text hover:bg-skin-card/50'}"
        on:click={() => dispatch("navigate", "alerts")}
      >
        <Bell size={14} />
        <span>Alerts</span>
      </button>

      <button
        class="w-full flex items-center gap-3 px-3 py-1.5 rounded-md text-sm transition-all duration-200 font-medium {activeView ===
        'analytics'
          ? 'bg-skin-card text-skin-text border border-skin-border shadow-sm'
          : 'text-skin-muted hover:text-skin-text hover:bg-skin-card/50'}"
        on:click={() => dispatch("navigate", "analytics")}
      >
        <BarChart3 size={14} />
        <span>Analytics</span>
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
          <div class="space-y-4 mb-6">
            <!-- ADD INPUT -->
            <div class="flex gap-2">
              <input
                type="text"
                bind:value={newChannel}
                placeholder="Ispeziona URL YouTube..."
                class="bg-skin-card border border-skin-border rounded px-2 py-1 text-xs w-full focus:outline-none focus:border-skin-accent/50 transition-all font-mono text-skin-text placeholder:text-skin-muted"
                on:keydown={(e) => e.key === "Enter" && addSource()}
              />
              <button
                on:click={addSource}
                disabled={!newChannel || loadingSources}
                class="bg-skin-card border border-skin-border rounded px-2 hover:bg-skin-card hover:border-skin-muted transition-all disabled:opacity-50 text-skin-text"
              >
                {#if loadingSources}
                  <div
                    class="w-3 h-3 border-2 border-skin-text border-t-transparent rounded-full animate-spin"
                  ></div>
                {:else}
                  <Plus size={12} />
                {/if}
              </button>
            </div>

            <!-- YOUTUBE GROUP -->
            <div
              class="group relative"
              on:mouseenter={() => (youtubeExpanded = true)}
              on:mouseleave={() => (youtubeExpanded = false)}
              role="group"
              aria-label="YouTube Sources"
            >
              <div
                class="flex items-center gap-2 px-2 py-1 text-xs font-semibold text-skin-text bg-skin-card/50 rounded border border-transparent group-hover:border-skin-border cursor-default transition-colors"
              >
                <Youtube size={12} class="text-red-500" />
                <span>YouTube Sources</span>
                <span class="ml-auto text-skin-muted text-[10px]"
                  >{channels.length}</span
                >
              </div>

              {#if youtubeExpanded}
                <div
                  class="w-full bg-skin-sidebar/50 border-l-2 border-skin-border ml-2 pl-2 mt-1 space-y-0.5 animate-in slide-in-from-top-1 fade-in duration-200"
                >
                  {#each channels as channel}
                    <div
                      class="group/item flex items-center justify-between gap-2 text-xs text-skin-muted px-2 py-1 hover:text-skin-text hover:bg-white/5 rounded transition-colors"
                    >
                      <span
                        class="truncate"
                        title={typeof channel === "string"
                          ? channel
                          : channel.handle}
                      >
                        {typeof channel === "string"
                          ? channel
                          : channel.name || channel.handle}
                      </span>

                      <div
                        class="flex items-center gap-1 opacity-0 group-hover/item:opacity-100 transition-opacity"
                      >
                        {#if typeof channel !== "string" && channel.strategy}
                          <span
                            class="text-[9px] px-1 py-0.5 rounded border border-skin-border font-mono opacity-50"
                            title={channel.strategy}
                          >
                            {channel.strategy
                              .replace("STRATEGY_", "")
                              .substring(0, 4)}
                          </span>
                        {/if}
                        <button
                          on:click|stopPropagation={() =>
                            removeSource(
                              typeof channel === "string"
                                ? channel
                                : channel.handle,
                            )}
                          class="text-skin-muted hover:text-red-400 p-0.5 transition-colors"
                          title="Remove Source"
                        >
                          <Minus size={10} />
                        </button>
                      </div>
                    </div>
                  {/each}
                  {#if channels.length === 0}
                    <div
                      class="px-2 py-2 text-center text-[10px] text-skin-muted"
                    >
                      Nessun canale
                    </div>
                  {/if}
                </div>
              {/if}
            </div>

            <!-- RSS GROUP -->
            <div
              class="group relative"
              on:mouseenter={() => (rssExpanded = true)}
              on:mouseleave={() => (rssExpanded = false)}
              role="group"
              aria-label="RSS Sources"
            >
              <div
                class="flex items-center gap-2 px-2 py-1 text-xs font-semibold text-skin-text bg-skin-card/50 rounded border border-transparent group-hover:border-skin-border cursor-default transition-colors"
              >
                <Globe size={12} class="text-blue-500" />
                <span>RSS Feeds</span>
                <span class="ml-auto text-skin-muted text-[10px]"
                  >{rssFeeds.length}</span
                >
              </div>

              {#if rssExpanded}
                <div
                  class="w-full bg-skin-sidebar/50 border-l-2 border-skin-border ml-2 pl-2 mt-1 space-y-0.5 animate-in slide-in-from-top-1 fade-in duration-200"
                >
                  {#each rssFeeds as feed}
                    <div
                      class="group/item flex items-center justify-between gap-2 text-xs text-skin-muted px-2 py-1 hover:text-skin-text hover:bg-white/5 rounded transition-colors"
                    >
                      <span
                        class="truncate"
                        title={Array.isArray(feed) ? feed[0] : feed}
                      >
                        {Array.isArray(feed) ? feed[1] || feed[0] : feed}
                      </span>

                      <div
                        class="flex items-center gap-1 opacity-0 group-hover/item:opacity-100 transition-opacity"
                      >
                        <button
                          on:click|stopPropagation={() =>
                            removeSource(Array.isArray(feed) ? feed[0] : feed)}
                          class="text-skin-muted hover:text-red-400 p-0.5 transition-colors"
                          title="Remove Source"
                        >
                          <Minus size={10} />
                        </button>
                      </div>
                    </div>
                  {/each}
                  {#if rssFeeds.length === 0}
                    <div
                      class="px-2 py-2 text-center text-[10px] text-skin-muted"
                    >
                      Nessun feed
                    </div>
                  {/if}
                </div>
              {/if}
            </div>
          </div>
        {/if}
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
