<template>
  <section id="comparison" class="relative py-16 sm:py-24 bg-bg-main paper-noise" aria-labelledby="comparison-heading">
    <div class="relative max-w-6xl mx-auto px-4 sm:px-6">
      <div class="text-center mb-12">
        <p class="mb-3 text-xs font-black uppercase tracking-[0.32em] text-primary">为什么不一样</p>
        <h2 id="comparison-heading" class="display-font text-3xl sm:text-5xl font-black text-text-primary mb-4">
          {{ siteConfig.comparison.title }}
        </h2>
        <p class="text-text-secondary text-base sm:text-lg max-w-xl mx-auto leading-8">
          {{ siteConfig.comparison.description }}
        </p>
      </div>

      <div class="overflow-x-auto rounded-[2rem] border border-white/75 bg-white/72 shadow-[0_24px_80px_rgba(15,23,42,0.10)] backdrop-blur">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-[#07111f] text-white">
              <th class="text-left px-5 py-3.5 font-semibold">功能对比</th>
              <th class="px-5 py-3.5 font-semibold text-cyan-100">{{ siteConfig.name }}</th>
              <th class="px-5 py-3.5 font-semibold text-white/70">其他在线工具</th>
              <th class="px-5 py-3.5 font-semibold text-white/70">桌面下载软件</th>
            </tr>
          </thead>
          <tbody class="bg-white/78">
            <tr v-for="(row, i) in siteConfig.comparison.rows" :key="row.feature" :class="i % 2 === 1 ? 'bg-[#f8f1e5]' : ''">
              <td class="px-5 py-3 text-text-primary font-medium">{{ row.feature }}</td>
              <td class="px-5 py-3 text-center">
                <span v-if="row.saveany === true" class="inline-grid h-6 w-6 place-items-center rounded-full bg-success text-white text-sm">✓</span>
                <span v-else-if="row.saveany === false" class="text-text-muted">✗</span>
                <span v-else class="rounded-full bg-primary-light px-3 py-1 text-xs font-bold text-primary-dark">{{ row.saveany }}</span>
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
