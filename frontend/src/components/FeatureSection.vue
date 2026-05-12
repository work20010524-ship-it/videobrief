<template>
  <section id="features" class="py-16 sm:py-20 bg-bg-section" aria-labelledby="features-heading">
    <div class="max-w-6xl mx-auto px-4 sm:px-6">
      <div class="text-center mb-12">
        <h2 id="features-heading" class="text-2xl sm:text-3xl font-bold text-text-primary mb-3">
          为什么选择 <span class="text-primary">{{ siteConfig.name }}</span>
        </h2>
        <p class="text-text-secondary text-base max-w-xl mx-auto">
          从视频解析到内容理解，完整覆盖下载、字幕、摘要和会员化扩展能力
        </p>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-5">
        <article
          v-for="feature in siteConfig.features"
          :key="feature.title"
          class="group bg-white rounded-2xl p-6 border border-border-light shadow-sm hover:shadow-md hover:border-primary/20 transition-all"
        >
          <div class="w-12 h-12 rounded-xl flex items-center justify-center mb-4 text-2xl"
            :class="feature.bgClass" role="img" :aria-label="feature.title">
            {{ feature.icon }}
          </div>
          <h3 class="text-base font-semibold text-text-primary mb-2">{{ feature.title }}</h3>
          <p class="text-sm text-text-secondary leading-relaxed">{{ feature.desc }}</p>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup>
import { siteConfig } from '../config/site.js'
</script>
