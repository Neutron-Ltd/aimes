/** AI采购助手 — 页面文案与 KPI */
export const procurementPageConfig = {
  title: 'AI采购助手',
  subtitle: '供应商评估、采购预测与成本优化',
  avatar: '/avatars/assistant-procurement.png',
  accent: '#60a5fa',
  layout: 'procurement-layout',
  route: '/assistant/procurement',
  greeting: '你好，我是AI采购助手，可以帮你分析采购成本、供应风险和供应商表现。',
  prompts: ['本月采购成本趋势？', '哪些供应商存在风险？', '生成补货采购建议'],
  homeDetails: [
    {
      title: '智能采购决策',
      desc: '分析供应商数据，优化采购策略，智能预测价格走势，降低采购成本，确保供应链稳定。'
    }
  ],
  kpis: [
    { label: '采购节省率', value: '6.4%', trend: '+1.7%' },
    { label: '准交率', value: '93.8%', trend: '+2.4%' },
    { label: '风险供应商', value: '5', trend: '-2' }
  ]
}
