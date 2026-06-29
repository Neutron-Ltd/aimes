export const messages = {
  zh: {
    header: {
      title: '宁波睿创AI工业大脑',
      weekdays: ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
    },
    common: {
      backHome: '返回首页',
      send: '发送',
      chatPlaceholder: '请输入你的业务问题...',
      aiAgent: 'AI 智能体',
      clickEnter: '点击进入 →',
      aiAnalysis: 'AI分析',
      insight: '智能洞察',
      statusAnalyzing: '实时智能分析中',
      insightTitle: '{title}已完成最新业务扫描',
      insightText: '系统结合实时指标、历史趋势和异常规则，已为你生成{subtitle}相关的重点分析建议。',
      months: ['1月', '2月', '3月', '4月', '5月', '6月'],
      chatThinking: '正在分析，请稍候...',
      chatHide: '收起助手',
      chatShow: '展开 AI 助手',
      fullscreen: '全屏',
      exitFullscreen: '退出全屏'
    },
    home: {
      heroTitle: '工业AI数字员工，赋能智造新纪元',
      heroSubtitle: '阿里千问大模型打造AI工业智能体，五大AI助手协同赋能，贯穿生产、仓储、质量、设备、采购管理全链路',
      partners: [
        { icon: '🌐', label: '阿里云' },
        { icon: '📱', label: '千问大模型' },
        { icon: '⚡', label: '睿创  Ai' }
      ]
    },
    assistants: {
      production: {
        title: 'AI生产助手',
        subtitle: '智能生产排程、产能评估与产线协同',
        greeting: '你好，我是AI生产助手，可以帮你分析产能、排程、工单进度和瓶颈工序。',
        prompts: ['今天各产线达成率如何？', '帮我找出生产瓶颈', '生成明日排产建议'],
        mockReply: '关于「{message}」：当前计划达成率 96.2%，装配二线负荷偏高。建议下午班前完成关键物料齐套，并优先压缩换型等待时间。',
        homeDetails: [{ title: '智能生产排程分析', desc: '实时精准评估产能，智能优化生产计划与资源分配，自动化排程决策，通过数据驱动实现高效生产管理。' }],
        kpiLabels: ['计划达成率', '设备稼动率', '在制工单'],
        charts: [
          { title: '产线达成趋势' },
          { title: '工单状态分布', xData: ['待排产', '生产中', '待检', '已完成', '暂停'] },
          { title: '产能负荷' },
          { title: '产线负荷对比', xData: ['一线', '二线', '三线', '四线', '五线'] },
          { title: 'OEE趋势' },
          { title: '异常停机分析', xData: ['换型', '缺料', '故障', '待检', '其他'] }
        ]
      },
      warehouse: {
        title: 'AI仓库助手',
        subtitle: '库存周转、仓储作业与物流调度',
        greeting: '你好，我是AI仓库助手，可以帮你分析库存、库位、收发货效率和异常预警。',
        prompts: ['库存周转是否健康？', '哪些物料低于安全库存？', '今日出入库效率如何？'],
        mockReply: '关于「{message}」：库存周转天数 18.6 天，整体健康。有 7 项物料低于安全库存，建议优先补货编码 M-2048、M-3112，今日出库效率较昨日提升 4.3%。',
        homeDetails: [{ title: '智能库存管理', desc: '实时监控库存水平，智能预警缺货与滞销，优化库存结构，降低资金占用。' }],
        kpiLabels: ['库存准确率', '周转天数', '待拣任务'],
        charts: [
          { title: '出入库趋势' },
          { title: '库存结构' },
          { title: '库位利用率' },
          { title: '呆滞库存分析', xData: ['0-30天', '31-60天', '61-90天', '91-180天', '180天+'] },
          { title: '拣货效率趋势' },
          { title: '收货及时率' }
        ]
      },
      quality: {
        title: 'AI质量助手',
        subtitle: '质量检测、缺陷分析与持续改进',
        greeting: '你好，我是AI质量助手，可以帮你分析质量异常、缺陷分布和改善建议。',
        prompts: ['本周质量异常有哪些？', '分析不良原因排行', '生成质量改善建议'],
        mockReply: '关于「{message}」：本周检出 3 批质量异常，主要集中在外观与尺寸偏差。外观类占比 42%，建议加强首件确认与工装校准，预计可改善一次合格率约 1.8%。',
        homeDetails: [{ title: '质量智能分析', desc: '实时分析生产质量数据，智能识别质量问题根源，提供改进建议，持续提升产品品质。' }],
        kpiLabels: ['一次合格率', '异常批次', '闭环率'],
        charts: [
          { title: '不良率趋势' },
          { title: '缺陷类型排行', xData: ['外观', '尺寸', '功能', '包装', '其他'] },
          { title: '质量健康度' },
          { title: '返修率趋势' },
          { title: '工序良率对比', xData: ['冲压', '焊接', '装配', '测试', '包装'] },
          { title: '检验及时率' }
        ]
      },
      equipment: {
        title: 'AI设备助手',
        subtitle: '设备状态监控、预测维护与故障诊断',
        greeting: '你好，我是AI设备助手，可以帮你分析设备状态、故障风险和维护计划。',
        prompts: ['哪些设备存在停机风险？', '生成本周保养计划', '分析设备异常原因'],
        mockReply: '关于「{message}」：CNC-03、注塑-07 存在较高停机风险，预测告警 2 条。建议本周内完成润滑保养与传感器复检，可将非计划停机风险降低约 35%。',
        homeDetails: [{ title: '设备预测性维护', desc: '实时监控设备状态，智能预测故障风险，提前安排维护计划，减少停机时间，降低维护成本。' }],
        kpiLabels: ['设备健康度', '预测告警', '平均停机'],
        charts: [
          { title: '设备健康趋势' },
          { title: '告警等级分布', xData: ['提示', '一般', '重要', '紧急', '严重'] },
          { title: '维护完成率' },
          { title: '停机时长分析', xData: ['CNC', '注塑', '冲压', '装配', '检测'] },
          { title: 'MTBF趋势' },
          { title: '点检完成率' }
        ]
      },
      procurement: {
        title: 'AI采购助手',
        subtitle: '供应商评估、采购预测与成本优化',
        greeting: '你好，我是AI采购助手，可以帮你分析采购成本、供应风险和供应商表现。',
        prompts: ['本月采购成本趋势？', '哪些供应商存在风险？', '生成补货采购建议'],
        mockReply: '关于「{message}」：本月采购成本环比下降 2.1%，供应商 B 准交率下滑需关注。建议对关键件启动备选供应商询价，并优先下达 M-2048 补货采购单。',
        homeDetails: [{ title: '智能采购决策', desc: '分析供应商数据，优化采购策略，智能预测价格走势，降低采购成本，确保供应链稳定。' }],
        kpiLabels: ['采购节省率', '准交率', '风险供应商'],
        charts: [
          { title: '采购金额趋势' },
          { title: '供应商评分', xData: ['供应商A', '供应商B', '供应商C', '供应商D', '供应商E'] },
          { title: '供应链稳定性' },
          { title: '交付周期对比', xData: ['A类', 'B类', 'C类', 'D类', 'E类'] },
          { title: '议价空间趋势' },
          { title: '物料齐套率' }
        ]
      }
    }
  },
  en: {
    header: {
      title: 'Ningbo Ruichuang AI Industrial Brain',
      weekdays: ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    },
    common: {
      backHome: 'Back to Home',
      send: 'Send',
      chatPlaceholder: 'Enter your business question...',
      aiAgent: 'AI Agent',
      clickEnter: 'Enter →',
      aiAnalysis: 'AI Insight',
      insight: 'Smart Insight',
      statusAnalyzing: 'Real-time AI Analysis',
      insightTitle: '{title} has completed the latest scan',
      insightText: 'Based on live metrics, trends and rules, key recommendations for {subtitle} are ready.',
      months: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
      chatThinking: 'Analyzing, please wait...',
      chatHide: 'Hide Assistant',
      chatShow: 'Show AI Assistant',
      fullscreen: 'Fullscreen',
      exitFullscreen: 'Exit Fullscreen'
    },
    home: {
      heroTitle: 'Industrial AI Digital Workers for Smart Manufacturing',
      heroSubtitle: 'Powered by Qwen LLM — five AI assistants across production, warehouse, quality, equipment and procurement.',
      partners: [
        { icon: '🌐', label: 'Alibaba Cloud' },
        { icon: '📱', label: 'Qwen LLM' },
        { icon: '⚡', label: 'Ruichuang AI' }
      ]
    },
    assistants: {
      production: {
        title: 'Product Assistant',
        subtitle: 'Scheduling, capacity evaluation & line coordination',
        greeting: 'Hi, I can help with capacity, scheduling, work orders and bottlenecks.',
        prompts: ['Line attainment today?', 'Find production bottlenecks', 'Tomorrow scheduling advice'],
        mockReply: 'Regarding "{message}": plan attainment is 96.2% and Assembly Line 2 is the main bottleneck. Complete kitting before the afternoon shift and prioritize changeover wait time.',
        homeDetails: [{ title: 'Smart Production Scheduling', desc: 'Evaluate capacity in real time, optimize plans and resources, and automate scheduling decisions.' }],
        kpiLabels: ['Plan Attainment', 'Equipment Utilization', 'WIP Orders'],
        charts: [
          { title: 'Line Attainment Trend' },
          { title: 'Work Order Status', xData: ['Pending', 'In Progress', 'QC', 'Done', 'Hold'] },
          { title: 'Capacity Load' },
          { title: 'Line Load Comparison', xData: ['Line 1', 'Line 2', 'Line 3', 'Line 4', 'Line 5'] },
          { title: 'OEE Trend' },
          { title: 'Downtime Analysis', xData: ['Changeover', 'Material', 'Fault', 'QC', 'Other'] }
        ]
      },
      warehouse: {
        title: 'Stock Assistant',
        subtitle: 'Inventory turnover, warehousing & logistics',
        greeting: 'Hi, I can help with inventory, locations, inbound/outbound efficiency and alerts.',
        prompts: ['Is inventory turnover healthy?', 'Items below safety stock?', 'Inbound/outbound efficiency today?'],
        mockReply: 'Regarding "{message}": turnover is 18.6 days and overall healthy. 7 items are below safety stock — prioritize M-2048 and M-3112. Outbound efficiency is up 4.3% vs yesterday.',
        homeDetails: [{ title: 'Smart Inventory Management', desc: 'Monitor stock levels, alert shortages and slow movers, and optimize inventory structure.' }],
        kpiLabels: ['Inventory Accuracy', 'Turnover Days', 'Pick Tasks'],
        charts: [
          { title: 'Inbound/Outbound Trend' },
          { title: 'Inventory Structure' },
          { title: 'Bin Utilization' },
          { title: 'Slow-moving Stock', xData: ['0-30d', '31-60d', '61-90d', '91-180d', '180d+'] },
          { title: 'Picking Efficiency' },
          { title: 'Receiving On-time Rate' }
        ]
      },
      quality: {
        title: 'Quality Assistant',
        subtitle: 'Inspection, defect analysis & continuous improvement',
        greeting: 'Hi, I can help with quality issues, defect distribution and improvement plans.',
        prompts: ['Quality issues this week?', 'Top defect causes', 'Improvement recommendations'],
        mockReply: 'Regarding "{message}": 3 abnormal lots this week, mainly cosmetic and dimension issues. Cosmetic defects account for 42% — strengthen first-piece checks and tooling calibration to lift FPY by ~1.8%.',
        homeDetails: [{ title: 'Quality Intelligence', desc: 'Analyze quality data, identify root causes and suggest improvements.' }],
        kpiLabels: ['First Pass Yield', 'Abnormal Lots', 'Closure Rate'],
        charts: [
          { title: 'Defect Rate Trend' },
          { title: 'Defect Type Ranking', xData: ['Cosmetic', 'Dimension', 'Function', 'Packaging', 'Other'] },
          { title: 'Quality Health' },
          { title: 'Rework Rate Trend' },
          { title: 'Process Yield', xData: ['Stamp', 'Weld', 'Asm', 'Test', 'Pack'] },
          { title: 'Inspection On-time' }
        ]
      },
      equipment: {
        title: 'Device Assistant',
        subtitle: 'Equipment monitoring, predictive maintenance & diagnostics',
        greeting: 'Hi, I can help with equipment status, failure risk and maintenance plans.',
        prompts: ['Equipment at downtime risk?', 'Weekly maintenance plan', 'Analyze equipment anomalies'],
        mockReply: 'Regarding "{message}": CNC-03 and Injection-07 show elevated downtime risk with 2 predicted alerts. Complete lubrication and sensor checks this week to cut unplanned downtime risk by ~35%.',
        homeDetails: [{ title: 'Predictive Maintenance', desc: 'Monitor equipment health, predict failures and plan maintenance to reduce downtime.' }],
        kpiLabels: ['Equipment Health', 'Predicted Alerts', 'Avg. Downtime'],
        charts: [
          { title: 'Equipment Health Trend' },
          { title: 'Alert Level Distribution', xData: ['Info', 'Minor', 'Major', 'Critical', 'Severe'] },
          { title: 'Maintenance Completion' },
          { title: 'Downtime by Equipment', xData: ['CNC', 'Injection', 'Press', 'Asm', 'QC'] },
          { title: 'MTBF Trend' },
          { title: 'Inspection Completion' }
        ]
      },
      procurement: {
        title: 'Purchase Assistant',
        subtitle: 'Supplier evaluation, forecasting & cost optimization',
        greeting: 'Hi, I can help with procurement cost, supply risk and supplier performance.',
        prompts: ['Procurement cost trend this month?', 'Suppliers at risk?', 'Replenishment suggestions'],
        mockReply: 'Regarding "{message}": procurement cost is down 2.1% MoM; Supplier B on-time delivery needs attention. Start backup sourcing for critical parts and prioritize a PO for M-2048 replenishment.',
        homeDetails: [{ title: 'Smart Procurement', desc: 'Analyze suppliers, optimize strategy and forecast prices to reduce cost.' }],
        kpiLabels: ['Savings Rate', 'On-time Delivery', 'Risk Suppliers'],
        charts: [
          { title: 'Procurement Spend Trend' },
          { title: 'Supplier Scores', xData: ['Supplier A', 'Supplier B', 'Supplier C', 'Supplier D', 'Supplier E'] },
          { title: 'Supply Chain Stability' },
          { title: 'Lead Time Comparison', xData: ['Cat A', 'Cat B', 'Cat C', 'Cat D', 'Cat E'] },
          { title: 'Negotiation Margin' },
          { title: 'Material Kit Rate' }
        ]
      }
    }
  }
}

