# AI Fitness Dashboard — Design System Reference

> 深色模式优先 · Apple Health / Garmin 风格 · 简洁高级

---

## 色彩系统

### 背景层级（深色模式）

| Token | Hex | 用途 |
|-------|-----|------|
| `--bg-primary` | `#0A0A0B` | 页面主背景（最深） |
| `--bg-secondary` | `#141416` | 卡片、侧边栏背景 |
| `--bg-tertiary` | `#1E1E21` | hover 状态、输入框背景 |
| `--bg-elevated` | `#28282C` | 弹窗、下拉菜单、Sheet |

### 文字层级

| Token | Hex | 用途 |
|-------|-----|------|
| `--text-primary` | `#F5F5F6` | 标题、正文强调 |
| `--text-secondary` | `#A1A1A6` | 辅助文字、标签 |
| `--text-tertiary` | `#63636B` | 占位符、次要信息 |

### 功能色

| Token | Hex | 语义 |
|-------|-----|------|
| `--accent` | `#4ADE80` | 主强调色 — 健康 / 成功 |
| `--accent-blue` | `#60A5FA` | 训练 / 信息 |
| `--accent-orange` | `#FB923C` | 热量 / 能量 / 警告 |
| `--accent-red` | `#F87171` | 蛋白 / 危险 / 超标 |
| `--accent-purple` | `#C084FC` | AI / 智能 |
| `--accent-cyan` | `#22D3EE` | 饮水 / 清新 |

### 语义色

| Token | Hex | 使用场景 |
|-------|-----|---------|
| `--success` | `#4ADE80` | 热量缺口、指标正常 |
| `--warning` | `#FB923C` | 热量盈余、指标偏高 |
| `--danger` | `#F87171` | 超标、异常指标 |
| `--info` | `#60A5FA` | 中性信息 |

### 图表调色板（7色序列）

```
#4ADE80  #60A5FA  #FB923C  #C084FC  #F87171  #22D3EE  #FBBF24
```

### 边框

| Token | 值 |
|-------|---|
| `--border` | `rgba(255, 255, 255, 0.08)` |
| `--border-subtle` | `rgba(255, 255, 255, 0.05)` |

---

## 排版

### 字体

| 用途 | Font Stack |
|------|-----------|
| 正文 | `'Inter', system-ui, sans-serif` |
| 数字/代码 | `'JetBrains Mono', monospace` |

### 字号阶梯

| Class | Size | 用途 |
|-------|------|------|
| `text-xs` | 12px | 辅助信息、提示文字 |
| `text-sm` | 14px | 正文、标签、按钮 |
| `text-base` | 16px | 正文强调 |
| `text-lg` | 18px | 小标题 |
| `text-xl` | 20px | 卡片标题 |
| `text-2xl` | 24px | 页面标题 |
| `text-3xl` | 30px | KPI 数值大字 |
| `text-4xl` | 36px | 关键 KPI 数字 |

---

## 间距系统

基于 4px 网格：

| Token | Px | 常用场景 |
|-------|-----|---------|
| `1` | 4px | 紧凑间距 |
| `2` | 8px | 图标与文字间距 |
| `3` | 12px | 卡片内元素间距 |
| `4` | 16px | 卡片 padding、表单间距 |
| `5` | 20px | 段间距 |
| `6` | 24px | 模块间距 |
| `8` | 32px | 大模块间距 |
| `12` | 48px | 页面区块间距 |

---

## 圆角

| Token | Size | 用途 |
|-------|------|------|
| `rounded-sm` | 6px | 小按钮、标签 |
| `rounded-md` | 8px | 输入框、选择器 |
| `rounded-lg` | 12px | 卡片 |
| `rounded-xl` | 16px | 弹窗、大卡片 |
| `rounded-full` | 9999px | 头像、药丸按钮 |

---

## 阴影

| Token | 值 | 用途 |
|-------|-----|------|
| `shadow-card` | `0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3)` | 卡片默认 |
| `shadow-card-hover` | `0 4px 12px rgba(0,0,0,0.5), 0 2px 4px rgba(0,0,0,0.3)` | 卡片 hover |
| `shadow-elevated` | `0 8px 24px rgba(0,0,0,0.5)` | 弹窗、下拉 |

---

## 组件模式

### 卡片

```tsx
// 默认卡片
<div className="card p-4">
  <h3 className="text-sm font-medium text-text-secondary">标题</h3>
  <p className="font-mono text-2xl font-bold text-text-primary">数值</p>
</div>

// 高亮卡片（带左侧色条）
<div className="card p-4 border-l-2 border-accent-purple bg-gradient-to-r from-accent-purple/5 to-transparent">
  ...
</div>

// 悬浮卡片
<div className="card-elevated p-6">...</div>
```

### 环形进度（KPI Ring）

```tsx
function KpiRing({ value, target, label, unit, color, icon: Icon }) {
  const pct = Math.min((value / target) * 100, 100);
  const circumference = 2 * Math.PI * 38;
  const offset = circumference - (pct / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative flex h-24 w-24 items-center justify-center">
        <svg className="absolute inset-0 -rotate-90" viewBox="0 0 96 96">
          <circle cx="48" cy="48" r="38" fill="none" stroke="currentColor"
            strokeWidth="6" className="text-bg-tertiary" />
          <circle cx="48" cy="48" r="38" fill="none" stroke="currentColor"
            strokeWidth="6" strokeLinecap="round"
            strokeDasharray={circumference} strokeDashoffset={offset}
            className={color} />
        </svg>
        <Icon className={cn("h-7 w-7", color)} />
      </div>
      <p className="text-xs font-medium text-text-secondary">{label}</p>
      <p className="font-mono text-base font-bold text-text-primary">
        {Math.round(value)}
        <span className="text-xs font-normal text-text-tertiary">{unit}</span>
      </p>
    </div>
  );
}
```

