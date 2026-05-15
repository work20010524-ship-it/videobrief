<template>
  <section id="pricing" class="relative overflow-hidden py-16 sm:py-24 bg-[#f9f4ea] paper-noise" aria-labelledby="pricing-heading">
    <div class="absolute left-8 top-20 hidden h-32 w-32 rounded-full border border-primary/20 md:block"></div>
    <div class="absolute right-8 bottom-16 hidden h-44 w-44 rounded-full border border-success/20 md:block"></div>
    <div class="max-w-7xl mx-auto px-4 sm:px-6">
      <div class="text-center mb-12">
        <p class="mb-3 text-xs font-black uppercase tracking-[0.32em] text-primary">会员权益</p>
        <h2 id="pricing-heading" class="display-font text-3xl sm:text-5xl font-black text-text-primary mb-4">
          选择适合你的会员方案
        </h2>
        <p class="text-text-secondary text-base sm:text-lg max-w-xl mx-auto leading-8">
          按你的使用频率选择合适额度：偶尔整理、日常学习或高频内容研究，都有对应方案。
        </p>
        <p class="mt-3 text-sm text-text-muted">
          {{ siteConfig.pricing.note }}
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
        <div
          v-for="plan in siteConfig.pricing.plans"
          :key="plan.key"
          :class="cardClass(plan)"
          class="relative rounded-[2rem] p-7 flex flex-col overflow-hidden border lift-hover"
        >
          <div v-if="plan.key === 'pro'" class="absolute -top-20 -right-20 w-56 h-56 bg-white/8 rounded-full"></div>
          <div v-else class="absolute -top-20 -right-16 w-48 h-48 bg-primary/8 rounded-full blur-2xl"></div>
          <div v-if="badgeLabel(plan)" :class="badgeClass(plan)" class="absolute top-4 right-4 px-3 py-1 rounded-full text-xs font-medium backdrop-blur-sm">
            {{ badgeLabel(plan) }}
          </div>
          <div class="relative">
            <div class="mb-6">
              <h3 :class="titleClass(plan)" class="text-lg font-semibold mb-1">{{ plan.name }}</h3>
              <p :class="descClass(plan)" class="text-sm">{{ plan.description }}</p>
            </div>
            <div class="mb-6">
              <span :class="priceClass(plan)" class="display-font text-5xl font-black">
                <template v-if="plan.price === '待定'">{{ plan.price }}</template>
                <template v-else>{{ siteConfig.pricingDisplay.currencySymbol }}{{ plan.price }}</template>
              </span>
              <span :class="descClass(plan)" class="text-sm ml-1">{{ plan.cycle }}</span>
            </div>
            <ul class="space-y-3 mb-8 flex-1">
              <li v-for="item in plan.features" :key="item" :class="featureClass(plan)" class="flex items-start gap-2.5 text-sm">
                <svg :class="checkClass(plan)" class="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                {{ item }}
              </li>
            </ul>
            <button
              @click="handlePlanClick(plan)"
              :disabled="plan.action === 'planned' || isLowerThanCurrentPlan(plan)"
              :class="buttonClass(plan)"
              class="w-full h-11 rounded-full text-sm font-semibold transition-colors shadow-sm"
            >
              {{ buttonLabel(plan) }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { siteConfig } from '../config/site.js'

const props = defineProps({
  user: { type: Object, default: null },
})

const emit = defineEmits(['open-vip', 'need-login'])

function handlePlanClick(plan) {
  if (isFreePlanCurrent(plan) || isLowerThanCurrentPlan(plan)) {
    return
  }
  if (plan.action === 'planned') {
    return
  }
  if (plan.action === 'login') {
    if (!props.user) emit('need-login')
    return
  }
  if (plan.action === 'open-vip') {
    if (!props.user) {
      emit('need-login')
      return
    }
    emit('open-vip', plan.key === 'pro' ? 'pro' : plan.key)
  }
}

function cardClass(plan) {
  if (plan.key === 'pro') return 'ink-card text-white border-transparent shadow-[0_32px_90px_rgba(7,17,31,0.28)]'
  if (plan.action === 'planned') return 'bg-slate-50 text-text-primary border-slate-200'
  return 'bg-white/76 text-text-primary border-white/80 shadow-[0_18px_60px_rgba(15,23,42,0.08)] backdrop-blur'
}

function badgeClass(plan) {
  if (isCurrentPlan(plan)) return plan.key === 'pro' ? 'bg-white/25 text-white' : 'bg-primary-light text-primary'
  if (plan.key === 'pro') return 'bg-white/20 text-white'
  if (plan.action === 'planned') return 'bg-slate-200 text-slate-700'
  return 'bg-primary-light text-primary'
}

function titleClass(plan) {
  return plan.key === 'pro' ? 'text-white' : 'text-text-primary'
}

function descClass(plan) {
  return plan.key === 'pro' ? 'text-white/70' : 'text-text-secondary'
}

function priceClass(plan) {
  return plan.key === 'pro' ? 'text-white' : 'text-text-primary'
}

function featureClass(plan) {
  return plan.key === 'pro' ? 'text-white/90' : 'text-text-secondary'
}

function checkClass(plan) {
  return plan.key === 'pro' ? 'text-yellow-300' : 'text-success'
}

function buttonClass(plan) {
  if (isFreePlanCurrent(plan) || isLowerThanCurrentPlan(plan)) {
    return 'bg-gray-50 text-text-primary border border-border cursor-default'
  }
  if (plan.action === 'planned') {
    return 'bg-white text-slate-400 border border-slate-200 cursor-not-allowed'
  }
  if (plan.key === 'pro') {
    return 'bg-white text-[#07111f] hover:bg-cyan-50 cursor-pointer'
  }
  return props.user
    ? 'bg-[#f8f1e5] text-text-primary border border-border cursor-default'
    : 'bg-[#07111f] text-white border border-[#07111f] hover:bg-[#102033] cursor-pointer'
}

function buttonLabel(plan) {
  if (plan.action === 'planned') return '即将开放'
  if (plan.action === 'login') {
    if (!props.user) return '免费开始'
    return getCurrentPlanKey() === 'free' ? '当前方案' : `已升级 ${getCurrentPlanName()}`
  }
  if (plan.action === 'open-vip') {
    if (!props.user) return `立即开通 ${plan.name}`
    if (isCurrentPlan(plan)) return `续费 ${plan.name}`
    if (isLowerThanCurrentPlan(plan)) return `已升级 ${getCurrentPlanName()}`
    return `升级 ${plan.name}`
  }
  return '查看详情'
}

function isCurrentPlan(plan) {
  return !!props.user && plan.key === getCurrentPlanKey()
}

function isFreePlanCurrent(plan) {
  return plan.key === 'free' && getCurrentPlanKey() === 'free'
}

function badgeLabel(plan) {
  if (isCurrentPlan(plan)) return '当前方案'
  if (plan.key === 'free' && !props.user) return '当前可用'
  return plan.badge || ''
}

function getCurrentPlanKey() {
  if (!props.user) return ''
  if (props.user.plan_tier) return props.user.plan_tier
  return props.user.is_vip ? 'pro' : 'free'
}

function getCurrentPlanName() {
  const names = { free: 'Free', go: 'Go', plus: 'Plus', pro: 'Pro' }
  return names[getCurrentPlanKey()] || 'Free'
}

function isLowerThanCurrentPlan(plan) {
  if (!props.user) return false
  const rank = { free: 0, go: 1, plus: 2, pro: 3 }
  return (rank[plan.key] ?? 0) < (rank[getCurrentPlanKey()] ?? 0)
}
</script>
