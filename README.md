# AI Agent 智慧农场系统

一套能跑通 **「感知 → 诊断 → 人工确认 → 规划 → 控制 → 预警」** 完整闭环的多 Agent 智慧农场系统。
**断网、没 Key、缺依赖也能全流程演示**——每一项 AI 能力都有对应的本地降级实现，节点函数完全一致。

> 技术栈：FastAPI + Tortoise ORM + MySQL 8 · LangChain + LangGraph · 多模态（视觉/时序/气象/RAG）· Vue3 + Element Plus + SSE

---

## 一、系统架构

```
smart-farm-system/
├── backend/                     # FastAPI 后端
│   ├── app/
│   │   ├── main.py              # 入口：自动扫描 api/ 挂载路由 + 统一异常 + 生命周期
│   │   ├── config.py            # 全局配置（环境变量可覆盖）
│   │   ├── db.py                # Tortoise ORM 初始化
│   │   ├── models.py            # 18 张业务表 + Agent 日志表
│   │   ├── seed.py              # 首次启动播种演示数据
│   │   ├── common/              # Result 统一返回体 / 统一异常 / CRUD 收敛 / 安全(JWT)
│   │   ├── agent/               # AI 内核
│   │   │   ├── state.py         # FarmState（带 reducer 的状态通道）
│   │   │   ├── llm.py           # LLM 封装：ChatOpenAI ↔ 本地规则内核
│   │   │   ├── tools.py         # LangChain 风格工具层（感知/检索/视觉/控制/预警/配置）
│   │   │   ├── nodes.py         # 7 个 Agent 节点函数（两种模式共用）
│   │   │   ├── engine.py        # LangGraph StateGraph + 离线等价状态机 + 路由表
│   │   │   └── service.py       # 跑流水线 + 落库 + Human-in-the-loop resume
│   │   ├── rag/                 # 本地向量库（哈希嵌入 + 余弦/关键词混合打分）
│   │   ├── services/            # 视觉像素内核 / 气象 / 设备安全护栏 / 视频抽帧
│   │   └── api/                 # 业务模块（每模块一文件，自动挂载）
│   └── requirements.txt
└── frontend/                    # Vue3 + Vite 前端（18 页面）
    └── src/
        ├── api/                 # axios（CRUD 30s / AI 推理 180s 分级超时）+ SSE
        ├── layout/              # Admin 布局（侧边菜单 + 实时引擎/LLM 模式提示）
        ├── components/          # 通用 CRUD 表格组件
        └── views/               # 18 个页面
```

## 二、七个 Agent，一条流水线

| Agent | 做什么 | 关键能力 |
|---|---|---|
| 感知 Agent | 多模态数据清洗、异常过滤、气象融合 | 输出标准化「农场现状」 |
| 病虫害诊断 Agent | 叶片/航拍识别 + 知识库检索 + 处方校验 | 病害、严重度、药剂用量、安全间隔期、休药期 |
| 作物生长诊断 Agent | 长势评分、缺素判断、成熟期推算、产量预估 | 历史曲线对比 |
| 农事规划 Agent | 灌溉/施肥/打药/除草/采收排期 | 多目标优化（节水/降本/增产） |
| 设备调度 Agent | 下发 IoT 指令 | 安全校验 + 指令可追溯 + 拦截留痕 |
| 预警研判 Agent | 多源风险推理与分级 | 一般/重要/紧急三级，同类型去重合并 |
| 问答交互 Agent | 多轮记忆 + 图文提问 + 意图路由 | 回答附知识依据，可溯源 |

**按任务类型动态路由**（`GET /agent/engine` 实时查看路由表）：

```
diagnose → 感知 → 诊断 → [人工介入] → 规划 → 控制
growth   → 感知 → 长势 → 规划
plan     → 感知 → 规划 → 控制
control  → 感知 → 控制
alert    → 感知 → 预警
chat     → 感知 → 问答
full     → 感知 → 诊断 → [人工介入] → 长势 → 规划 → 控制 → 预警（综合会诊）
```

## 三、核心特性

