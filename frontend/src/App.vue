<template>
  <div id="app-root">
    <header class="app-header">
      <div class="container">
        <h1 class="app-title">
          <span class="title-full">资讯聚合平台</span>
          <span class="title-short">资讯聚合</span>
        </h1>
      </div>
    </header>
    <main class="container">
      <router-view />
    </main>
  </div>
</template>

<script setup>
// 根组件，暂无逻辑
</script>

<style scoped>
.title-short {
  display: none;
}

@media (max-width: 480px) {
  .title-full {
    display: none;
  }

  .title-short {
    display: inline;
  }
}
</style>
