# 🔧 技术方案：AI短视频自动生产平台

---

## 一、总体架构

```
┌─────────────────────────────────────────────────────┐
│                  前端 (React + TS)                    │
│   商家控制台 / 素材管理 / 视频预览 / 数据看板         │
└──────────────────────┬──────────────────────────────┘
                       │ REST API
┌──────────────────────▼──────────────────────────────┐
│                 后端 (FastAPI)                        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────┐  │
│  │ 用户系统 │ │ 素材管理 │ │ 任务调度 │ │ 发布管理  │  │
│  └─────────┘ └─────────┘ └─────────┘ └───────────┘  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────┐  │
│  │ 模板引擎 │ │ 文案生成 │ │ 视频合成 │ │ 数据报表  │  │
│  └─────────┘ └─────────┘ └─────────┘ └───────────┘  │
└──────┬──────────────┬──────────────┬───────────────┘
       │              │              │
┌──────▼─────┐ ┌──────▼─────┐ ┌──────▼─────┐
│  AI 服务层  │ │  存储层     │ │ 外部服务    │
│  DeepSeek  │ │ PostgreSQL │ │ 抖音开放API │
│  TTS引擎   │ │ 对象存储S3 │ │ TTS服务    │
│  图像生成   │ │ Redis缓存  │ │ FFmpeg     │
└────────────┘ └────────────┘ └────────────┘
```

---

## 二、核心技术选型

### 2.1 AI能力层

| 能力 | 技术选型 | 说明 |
|------|----------|------|
| 文案生成 | DeepSeek-V3 | 本地/API调用，生成短视频脚本 |
| 图像生成 | Stable Diffusion / 即梦 | 生成商品图、场景图 |
| 视频生成 | 模板混剪（FFmpeg） | 用模板+素材拼接，不用文生视频（成本高） |
| 语音合成 | 火山引擎TTS / 阿里云TTS | 中文语音合成，支持方言 |
| 字幕生成 | 自研/讯飞ASR | 自动生成字幕 |
| 智能配乐 | 版权音乐库 | 自动匹配BGM |

### 2.2 核心决策：**模板混剪 vs 文生视频**
> ⚠️ **关键决策**：90天内不做"文生视频"，采用"模板+素材混剪"

**原因**：
1. 文生视频成本高（每条0.5-3元），小商家预算承受不了
2. 文生视频质量不稳定，不适合商业场景
3. 模板混剪效果好（类似剪映模板），且成本极低
4. 抖音算法对"真实素材"更友好，纯AI生成内容有降权风险

**模板混剪方案**：
- 预设行业模板（餐饮/零售/服务）
- 商家上传3-5张产品图/视频素材
- AI生成文案+配音+字幕+模板合成
- 输出15-30秒成片

### 2.3 技术栈总结

| 层面 | 技术 | 理由 |
|------|------|------|
| 后端 | FastAPI + Python | 熟悉，异步高性能 |
| 前端 | React + TypeScript + Vite | 熟悉，开发效率高 |
| 数据库 | PostgreSQL + SQLAlchemy | 关系数据+灵活查询 |
| 缓存 | Redis | 任务队列、缓存 |
| 视频处理 | FFmpeg | 开源、功能强大 |
| 任务队列 | Celery + Redis | 异步视频生成任务 |
| AI模型 | DeepSeek API + 本地部署 | 成本可控 |
| 对象存储 | 阿里云OSS / MinIO | 素材和视频存储 |
| 部署 | Docker + 云服务器 | 简单可扩展 |

---

## 三、核心流程设计

### 3.1 视频生成流程
```
① 商家填写商品信息/上传素材
        ↓
② AI生成视频脚本（DeepSeek）
   - 标题、口播文案、画面描述
        ↓
③ 匹配行业模板
   - 餐饮/零售/服务模板
        ↓
④ 合成视频（FFmpeg）
   - 素材+文案+配音+字幕+BGM
        ↓
⑤ 生成预览
   - 商家确认或自动发布
        ↓
⑥ 发布到抖音
   - 抖音开放平台API
```

### 3.2 自动发布流程
```
定时任务（每天定时）
    ↓
从素材库取最新素材
    ↓
批量生成视频
    ↓
调用抖音开放平台API
    ↓
自动发布+获取播放数据
    ↓
数据回流分析
```

---

## 四、数据模型设计

### 4.1 核心表结构
```sql
-- 用户表
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255),
    business_name VARCHAR(100),
    business_type VARCHAR(50),  -- restaurant/retail/service
    plan_type VARCHAR(20),      -- free/standard/pro
    created_at TIMESTAMP
);

-- 素材表
CREATE TABLE assets (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    type VARCHAR(20),           -- image/video
    url VARCHAR(500),
    tags TEXT[],
    created_at TIMESTAMP
);

-- 视频任务表
CREATE TABLE video_tasks (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    template_id INT,
    status VARCHAR(20),         -- pending/processing/done/failed
    script TEXT,
    video_url VARCHAR(500),
    created_at TIMESTAMP
);

-- 发布记录表
CREATE TABLE publish_records (
    id SERIAL PRIMARY KEY,
    task_id INT REFERENCES video_tasks(id),
    platform VARCHAR(20),       -- douyin
    status VARCHAR(20),         -- published/failed
    video_id VARCHAR(100),
    play_count INT DEFAULT 0,
    like_count INT DEFAULT 0,
    comment_count INT DEFAULT 0,
    share_count INT DEFAULT 0,
    published_at TIMESTAMP
);

-- 模板表
CREATE TABLE templates (
    id SERIAL PRIMARY KEY,
    industry VARCHAR(50),
    name VARCHAR(100),
    config JSONB,               -- 模板配置
    usage_count INT DEFAULT 0
);
```

---

## 五、成本估算

### 5.1 AI成本（单条视频）
| 项目 | 成本 |
|------|------|
| 文案生成 (DeepSeek) | ~0.01元 |
| 配音 (TTS) | ~0.1元 |
| 视频合成 (FFmpeg) | ~0.01元 |
| 存储 | ~0.05元 |
| **合计** | **~0.2元/条** |

### 5.2 服务器成本
| 项目 | 月成本 |
|------|--------|
| 云服务器 (8C16G) | ~500元 |
| 对象存储 | ~100元 |
| 数据库 | ~200元 |
| **合计** | **~800元/月** |

### 5.3 毛利率
- 标准版99元/月，每天1条 = 30条/月
- 每条成本 0.2元 × 30 = 6元
- **毛利率 > 90%**（不含获客成本）

---

## 六、技术风险与应对

| 风险 | 应对 |
|------|------|
| 抖音API限制 | 多账号轮换、合规使用 |
| 视频生成速度慢 | 异步队列+批量处理+预生成 |
| AI文案质量不稳定 | 行业prompt库+人工审核选项 |
| 素材版权问题 | 提供正版素材库+用户上传 |
| DeepSeek限流 | 本地部署+API降级方案 |
