<template>
  <section class="relative overflow-hidden transition-all ink-card signal-grid"
    :class="compact ? 'pt-6 pb-5 sm:pt-8 sm:pb-7' : 'pt-14 pb-14 sm:pt-24 sm:pb-20'"
  >
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
      <div class="absolute left-1/2 top-12 h-[38rem] w-[38rem] -translate-x-1/2 rounded-full border border-white/10"></div>
      <div class="absolute left-1/2 top-24 h-[28rem] w-[28rem] -translate-x-1/2 rounded-full border border-white/10"></div>
      <div class="absolute -top-40 -right-32 w-[34rem] h-[34rem] bg-primary/20 rounded-full blur-3xl"></div>
      <div class="absolute -bottom-32 -left-28 w-[30rem] h-[30rem] bg-success/20 rounded-full blur-3xl"></div>
      <div class="absolute inset-x-0 bottom-0 h-px overflow-hidden bg-white/10">
        <div class="h-full w-1/2 bg-gradient-to-r from-transparent via-success to-transparent animate-[scan-line_4s_linear_infinite]"></div>
      </div>
    </div>

    <div class="relative max-w-7xl mx-auto px-4 sm:px-6">
      <div class="grid items-center gap-10 lg:grid-cols-[1.08fr_0.92fr]">
        <div class="text-center lg:text-left reveal-up">
          <template v-if="showSlogan">
            <div class="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm text-cyan-50 shadow-2xl backdrop-blur"
              :class="compact ? 'mb-3' : 'mb-6'"
            >
              <span class="relative flex h-2.5 w-2.5">
                <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-70"></span>
                <span class="relative inline-flex h-2.5 w-2.5 rounded-full bg-success"></span>
              </span>
              {{ siteConfig.hero.badge }}
            </div>

            <h1 :class="compact ? 'text-3xl sm:text-4xl mb-3' : 'text-5xl sm:text-7xl mb-6'" class="display-font font-black leading-[0.95] text-white">
              {{ siteConfig.hero.titlePrefix }}
              <span class="block bg-gradient-to-r from-cyan-200 via-white to-emerald-200 bg-clip-text pt-2 text-transparent">
                {{ siteConfig.hero.titleHighlight }}
              </span>
            </h1>
            <p :class="compact ? 'mb-5 text-sm sm:text-base' : 'mb-9 text-base sm:text-lg'" class="max-w-2xl text-cyan-50/76 leading-8 lg:mx-0 mx-auto">
              {{ siteConfig.hero.description }}
            </p>
          </template>

          <div class="mx-auto max-w-2xl lg:mx-0">
            <form @submit.prevent="onSubmit" class="relative rounded-[2rem] border border-white/15 bg-white/10 p-2 shadow-[0_24px_80px_rgba(0,0,0,0.28)] backdrop-blur-xl" role="search" aria-label="视频链接解析">
              <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
                <div class="relative flex-1">
                  <label for="video-url-input" class="sr-only">粘贴视频链接进行解析下载</label>
                  <svg class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-cyan-100/70" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                  </svg>
                  <input
                    id="video-url-input"
                    v-model="url"
                    type="url"
                    :placeholder="siteConfig.hero.placeholder"
                    class="w-full h-13 sm:h-14 pl-12 pr-4 rounded-[1.45rem] border border-white/10 bg-[#07111f]/65 text-base text-white placeholder:text-cyan-100/42 focus:outline-none focus:ring-2 focus:ring-success/40 focus:border-success/50 transition-all"
                    :disabled="loading"
                    autocomplete="url"
                  />
                </div>
                <button
                  type="submit"
                  :disabled="loading || !url.trim()"
                  class="inline-flex h-13 sm:h-14 items-center justify-center gap-2 rounded-[1.45rem] bg-white px-7 text-base font-black text-[#07111f] shadow-[0_16px_34px_rgba(255,255,255,0.16)] transition-all hover:-translate-y-0.5 hover:bg-cyan-50 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer"
                >
                  <svg v-if="loading" class="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                  </svg>
                  {{ loading ? '解析中...' : '进入分析' }}
                </button>
              </div>
            </form>

            <div v-if="showSlogan" class="mt-5 flex flex-wrap items-center justify-center gap-3 text-xs text-cyan-50/60 lg:justify-start">
              <span>试试真实样例：</span>
              <button
                v-for="example in siteConfig.hero.examples"
                :key="example.label"
                @click="url = example.url"
                class="rounded-full border border-white/12 bg-white/8 px-3 py-1.5 text-cyan-50 transition-all hover:border-success/70 hover:bg-success/15 hover:text-white cursor-pointer"
              >
                {{ example.label }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="showSlogan" class="relative hidden lg:block">
          <div class="float-slow relative mx-auto w-full max-w-md rounded-[2.2rem] border border-white/14 bg-white/10 p-4 shadow-[0_35px_100px_rgba(0,0,0,0.36)] backdrop-blur-xl">
            <div class="rounded-[1.7rem] border border-white/10 bg-[#07111f]/80 p-5">
              <div class="mb-5 flex items-center justify-between">
                <div>
                  <p class="text-xs uppercase tracking-[0.35em] text-success/80">内容分析中</p>
                  <p class="display-font mt-1 text-2xl font-black text-white">视频知识工作台</p>
                </div>
                <div class="h-11 w-11 rounded-2xl bg-success/15 text-success grid place-items-center">
                  <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6l4 2m6-2a10 10 0 11-20 0 10 10 0 0120 0z" />
                  </svg>
                </div>
              </div>
              <div class="space-y-3">
                <div class="rounded-2xl bg-white/8 p-4">
                  <div class="mb-2 flex items-center justify-between text-xs text-cyan-50/60">
                    <span>解析链接</span><span>00:02</span>
                  </div>
                  <div class="h-2 rounded-full bg-white/10 overflow-hidden">
                    <div class="h-full w-4/5 rounded-full bg-gradient-to-r from-primary to-success"></div>
                  </div>
                </div>
                <div class="grid grid-cols-2 gap-3">
                  <div class="rounded-2xl bg-white p-4 text-[#07111f]">
                    <p class="text-xs text-text-secondary">字幕片段</p>
                    <p class="mt-2 text-3xl font-black">128</p>
                  </div>
                  <div class="rounded-2xl bg-success/15 p-4 text-white">
                    <p class="text-xs text-cyan-50/65">知识卡片</p>
                    <p class="mt-2 text-3xl font-black">4 类</p>
                  </div>
                </div>
                <div class="rounded-2xl border border-white/10 bg-white/6 p-4">
                  <div class="flex items-center gap-3">
                    <span class="h-9 w-9 rounded-full bg-primary/20 grid place-items-center text-cyan-100">AI</span>
                    <p class="text-sm leading-6 text-cyan-50/78">把视频变成摘要、字幕、思维导图和可追问的知识卡片。</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { siteConfig } from '../config/site.js'

const props = defineProps({
  loading: Boolean,
  compact: Boolean,
  showSlogan: { type: Boolean, default: true },
})
const emit = defineEmits(['parse'])

const url = ref('')

function normalizeUrl(raw) {
  let u = raw
  if (u.includes('bilibili.com') && !u.includes('www.bilibili.com')) {
    u = u.replace('bilibili.com', 'www.bilibili.com')
  }
  return u
}

function onSubmit() {
  const trimmed = url.value.trim()
  if (trimmed) {
    emit('parse', normalizeUrl(trimmed))
  }
}
</script>
