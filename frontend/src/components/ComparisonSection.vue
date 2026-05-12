<template>
  <section id="comparison" class="py-16 sm:py-20 bg-bg-section" aria-labelledby="comparison-heading">
    <div class="max-w-5xl mx-auto px-4 sm:px-6">
      <div class="text-center mb-12">
        <h2 id="comparison-heading" class="text-2xl sm:text-3xl font-bold text-text-primary mb-3">
          {{ siteConfig.comparison.title }}
        </h2>
        <p class="text-text-secondary text-base max-w-xl mx-auto">
          {{ siteConfig.comparison.description }}
        </p>
      </div>

      <div class="overflow-x-auto rounded-2xl border border-border-light shadow-sm">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-gray-50 text-text-primary">
              <th class="text-left px-5 py-3.5 font-semibold">功能对比</th>
              <th class="px-5 py-3.5 font-semibold text-primary">{{ siteConfig.name }}</th>
              <th class="px-5 py-3.5 font-semibold">其他在线工具</th>
              <th class="px-5 py-3.5 font-semibold">桌面下载软件</th>
            </tr>
          </thead>
          <tbody class="bg-white">
            <tr v-for="(row, i) in siteConfig.comparison.rows" :key="row.feature" :class="i % 2 === 1 ? 'bg-gray-50/50' : ''">
              <td class="px-5 py-3 text-text-primary font-medium">{{ row.feature }}</td>
              <td class="px-5 py-3 text-center">
                <span v-if="row.saveany === true" class="text-success text-base">✓</span>
                <span v-else-if="row.saveany === false" class="text-text-muted">✗</span>
                <span v-else class="text-text-primary">{{ row.saveany }}</span>
              </td>
              <td class="px-5 py-3 text-center text-text-secondary">
                <span v-if="row.online === true" class="text-success text-base">✓</span>
                <span v-else-if="row.online === false" class="text-text-muted">✗</span>
                <span v-else>{{ row.online }}</span>
              </td>
              <td class="px-5 py-3 text-center text-text-secondary">
                <span v-if="row.desktop === true" class="text-success text-base">✓</span>
                <span v-else-if="row.desktop === false" class="text-text-muted">✗</span>
                <span v-else>{{ row.desktop }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<script setup>
import { siteConfig } from '../config/site.js'
</script>
