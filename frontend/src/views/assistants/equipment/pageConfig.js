/** AI设备助手 — 页面文案与 KPI */
export const equipmentPageConfig = {
  title: 'AI设备助手',
  subtitle: '设备状态监控、预测维护与故障诊断',
  avatar: '/avatars/assistant-equipment.png',
  accent: '#06b6d4',
  layout: 'equipment-layout',
  route: '/assistant/equipment',
  greeting: '你好，我是AI设备助手，可以帮你分析设备状态、故障风险和维护计划。',
  prompts: ['哪些设备存在停机风险？', '生成本周保养计划', '分析设备异常原因'],
  homeDetails: [
    {
      title: '设备预测性维护',
      desc: '实时监控设备状态，智能预测故障风险，提前安排维护计划，减少停机时间，降低维护成本。'
    }
  ],
  kpis: [
    { label: '设备健康度', value: '91.6%', trend: '+3.4%' },
    { label: '预测告警', value: '12', trend: '-5' },
    { label: '平均停机', value: '1.8h', trend: '-0.7h' }
  ]
}
