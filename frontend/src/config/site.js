const env = import.meta.env

const siteName = env.VITE_SITE_NAME || 'VideoBrief'
const siteDomain = (env.VITE_SITE_DOMAIN || 'https://video.kateai.cn').replace(/\/+$/, '')
const supportPlatformCount = env.VITE_PLATFORM_COUNT || '1800+'
const freeSummaryLimit = env.VITE_FREE_SUMMARY_LIMIT || '3'
const goSummaryLimit = env.VITE_GO_SUMMARY_LIMIT || '3'
const plusSummaryLimit = env.VITE_PLUS_SUMMARY_LIMIT || '10'
const goMonthlyPrice = env.VITE_GO_MONTHLY_PRICE || '3.9'
const plusMonthlyPrice = env.VITE_PLUS_MONTHLY_PRICE || '6.9'
const vipMonthlyPrice = env.VITE_VIP_MONTHLY_PRICE || '9.9'
const currencySymbol = env.VITE_CURRENCY_SYMBOL || '¥'
const supportEmail = env.VITE_SUPPORT_EMAIL || 'hello@kateai.cn'

export const siteConfig = {
  name: siteName,
  domain: siteDomain,
  supportEmail,
  supportPlatformCount,
  storagePrefix: env.VITE_STORAGE_PREFIX || 'videobrief',
  header: {
    badge: '视频解析与 AI 总结',
    nav: [
      { href: '#features', label: '功能特性', title: '查看核心功能' },
      { href: '#how-to-use', label: '使用流程', title: '查看使用流程' },
      { href: '#comparison', label: '能力对比', title: '查看能力对比' },
      { href: '#pricing', label: '会员方案', title: '查看会员方案' },
    ],
  },
  hero: {
    badge: `支持 ${supportPlatformCount} 平台的视频解析与字幕提取`,
    titlePrefix: '多平台视频解析',
    titleHighlight: '与 AI 总结',
    description:
      '复制视频链接，即可获取封面、标题、可选清晰度和字幕内容，并继续生成摘要、思维导图和问答，帮你更快看懂一条视频。',
    placeholder: 'https://www.youtube.com/watch?v=... 粘贴视频链接',
    examples: [
      { label: 'YouTube', url: 'https://www.youtube.com/watch?v=jNQXAC9IVRw' },
      { label: 'Bilibili', url: 'https://www.bilibili.com/video/BV1fs5b6UE4z/?spm_id_from=333.1007.tianma.2-1-3.click&vd_source=8ef95747e35324faccc116acab29a6a9' },
      { label: '抖音', url: 'https://www.douyin.com/jingxuan?modal_id=7621485780740951334' },
    ],
  },
  features: [
    {
      icon: '🌐',
      title: '多平台解析',
      desc: `覆盖 ${supportPlatformCount} 个以上视频与社交平台，常见链接粘贴即可开始整理，不需要安装额外软件。`,
      bgClass: 'bg-cyan-50',
    },
    {
      icon: '⚡',
      title: '稳定保存重点内容',
      desc: '优先提供清晰、可理解的下载选项；遇到平台限制时，也会尽量保留可阅读的标题、封面和摘要信息。',
      bgClass: 'bg-amber-50',
    },
    {
      icon: '🧾',
      title: '字幕提取与导出',
      desc: '自动提取字幕、整理时间轴，并支持导出为 SRT、VTT、TXT，适合内容归档和二次处理。',
      bgClass: 'bg-emerald-50',
    },
    {
      icon: '🧠',
      title: 'AI 摘要与问答',
      desc: '自动生成摘要、思维导图和上下文问答，把长视频转换成可以快速阅读和检索的知识内容。',
      bgClass: 'bg-rose-50',
    },
    {
      icon: '🚀',
      title: '专属内容工作台',
      desc: '把分散在不同平台的视频统一整理成可保存、可复习、可追问的知识卡片，适合学习、创作和资料归档。',
      bgClass: 'bg-violet-50',
    },
  ],
  steps: [
    {
      number: 1,
      title: '复制视频链接',
      desc: '从 YouTube、Bilibili、抖音等平台复制分享链接或地址栏 URL。',
    },
    {
      number: 2,
      title: '解析视频信息',
      desc: '粘贴链接后即可获取标题、封面、上传者、可选格式和可用字幕，快速确认内容是否值得保存。',
    },
    {
      number: 3,
      title: '下载或开始 AI 分析',
      desc: '选择清晰度后即可下载，也可以继续生成摘要、思维导图和视频问答，构建自己的内容知识库。',
    },
  ],
  comparison: {
    title: `${siteName} 与常见视频工具对比`,
    description: '不只是下载视频，更关注看懂内容、沉淀重点和后续复习。',
    rows: [
      { feature: '支持平台数量', saveany: supportPlatformCount, online: '10-50', desktop: '100-500' },
      { feature: 'AI 视频总结', saveany: true, online: false, desktop: false },
      { feature: '字幕导出', saveany: 'SRT/VTT/TXT', online: '部分支持', desktop: '部分支持' },
      { feature: '思维导图', saveany: true, online: false, desktop: false },
      { feature: '抖音无水印适配', saveany: true, online: '不稳定', desktop: '通常需登录' },
      { feature: '浏览器直接使用', saveany: true, online: true, desktop: false },
      { feature: '适合长期整理资料', saveany: true, online: '有限', desktop: '有限' },
      { feature: '手机浏览器可用', saveany: true, online: '部分支持', desktop: false },
    ],
  },
  pricing: {
    note: '不同方案对应不同的每日 AI 使用次数：Go 每日 3 次，Plus 每日 10 次，Pro 不限次数。',
    plans: [
      {
        key: 'free',
        name: 'Free',
        price: '0',
        cycle: '/永久',
        description: '用于体验解析、下载和基础 AI 能力',
        badge: '当前可用',
        action: 'login',
        features: [
          '无限次视频解析',
          '基础视频下载能力',
          '字幕提取与导出',
          `每日 ${freeSummaryLimit} 次 AI 总结`,
        ],
      },
      {
        key: 'go',
        name: 'Go',
        price: goMonthlyPrice,
        cycle: '/月',
        description: '面向轻度使用和移动端高频场景',
        badge: '轻量',
        action: 'open-vip',
        features: [
          `每日 ${goSummaryLimit} 次 AI 总结`,
          '更快的摘要生成优先级',
          '适合临时查资料和日常收藏',
          '比免费版更适合连续使用',
        ],
      },
      {
        key: 'plus',
        name: 'Plus',
        price: plusMonthlyPrice,
        cycle: '/月',
        description: '面向常规创作者与学习型用户',
        badge: '常用',
        action: 'open-vip',
        features: [
          `每日 ${plusSummaryLimit} 次 AI 总结`,
          '思维导图导出增强',
          '更丰富的历史与收藏能力',
          '适合课程学习和内容选题整理',
        ],
      },
      {
        key: 'pro',
        name: 'Pro',
        price: vipMonthlyPrice,
        cycle: '/月',
        description: '面向高频使用、内容研究和进阶会员体系',
        badge: '推荐',
        action: 'open-vip',
        features: [
          '无限次 AI 总结与问答',
          '思维导图生成与导出',
          '适合高频研究和资料归档',
          '持续处理更多长视频内容',
        ],
      },
    ],
  },
  platforms: [
    { icon: '▶️', name: 'YouTube' },
    { icon: '📺', name: 'Bilibili' },
    { icon: '🎵', name: '抖音 / TikTok' },
    { icon: '🐦', name: 'Twitter / X' },
    { icon: '📷', name: 'Instagram' },
    { icon: '📘', name: 'Facebook' },
    { icon: '🎬', name: 'Vimeo' },
    { icon: '🎧', name: 'SoundCloud' },
    { icon: '🎮', name: 'Twitch' },
    { icon: '💬', name: '微博' },
    { icon: '📌', name: 'Pinterest' },
    { icon: '📰', name: 'Reddit' },
  ],
  footer: {
    description: `${siteName} 提供视频解析、字幕提取、AI 摘要和思维导图能力，帮助你把视频内容整理成更容易复习和分享的知识资料。`,
    legal: '请仅处理拥有合法授权的内容，并遵守所在地法律法规与平台服务条款。',
  },
  meta: {
    title: env.VITE_SITE_TAGLINE || '多平台视频解析与 AI 总结平台',
    description:
      env.VITE_SITE_DESCRIPTION ||
      '多平台视频解析、字幕提取与 AI 总结工具，支持下载、思维导图和视频问答。',
    keywords:
      env.VITE_SITE_KEYWORDS ||
      '视频下载,视频解析,字幕提取,AI视频总结,思维导图,视频问答,学习整理,VideoBrief',
    ogImage: env.VITE_OG_IMAGE || `${siteDomain}/og-image.png`,
  },
  pricingDisplay: {
    currencySymbol,
  },
}
