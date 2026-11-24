<template>
  <section class="page">
    <header class="page-head">
      <div>
        <h2>运营概览</h2>
        <p class="page-desc">汇总各业务模块的关键指标，先看总量再看异常。</p>
      </div>
    </header>
    <div class="stat-row">
      <article v-for="card in cards" :key="card.label" class="stat-card">
        <span class="stat-label">{{ card.label }}</span>
        <strong class="stat-value">{{ card.value }}</strong>
      </article>
    </div>
    <table class="data-table">
      <thead>
        <tr><th>业务模块</th><th>今日新增</th><th>待处理</th><th>异常量</th></tr>
      </thead>
      <tbody>
        <tr v-for="row in moduleRows" :key="row.name">
          <td>{{ row.name }}</td>
          <td>{{ row.created }}</td>
          <td>{{ row.pending }}</td>
          <td>{{ row.abnormal }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { fetchJson } from '@/api/client'

type Overview = {
  cards: { label: string; value: number }[]
  modules: { name: string; created: number; pending: number; abnormal: number }[]
}

const cards = ref<Overview['cards']>([])
const moduleRows = ref<Overview['modules']>([])

onMounted(async () => {
  try {
    const payload = await fetchJson<Overview>('/api/overview')
    cards.value = payload.cards
    moduleRows.value = payload.modules
  } catch {
    cards.value = [{"label": "业务模块", "value": 0}, {"label": "今日新增", "value": 0}]
    moduleRows.value = [{"name": "门店名录", "created": 0, "pending": 0, "abnormal": 0}, {"name": "货架稽核任务", "created": 0, "pending": 0, "abnormal": 0}, {"name": "图像上传通道", "created": 0, "pending": 0, "abnormal": 0}, {"name": "图像去重", "created": 0, "pending": 0, "abnormal": 0}, {"name": "货架检测", "created": 0, "pending": 0, "abnormal": 0}, {"name": "商品识别", "created": 0, "pending": 0, "abnormal": 0}, {"name": "排面计数", "created": 0, "pending": 0, "abnormal": 0}, {"name": "陈列标准库", "created": 0, "pending": 0, "abnormal": 0}, {"name": "缺货检查", "created": 0, "pending": 0, "abnormal": 0}, {"name": "价签核对", "created": 0, "pending": 0, "abnormal": 0}, {"name": "稽核结果汇总", "created": 0, "pending": 0, "abnormal": 0}, {"name": "人工复核台", "created": 0, "pending": 0, "abnormal": 0}, {"name": "巡检路线规划", "created": 0, "pending": 0, "abnormal": 0}, {"name": "采集设备管理", "created": 0, "pending": 0, "abnormal": 0}, {"name": "上传重试队列", "created": 0, "pending": 0, "abnormal": 0}, {"name": "稽核证据包", "created": 0, "pending": 0, "abnormal": 0}, {"name": "稽核导出中心", "created": 0, "pending": 0, "abnormal": 0}, {"name": "门店得分卡", "created": 0, "pending": 0, "abnormal": 0}, {"name": "稽核归档", "created": 0, "pending": 0, "abnormal": 0}]
  }
})
</script>
