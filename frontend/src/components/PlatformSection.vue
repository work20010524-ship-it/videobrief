<template>
  <section id="platforms" class="py-16 sm:py-24 bg-bg-main" aria-labelledby="platforms-heading">
    <div class="max-w-6xl mx-auto px-4 sm:px-6">
      <div class="text-center mb-12">
        <p class="mb-3 text-xs font-black uppercase tracking-[0.32em] text-primary">Platform canvas</p>
        <h2 id="platforms-heading" class="display-font text-3xl sm:text-5xl font-black text-text-primary mb-4">
          支持全球 <span class="text-primary">{{ siteConfig.supportPlatformCount }}</span> 视频平台
        </h2>
        <p class="text-text-secondary text-base sm:text-lg max-w-xl mx-auto leading-8">
          覆盖主流视频、音频、社交媒体平台，便于继续拓展成下载、整理和知识处理型工具
        </p>
      </div>

      <div class="flex flex-wrap justify-center gap-3 sm:gap-4 max-w-4xl mx-auto">
        <div
          v-for="platform in siteConfig.platforms"
          :key="platform.name"
          class="inline-flex items-center gap-2 px-4 sm:px-5 py-2.5 bg-white/72 rounded-full border border-white/80 shadow-sm hover:shadow-lg hover:-translate-y-1 hover:border-primary/30 transition-all backdrop-blur"
        >
          <span class="text-lg">{{ platform.icon }}</span>
          <span class="text-sm font-medium text-text-primary">{{ platform.name }}</span>
        </div>
      </div>

      <p class="text-center mt-8 text-sm text-text-muted">
        ...以及更多可由 yt-dlp 与定制解析逻辑继续扩展的平台和内容源
      </p>
    </div>
  </section>
</template>

<script setup>
import { siteConfig } from '../config/site.js'
</script>
