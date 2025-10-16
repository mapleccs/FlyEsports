<template>
  <div class="not-found">
    <a-result status="404" title="404" sub-title="抱歉，您访问的页面不存在。">
      <template #extra>
        <a-button type="primary" @click="$router.push('/')"> 返回首页 </a-button>
      </template>
    </a-result>
  </div>
</template>

<script setup lang="ts">
//
</script>

<style scoped>
.not-found {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
}
</style>
