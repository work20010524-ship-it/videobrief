<template>
  <section id="pricing" class="py-16 sm:py-20 bg-white" aria-labelledby="pricing-heading">
    <div class="max-w-7xl mx-auto px-4 sm:px-6">
      <div class="text-center mb-12">
        <h2 id="pricing-heading" class="text-2xl sm:text-3xl font-bold text-text-primary mb-3">
          选择适合你的会员方案
        </h2>
        <p class="text-text-secondary text-base max-w-xl mx-auto">
          先用 Free 和 Pro 跑通产品，再逐步把 Go / Plus 补成完整的分层会员体系
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
          class="relative rounded-2xl p-7 flex flex-col overflow-hidden border"
        >
          <div v-if="plan.key === 'pro'" class="absolute -top-20 -right-20 w-56 h-56 bg-white/5 rounded-full"></div>
          <div v-if="plan.badge" :class="badgeClass(plan)" class="absolute top-4 right-4 px-3 py-1 rounded-full text-xs font-medium backdrop-blur-sm">
            {{ plan.badge }}
          </div>
          <div class="relative">
            <div class="mb-6">
              <h3 :class="titleClass(plan)" class="text-lg font-semibold mb-1">{{ plan.name }}</h3>
              <p :class="descClass(plan)" class="text-sm">{{ plan.description }}</p>
            </div>
            <div class="mb-6">
              <span :class="priceClass(plan)" class="text-4xl font-bold">
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
              :disabled="plan.action === 'planned'"
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
    emit('open-vip')
  }
}

function cardClass(plan) {
  if (plan.key === 'pro') return 'bg-gradient-to-br from-primary to-blue-600 text-white border-transparent shadow-xl'
  if (plan.action === 'planned') return 'bg-slate-50 text-text-primary border-slate-200'
  return 'bg-white text-text-primary border-border'
}

function badgeClass(plan) {
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
  if (plan.action === 'planned') {
    return 'bg-white text-slate-400 border border-slate-200 cursor-not-allowed'
  }
  if (plan.key === 'pro') {
    return 'bg-white text-primary hover:bg-white/90 cursor-pointer'
  }
  return props.user
    ? 'bg-gray-50 text-text-primary border border-border cursor-default'
    : 'bg-white text-text-primary border border-border hover:bg-gray-50 cursor-pointer'
}

function buttonLabel(plan) {
  if (plan.action === 'planned') return '即将开放'
  if (plan.action === 'login') return props.user ? '当前方案' : '免费开始'
  if (plan.action === 'open-vip') return props.user?.is_vip ? '续费 Pro' : '立即开通 Pro'
  return '查看详情'
}
</script>
