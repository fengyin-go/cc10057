<template>
  <div class="app-shell">
    <aside class="app-side">
      <h1 class="app-title">零售货架陈列图像稽核采集平台</h1>
      <nav class="nav-list">
        <RouterLink v-for="item in navItems" :key="item.path" :to="item.path" class="nav-item">
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>
    <main class="app-main">
      <header class="app-head">
        <span class="head-desc">采集货架陈列图像，完成去重、检测、识别与排面计数，对照陈列标准输出缺货价签差异与证据包的图像稽核采集平台</span>
        <span class="head-user">当前值班：数据工程组</span>
      </header>
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
const navItems = [{ label: "运营概览", path: "/" }, { label: "门店名录", path: "/store_list" }, { label: "货架稽核任务", path: "/shelf_task" }, { label: "图像上传通道", path: "/image_upload" }, { label: "图像去重", path: "/image_dedup" }, { label: "货架检测", path: "/shelf_detect" }, { label: "商品识别", path: "/sku_recognize" }, { label: "排面计数", path: "/facing_count" }, { label: "陈列标准库", path: "/planogram_lib" }, { label: "缺货检查", path: "/gap_check" }, { label: "价签核对", path: "/price_tag_check" }, { label: "稽核结果汇总", path: "/audit_result" }, { label: "人工复核台", path: "/audit_review" }, { label: "巡检路线规划", path: "/field_route" }, { label: "采集设备管理", path: "/device_mgr" }, { label: "上传重试队列", path: "/upload_retry" }, { label: "稽核证据包", path: "/evidence_pack" }, { label: "稽核导出中心", path: "/audit_export" }, { label: "门店得分卡", path: "/score_card" }, { label: "稽核归档", path: "/audit_archive" }]
</script>
