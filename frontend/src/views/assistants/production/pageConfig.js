/** AI生产助手 — 页面文案与 KPI（不含图表，图表见 charts.js） */
export const productionPageConfig = {
  title: 'AI生产助手',
  subtitle: '智能生产排程、产能评估与产线协同',
  avatar: '/avatars/assistant-production.png',
  accent: '#38bdf8',
  layout: 'production-layout',
  route: '/assistant/production',
  greeting: '你好，我是AI生产助手，可以帮你分析产能、排程、工单进度和瓶颈工序。',
  prompts: ['今天各产线达成率如何？', '帮我找出生产瓶颈', '生成明日排产建议'],
  homeDetails: [
    {
      title: '智能生产排程分析',
      desc: '实时精准评估产能，智能优化生产计划与资源分配，自动化排程决策，通过数据驱动实现高效生产管理。'
    }
  ],
  kpis: [
    { label: '计划达成率', value: '96.8%', trend: '+4.2%' },
    { label: '设备稼动率', value: '88.5%', trend: '+2.1%' },
    { label: '在制工单', value: '126', trend: '-8' }
  ]
}
