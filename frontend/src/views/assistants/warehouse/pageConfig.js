/** AI仓库助手 — 页面文案与 KPI */
export const warehousePageConfig = {
  title: 'AI仓库助手',
  subtitle: '库存周转、仓储作业与物流调度',
  avatar: '/avatars/assistant-warehouse.png',
  accent: '#22c55e',
  layout: 'warehouse-layout',
  route: '/assistant/warehouse',
  greeting: '你好，我是AI仓库助手，可以帮你分析库存、库位、收发货效率和异常预警。',
  prompts: ['库存周转是否健康？', '哪些物料低于安全库存？', '今日出入库效率如何？'],
  homeDetails: [
    {
      title: '智能库存管理',
      desc: '实时监控库存水平，智能预警缺货与滞销，优化库存结构，降低资金占用。'
    }
  ],
  kpis: [
    { label: '库存准确率', value: '99.2%', trend: '+0.6%' },
    { label: '周转天数', value: '18.4', trend: '-2.3' },
    { label: '待拣任务', value: '48', trend: '+12' }
  ]
}
