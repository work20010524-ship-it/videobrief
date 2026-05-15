<template>
  <section id="features" class="relative overflow-hidden py-16 sm:py-24 bg-bg-main paper-noise" aria-labelledby="features-heading">
    <div class="relative max-w-7xl mx-auto px-4 sm:px-6">
      <div class="mx-auto mb-12 max-w-3xl text-center">
        <p class="mb-3 text-xs font-black uppercase tracking-[0.32em] text-primary">不只是下载</p>
        <h2 id="features-heading" class="display-font text-3xl sm:text-5xl font-black text-text-primary mb-4">
          为什么选择 <span class="text-primary">{{ siteConfig.name }}</span>
        </h2>
        <p class="text-text-secondary text-base sm:text-lg leading-8">
          它更像一个视频内容研究工作台：先拿到内容，再把内容变成可读、可搜、可追问的知识资产。
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-6 gap-5">
        <article
          v-for="(feature, index) in siteConfig.features"
          :key="feature.title"
          :class="featureCardClass(index)"
          class="group relative overflow-hidden rounded-[1.75rem] border border-white/70 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)] lift-hover"
        >
          <div class="absolute -right-12 -top-12 h-32 w-32 rounded-full bg-white/30 blur-2xl transition-transform group-hover:scale-125"></div>
          <div class="relative w-13 h-13 rounded-2xl flex items-center justify-center mb-5 text-2xl shadow-sm"
            :class="feature.bgClass" role="img" :aria-label="feature.title">
            {{ feature.icon }}
          </div>
          <h3 class="relative text-lg font-black text-text-primary mb-2">{{ feature.title }}</h3>
          <p class="relative text-sm text-text-secondary leading-7">{{ feature.desc }}</p>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup>
import { siteConfig } from '../config/site.js'

function featureCardClass(index) {
  const spans = [
    'md:col-span-3 bg-white/78',
    'md:col-span-3 bg-[#e7fff1]/82',
    'md:col-span-2 bg-[#e6f7ff]/82',
    'md:col-span-2 bg-white/78',
    'md:col-span-2 bg-[#fff3d6]/86',
  ]
  return spans[index] || 'md:col-span-2 bg-white/78'
}
</script>
