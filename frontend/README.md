# MES AI Client

宁波睿创 AI 工业大脑前端，基于 Vue 3 + Vite + Element Plus 构建，展示五大 AI 工业助手（生产、仓库、质量、设备、采购）的入口与数据看板。

## 快速开始

```bash
npm install
npm run dev
```

## 整体布局

所有页面共享同一套全局壳层，路由内容渲染在壳层主区域中。

```
App.vue
└── AppShell.vue                    # 全局布局容器
    ├── AppBackground.vue           # 全屏背景（渐变、网格、粒子、四角装饰）
    ├── AppHeader.vue               # 顶栏（日期时间、标题、操作图标）
    └── <RouterView />              # 当前页面内容（el-main 内）
        ├── Index.vue               # 首页 /
        └── AssistantDashboard.vue  # 助手看板 /assistant/:type
```

| 路由 | 页面组件 | 说明 |
|------|----------|------|
| `/` | `Index.vue` | 首页，五大 AI 助手入口 |
| `/assistant/:type` | `AssistantDashboard.vue` | 助手数据看板，`type` 见下方 |
| 其他路径 | — | 重定向至 `/` |

有效 `type` 参数：`production` · `warehouse` · `quality` · `equipment` · `procurement`（配置见 `src/data/assistantConfigs.js`）。

---

## 页面结构说明

### 1. 首页 `/` — `Index.vue`

首页由 **Hero 区**、**助手卡片区** 和 **浮动装饰** 三部分组成。

```
<section.content>
├── .hero-section                          # 顶部宣传区
│   ├── .hero-decoration.left-decoration   # 左侧装饰点（md+ 可见）
│   ├── .hero-content
│   │   ├── h2                               # 主标题
│   │   ├── .subtitle                        # 副标题说明
│   │   └── .partners                        # 合作方标签（阿里云 / 千问 / 时光星Ai）
│   └── .hero-decoration.right-decoration  # 右侧装饰点（md+ 可见）
│
├── .cards-container                       # 助手卡片区
│   └── .cards-wrapper (el-row)
│       └── .card-col × 5                    # 响应式栅格，每列一个助手
│           └── .card-shell
│               ├── .assistant-card          # 主卡片（点击跳转看板）
│               │   ├── .card-header
│               │   │   └── .role-title      # 助手名称 + 装饰翼
│               │   └── .card-body
│               │       └── .avatar-scene    # 助手头像
│               └── .detail-panel            # 悬停时展开的详情面板
│                   └── .detail-item × n     # 功能点标题 + 描述
│
└── .floating-ai                           # 右下角浮动 AI 头像装饰
```

**交互行为：**

- 鼠标悬停卡片 → 显示 `.detail-panel` 功能详情
- 点击卡片 → 跳转至对应 `/assistant/:type` 看板

**数据来源：** 页面内 `assistants` 数组（标题、头像、路由、详情文案）。

---

### 2. 助手看板 `/assistant/:type` — `AssistantDashboard.vue`

同一组件根据路由参数 `:type` 加载 `assistantConfigs.js` 中的配置，渲染对应助手的主题色、KPI、图表与对话区。五种助手结构相同，仅数据与 accent 色不同。

```
<div.assistant-page>                        # CSS 变量 --assistant-accent 随助手变化
├── .assistant-page-header (el-card)        # 页头
│   ├── .back-btn                           # 返回首页
│   ├── .assistant-page-meta
│   │   ├── h2                              # 助手名称（config.title）
│   │   └── p                               # 助手副标题（config.subtitle）
│   └── .status-pill                        # 状态标签「实时智能分析中」
│
└── .assistant-workspace-wrap
    └── .assistant-workspace (el-row)
        ├── .report-col (lg: 16/17)         # 左侧：数据报告区
        │   └── main.report-panel
        │       ├── .kpi-grid               # KPI 指标卡（3 个）
        │       │   └── .kpi-card × 3       # 标签 / 数值 / 趋势
        │       ├── .chart-grid             # 图表面板（2~3 个 ECharts）
        │       │   └── .chart-card × n
        │       │       ├── .chart-title    # 图表标题 + 「AI分析」
        │       │       └── .chart-box      # ECharts 挂载点
        │       └── .insight-card           # 智能洞察摘要
        │           ├── .insight-label
        │           ├── h3 / p              # 动态生成的洞察标题与正文
        │           └── .pulse-orb          # 装饰动画
        │
        └── .console-col (lg: 8/7)          # 右侧：AI 对话控制台
            └── .ai-console (el-card)
                ├── .console-avatar-stage   # 助手头像
                ├── .chat-window
                │   ├── .chat-message       # 助手问候语（config.greeting）
                │   └── .quick-prompt × n   # 快捷提问按钮（config.prompts）
                └── .chat-input             # 输入框 + 发送按钮
```

**各助手路由与配置键：**

| 路由 | config 键 | 助手名称 |
|------|-----------|----------|
| `/assistant/production` | `production` | AI 生产助手 |
| `/assistant/warehouse` | `warehouse` | AI 仓库助手 |
| `/assistant/quality` | `quality` | AI 质量助手 |
| `/assistant/equipment` | `equipment` | AI 设备助手 |
| `/assistant/procurement` | `procurement` | AI 采购助手 |

**配置字段（`assistantConfigs.js`）：**

| 字段 | 用途 |
|------|------|
| `title` / `subtitle` | 页头标题与说明 |
| `avatar` | 控制台头像 |
| `accent` | 主题色，用于图表与 CSS 变量 |
| `layout` | 图表区布局 class |
| `greeting` | 对话区问候语 |
| `prompts` | 快捷提问列表 |
| `kpis` | KPI 卡片（label / value / trend） |
| `charts` | 图表定义（title / type / data，type 支持 line · bar · gauge） |

---

## 公共组件

| 组件 | 文件 | 职责 |
|------|------|------|
| `AppShell` | `src/components/AppShell.vue` | 组合背景、顶栏与主内容 slot |
| `AppHeader` | `src/components/AppHeader.vue` | 实时日期时间、产品标题、顶栏图标 |
| `AppBackground` | `src/components/AppBackground.vue` | 全屏科技感背景与粒子动画 |

## 样式文件

| 文件 | 作用范围 |
|------|----------|
| `src/assets/styles/app.css` | 全局背景层 |
| `src/assets/styles/header.css` | 顶栏 |
| `src/assets/styles/index.css` | 首页 |
| `src/assets/styles/assistant-dashboard.css` | 助手看板 |

## 目录结构

```
src/
├── App.vue
├── main.js
├── router/index.js           # 路由定义
├── data/assistantConfigs.js  # 五类助手看板配置
├── views/
│   ├── Index.vue             # 首页
│   └── AssistantDashboard.vue
├── components/
│   ├── AppShell.vue
│   ├── AppHeader.vue
│   └── AppBackground.vue
└── assets/styles/            # 各页面样式
```