- **可编排的决策流水线**：LangGraph 把能力拆成 7 个职责单一的节点，条件路由组合成不同任务链，带 reducer 的 `FarmState` 在节点间传递统一状态。新增业务场景 = 新增一条路由。
- **Human-in-the-loop**：检测到重度病害/高危预警时自动挂起后续自动化节点，前端弹待确认卡片，`POST /diagnosis/{id}/resume` 确认才继续，驳回则终止。
- **全链路离线兜底**：LLM/Embedding/向量检索/视觉理解/气象/编排六项能力均有本地降级实现，节点函数完全一致。顶部实时提示当前模式。
- **工具化 + 安全护栏 + 全链路审计**：Agent 不直接碰数据库和设备，一切动作走工具层；控制类工具内嵌安全校验，拦截即留痕；每次推理生成 `request_id`，节点级日志（输入/输出/耗时）可分页复盘。
- **RAG 可溯源**：诊断与问答强制关联知识库命中项，回答下方展示「知识依据」；未命中时明确提示「以实地判断为准」。
- **性能与体验治理**：批量研判并发化（`SCAN_CONCURRENCY`）+ 气象 10 分钟缓存；前端对 AI 推理接口单独放宽超时至 3 分钟，普通 CRUD 保持 30 秒；对话 SSE 流式输出。

## 四、快速开始

### 后端

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt

# 方式一：MySQL 8（默认，需先建库）
#   CREATE DATABASE smart_farm DEFAULT CHARSET utf8mb4;
#   复制 .env.example 为 .env 并填写 DB_URL / 账号密码

# 方式二：无 MySQL，用 SQLite 直接跑通演示
export DB_URL="sqlite://data/farm.db"      # Windows PowerShell: $env:DB_URL="sqlite://data/farm.db"

uvicorn app.main:app --reload --port 8000
```

启动后：
- API 文档（Swagger）：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/health
- 首次启动自动建表 + 播种演示数据（地块/作物/传感器/设备/知识库/大模型配置）。

> 默认账号 **admin / admin123**。不配任何 API Key 即可跑通全流程；在【系统管理 → 大模型配置】启用任意 OpenAI 兼容模型，即切换为真实大模型 + 向量检索。

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://127.0.0.1:5173 （已配置 `/api`、`/uploads` 代理到后端 8000 端口）。

### 启用 LangGraph 编排（可选）

安装 `langgraph` 后，将 `.env` 的 `ENGINE_MODE=langgraph` 即可切换为 `StateGraph` 条件路由；未安装时自动降级为等价状态机（节点函数复用，行为一致）。

## 五、18 个前端页面

登录 · 首页 · 总览大屏 · AI 问答助手 · Agent 编排 · 病虫害诊断 · 作物长势 · 农事规划 · 预警研判 · 农业知识库 · 影像管理 · 传感器数据 · 设备管理 · 地块管理 · 作物管理 · 气象预报 · AI 分析报表 · 大模型配置

## 六、主要 API

| 分类 | 端点 |
|---|---|
| 认证 | `POST /auth/login`、`GET /auth/me` |
| Agent 编排 | `GET /agent/engine`、`POST /agent/run`、`GET /agent/logs`、`GET /agent/trace/{rid}` |
| 诊断 | `POST /diagnosis/run`、`POST /diagnosis/{id}/resume` |
| 长势 | `POST /growth/run`、`GET /growth/history/{field_id}` |
| 农事 | `POST /task/run`、`POST /task/{id}/status` |
| 预警 | `POST /alert/run`、`POST /alert/scan`（并发巡检）、`POST /alert/{id}/resolve` |
| 问答 | `POST /chat/send`、`POST /chat/stream`（SSE） |
| 知识库 | `POST /knowledge/upload`、`GET /knowledge/search`、`POST /knowledge/reindex` |
| 影像 | `POST /media/upload`（图片像素分析 / 视频抽帧） |
| 大屏/报表 | `GET /dashboard/overview`、`GET /report/operations` |
| 大模型配置 | `POST /llm-config/{id}/activate`（热切换）、`GET /llm-config/{id}/test` |

## 七、说明

本项目为按公开技术方案描述独立实现的教学/原型工程，可改造到其他垂直行业（园区能耗、水务巡检、养殖环控）作为 Agent 应用脚手架。
