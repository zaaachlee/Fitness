# AI Fitness Dashboard（AI 私人健身管理平台）

AI 驱动的个人健身管理平台。追踪饮食、训练、健康指标，获取个性化 AI 建议。

## 技术栈

| 层级 | 技术选型 |
|------|---------|
| 前端 | Next.js 15 + React 19 + TypeScript + Tailwind CSS |
| UI 组件 | shadcn/ui + Radix Primitives + Lucide Icons |
| 图表 | Recharts + ECharts |
| 后端 | Python FastAPI + SQLAlchemy 2.0（异步） |
| 数据库 | PostgreSQL 16 |
| 缓存 | Redis 7 |
| AI | Claude API（Anthropic） |
| 认证 | JWT（python-jose） |

## 快速开始

### 环境要求

- Docker & Docker Compose
- Node.js 20+（前端本地开发）
- Python 3.12+（后端本地开发）

### 开发环境启动

```bash
# 进入项目目录
cd ai-fitness-dashboard

# 复制环境配置文件
cp .env.example .env
# 编辑 .env，填入你的 Anthropic API Key

# 启动全部服务
docker compose up -d

# 或者分别启动：
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

- 前端：http://localhost:3000
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

### 数据库迁移

```bash
cd backend
alembic upgrade head
```

### 填充种子数据

```bash
cd backend
python -m app.seed.run
```

## 项目结构

```
ai-fitness-dashboard/
├── frontend/              # Next.js 前端应用
│   └── src/
│       ├── app/           # App Router 页面
│       ├── components/    # React 组件
│       ├── hooks/         # 自定义 Hooks
│       ├── lib/           # 工具函数 & API 客户端
│       ├── stores/        # Zustand 状态管理
│       └── types/         # TypeScript 类型定义
├── backend/               # FastAPI 后端应用
│   └── app/
│       ├── api/v1/        # API 路由
│       ├── core/          # 配置、安全、数据库
│       ├── models/        # SQLAlchemy 数据模型
│       ├── schemas/       # Pydantic 校验模型
│       ├── services/      # 业务逻辑
│       └── seed/          # 种子数据
├── docs/                  # 项目文档
│   └── DESIGN_SYSTEM.md   # 设计系统参考文档
├── docker-compose.yml
└── README.md
```

## 功能模块

- **首页 Dashboard** — 每日总览：KPI 环形面板、热量平衡、宏量营养素、AI 今日建议、趋势图表
- **饮食记录** — 手动搜索食物、AI 文字识别、AI 图片识别，按三餐+加餐分别统计
- **训练记录** — 动作数据库、训练模板、组数记录、PR 追踪、1RM 估算、Volume 统计
- **健康监测** — 体检指标录入、趋势折线图、正常范围对比、风险提示
- **AI 助手** — 上下文感知对话，结合饮食/训练/健康历史数据提供个性化建议

## 设计风格

深色模式优先，参考 Apple Health、Garmin Connect 和 Notion 的设计语言。

详见 [docs/DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md) 完整设计系统参考。

## 开发进度

1. ✅ **Phase 1** — 项目基础设施 + 认证系统
2. 🔜 **Phase 2** — 饮食记录模块
3. ⏳ **Phase 3** — 训练记录模块
4. ⏳ **Phase 4** — 首页 Dashboard + 数据可视化
5. ⏳ **Phase 5** — 健康监测模块
6. ⏳ **Phase 6** — AI 助手 + 知识库
7. ⏳ **Phase 7** — 打磨完善

## 许可证

MIT
