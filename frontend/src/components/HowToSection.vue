<template>
  <section id="how-to-use" class="relative overflow-hidden py-16 sm:py-24 bg-[#07111f] signal-grid" aria-labelledby="howto-heading">
    <div class="absolute -left-24 top-10 h-72 w-72 rounded-full bg-primary/15 blur-3xl"></div>
    <div class="absolute -right-20 bottom-0 h-72 w-72 rounded-full bg-success/15 blur-3xl"></div>
    <div class="relative max-w-6xl mx-auto px-4 sm:px-6">
      <div class="text-center mb-12">
        <p class="mb-3 text-xs font-black uppercase tracking-[0.32em] text-success">Three-step flow</p>
        <h2 id="howto-heading" class="display-font text-3xl sm:text-5xl font-black text-white mb-4">
          如何使用 <span class="text-cyan-200">{{ siteConfig.name }}</span>
        </h2>
        <p class="text-cyan-50/68 text-base max-w-xl mx-auto leading-8">
          从粘贴链接到生成知识摘要，3 步完成你的视频处理流程
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8">
        <article v-for="step in siteConfig.steps" :key="step.number" class="relative rounded-[1.75rem] border border-white/12 bg-white/8 p-7 text-center backdrop-blur lift-hover">
          <div class="w-15 h-15 rounded-3xl bg-white text-[#07111f] text-2xl font-black flex items-center justify-center mx-auto mb-5 shadow-[0_18px_45px_rgba(255,255,255,0.12)]">
            {{ step.number }}
          </div>
          <h3 class="text-xl font-black text-white mb-3">{{ step.title }}</h3>
          <p class="text-sm text-cyan-50/68 leading-7">{{ step.desc }}</p>
          <div v-if="step.number < 3" class="hidden md:block absolute top-1/2 -right-7 -translate-y-1/2 text-success/50" aria-hidden="true">
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </article>
      </div>

      <div class="mt-10 text-center">
        <p class="text-sm text-cyan-50/52">
          基础解析可直接体验，AI 总结和会员能力可按你的产品策略继续配置。
        </p>
      </div>
    </div>
  </section>
</template>

<script setup>
import { siteConfig } from '../config/site.js'
</script>