### 进度条

```tsx
<div className="progress-bar">
  <div className="progress-fill bg-accent-red" style={{ width: "75%" }} />
</div>
```

### 数值展示

```tsx
<span className="kpi-value">1,850</span>
<span className="kpi-label">今日热量摄入</span>
```

---

## 交互模式

### 动画规格

| 场景 | 时长 | 缓动 | 说明 |
|------|------|------|------|
| 页面元素入场 | 0.3s | ease-out | fadeIn + translateY(8px) |
| hover 过渡 | 0.2s | ease-out | 背景色、阴影变化 |
| 图表动画 | 0.5s | ease-out | 进度条、柱状图高度 |
| 页面切换 | 0.3s | ease-out | framer-motion AnimatePresence |
| 骨架屏闪烁 | 1.5s | infinite | pulse 动画 |

### Framer Motion 容器模式

```tsx
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

// Usage
<motion.div variants={containerVariants} initial="hidden" animate="visible">
  <motion.div variants={itemVariants}>...</motion.div>
</motion.div>
```

---

## 图标系统

使用 **Lucide Icons** (v0.468+)，线条风格，与深色主题搭配：

| 图标 | 使用场景 |
|------|---------|
| `LayoutDashboard` | 首页导航 |
| `Utensils` | 饮食模块 |
| `Dumbbell` | 训练模块、Logo |
| `Heart` | 健康模块 |
| `Sparkles` | AI 功能 |
| `Flame` | 热量 |
| `Beef` | 蛋白质 |
| `Wheat` | 碳水 |
| `Droplets` | 脂肪/饮水 |
| `Timer` | 运动时间 |
| `Footprints` | 步数 |
| `Target` | 目标 |
| `TrendingUp/Down` | 趋势 |
| `Moon/Sun` | 主题切换 |
| `Bell` | 通知 |
| `Search` | 搜索 |
| `Plus` | 添加 |
| `ChevronRight` | 查看更多 |

---

## 响应式断点

| 断点 | 宽度 | 布局变化 |
|------|------|---------|
| Base | < 768px | 单列，底部 Tab 导航（待实现），隐藏侧边栏 |
| `md` | ≥ 768px | 侧边栏可见，双列网格 |
| `lg` | ≥ 1024px | 三列网格，更大图表 |
| `xl` | ≥ 1280px | 四列 KPI 网格 |

---

## 命名约定

### 组件命名
- 页面组件：`*Page` (export default)
- UI 组件：PascalCase
- 图表组件：`*Chart.tsx`
- 布局组件：`Sidebar`, `Header`, `MobileNav`

### 文件组织
```
components/
  ui/          — 通用 UI 组件 (Button, Input, Card, etc.)
  charts/      — 图表组件 (LineChart, RingChart, etc.)
  dashboard/   — Dashboard 专属组件
  diet/        — 饮食模块组件
  workout/     — 训练模块组件
  health/      — 健康模块组件
  layout/      — 布局组件 (Sidebar, Header)
```

---

## 深色/亮色切换

- 使用 `next-themes` 实现
- 存储在 `localStorage`
- 默认深色模式 (`defaultTheme="dark"`)
- Tailwind 使用 `dark:` 前缀做亮色覆盖
- 系统级 CSS 变量定义在 `:root` 和 `.light` 选择器中
- 所有自定义颜色必须使用 CSS 变量，确保双模式兼容

---

## 图表规范

### 折线图 (LineChart)
- 用于：体重趋势、热量趋势、指标变化
- 线宽 2px，数据点 4px radius
- 渐变填充区域（opacity 0.1）
- Tooltip 显示日期 + 数值

### 柱状图 (BarChart)
- 用于：每日营养素对比、周训练次数
- 圆角柱顶（radius 4px）
- 间距 4px

### 环形图 (RingChart)
- 用于：KPI 进度展示
- 线宽 6px，圆角端点
- 背景环颜色 `bg-tertiary`

### 雷达图 (RadarChart)
- 用于：肌群训练分布、营养均衡
- 填充 opacity 0.2，边框 2px

### 热力图 (Heatmap)
- 用于：训练日历打卡
- GitHub 贡献图风格
- 5 级颜色渐变

### 通用规则
- 所有图表支持 hover tooltip
- 坐标轴颜色 `text-tertiary`
- 网格线 opacity 0.05
- 图例在底部或右侧
- Tooltip 背景 `bg-elevated` + 模糊

---

## 无障碍

- 所有交互元素需要 focus 样式
- 颜色对比度至少 AA 级（4.5:1）
- form 元素需要关联 label
- 使用 `sr-only` 提供屏幕阅读器文本
- 图表需要 data table 备选

---

## 开发工作流

### 每次更新后必须检查

```bash
# 前端状态
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/login
# 后端状态
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health
```

两端均需返回 200。如任一失败，先重启对应服务确认不是代码 Bug 再交付。

---

*最后更新: 2026-07-05 · Version 0.1.0*