export const assistantKeys = ['production', 'warehouse', 'quality', 'equipment', 'procurement']

export const assistantRoutes = {
  production: '/assistant/production',
  warehouse: '/assistant/warehouse',
  quality: '/assistant/quality',
  equipment: '/assistant/equipment',
  procurement: '/assistant/procurement'
}

export const assistantAvatars = {
  production: '/avatars/assistant-production.png',
  warehouse: '/avatars/assistant-warehouse.png',
  quality: '/avatars/assistant-quality.png',
  equipment: '/avatars/assistant-equipment.png',
  procurement: '/avatars/assistant-procurement.png'
}

export const assistantAccents = {
  production: '#38bdf8',
  warehouse: '#22c55e',
  quality: '#a78bfa',
  equipment: '#06b6d4',
  procurement: '#60a5fa'
}

export const assistantLayouts = {
  production: 'production-layout',
  warehouse: 'warehouse-layout',
  quality: 'quality-layout',
  equipment: 'equipment-layout',
  procurement: 'procurement-layout'
}

export const assistantKpiValues = {
  production: [
    { value: '96.8%', trend: '+4.2%' },
    { value: '88.5%', trend: '+2.1%' },
    { value: '126', trend: '-8' }
  ],
  warehouse: [
    { value: '99.2%', trend: '+0.6%' },
    { value: '18.4', trend: '-2.3' },
    { value: '48', trend: '+12' }
  ],
  quality: [
    { value: '98.7%', trend: '+1.1%' },
    { value: '7', trend: '-3' },
    { value: '94.5%', trend: '+5.8%' }
  ],
  equipment: [
    { value: '91.6%', trend: '+3.4%' },
    { value: '12', trend: '-5' },
    { value: '1.8h', trend: '-0.7h' }
  ],
  procurement: [
    { value: '6.4%', trend: '+1.7%' },
    { value: '93.8%', trend: '+2.4%' },
    { value: '5', trend: '-2' }
  ]
}
