<script>
  import Sidebar from "./lib/Sidebar.svelte";
  import Dashboard from "./lib/Dashboard.svelte";
  import Intelligence from "./lib/Intelligence.svelte";
  import TheCouncil from "./lib/TheCouncil.svelte";
  import AlertManager from "./lib/AlertManager.svelte";
  import Analytics from "./lib/Analytics.svelte";
  import { themeState } from "./lib/stores/theme.js";

  let currentView = "portfolio"; // 'portfolio' | 'intelligence' | 'council' | 'alerts' | 'analytics'
  let refreshTrigger = 0;

  function handleNavigate(event) {
    currentView = event.detail;
  }

  function handleRefresh() {
    refreshTrigger += 1;
  }

  // Reactive CSS variables injection
  $: {
    if (typeof document !== "undefined") {
      Object.entries($themeState)
        .filter(([key]) => key.startsWith("--"))
        .forEach(([key, value]) => {
          document.documentElement.style.setProperty(key, value);
        });
    }
  }
</script>

<main
  class="flex h-screen w-full bg-skin-base overflow-hidden font-sans text-skin-text antialiased transition-colors duration-300"
>
  <!-- DYNAMIC SCENE BACKGROUND -->
  <div
    class="absolute inset-0 z-0 pointer-events-none overflow-hidden transition-all duration-700 ease-in-out"
    style={$themeState.sceneData.css}
  >
    <!-- Overlay Gradient/Orbs -->
    {#if $themeState.sceneData.overlay}
      <div
        class="absolute inset-0 transition-opacity duration-1000"
        style="background: {$themeState.sceneData.overlay}; opacity: 0.6;"
      ></div>
    {/if}

    <!-- Special Cyber Grid (Only for Cyber Scene) -->
    {#if $themeState.scene === "cyber"}
      <div
        class="absolute inset-0 bg-[linear-gradient(rgba(18,18,23,0)_1px,transparent_1px),linear-gradient(90deg,rgba(18,18,23,0)_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_60%_60%_at_50%_50%,#000_70%,transparent_100%)] opacity-20"
      ></div>
    {/if}

    <!-- Subtle Noise Texture (Global) -->
    <div
      class="absolute inset-0 opacity-[0.03] mix-blend-overlay"
      style="background-image: url('data:image/svg+xml,%3Csvg viewBox=%220 0 200 200%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noise%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.65%22 numOctaves=%223%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noise)%22 opacity=%221%22/%3E%3C/svg%3E');"
    ></div>
  </div>

  <!-- Sidebar -->
  <Sidebar
    activeView={currentView}
    on:navigate={handleNavigate}
    on:refresh={handleRefresh}
  />

  <!-- Main Content -->
  <div class="flex-1 flex flex-col h-full overflow-hidden relative z-10">
    <!-- Scrollable Area -->
    <div class="flex-1 overflow-y-auto p-6 md:p-8 relative scrollbar-hide">
      {#if currentView === "portfolio"}
        <Dashboard {refreshTrigger} />
      {:else if currentView === "intelligence"}
        <Intelligence />
      {:else if currentView === "council"}
        <TheCouncil />
      {:else if currentView === "alerts"}
        <AlertManager />
      {:else if currentView === "analytics"}
        <Analytics />
      {/if}
    </div>
  </div>
</main>

<style>
  /* Custom scrollbar hiding */
  .scrollbar-hide::-webkit-scrollbar {
    display: none;
  }
  .scrollbar-hide {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
</style>
