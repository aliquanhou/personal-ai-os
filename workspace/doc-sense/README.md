# DocSense — 智能文档助手

一个基于 AI 的智能文档处理工具，支持文档上传、总结、问答、翻译、改写，以及基于 RAG 的知识库问答。

## 技术栈

- **后端**: Python + FastAPI
- **前端**: React + TypeScript + Vite
- **数据库**: SQLite（开发）/ PostgreSQL（生产）
- **向量库**: Chroma
- **AI**: OpenAI / Claude / 开源模型

## 项目结构

```
doc-sense/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── core/           # 配置、安全
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务逻辑
│   │   ├── ai/            # AI 集成层
│   │   └── rag/           # RAG 知识库
│   ├── tests/
│   └── requirements.txt
├── frontend/               # React 前端
│   ├── src/
│   │   ├── components/    # 组件
│   │   ├── pages/         # 页面
│   │   ├── hooks/         # 自定义hooks
│   │   └── api/           # API调用
│   └── package.json
├── docker-compose.yml
└── README.md
```

## 快速启动

### 后端

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## 开发状态

- [x] D1: 项目脚手架
- [ ] D2: 后端基础（FastAPI 结构、配置、CORS）
- [ ] D3: 前端基础（React + TS + Vite）
- [ ] D4: 数据库设计
- [ ] D5: AI 接入
