/** AI质量助手 — 页面文案与 KPI */
export const qualityPageConfig = {
  title: 'AI质量助手',
  subtitle: '质量检测、缺陷分析与持续改进',
  avatar: '/avatars/assistant-quality.png',
  accent: '#a78bfa',
  layout: 'quality-layout',
  route: '/assistant/quality',
  greeting: '你好，我是AI质量助手，可以帮你分析质量异常、缺陷分布和改善建议。',
  prompts: ['本周质量异常有哪些？', '分析不良原因排行', '生成质量改善建议'],
  homeDetails: [
    {
      title: '质量智能分析',
      desc: '实时分析生产质量数据，智能识别质量问题根源，提供改进建议，持续提升产品品质。'
    }
  ],
  kpis: [
    { label: '一次合格率', value: '98.7%', trend: '+1.1%' },
    { label: '异常批次', value: '7', trend: '-3' },
    { label: '闭环率', value: '94.5%', trend: '+5.8%' }
  ]
}
