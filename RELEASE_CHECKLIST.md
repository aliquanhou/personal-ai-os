# v1.0.0 Release Checklist

> Status: **READY TO PUSH** | 2026-08-02

---

## Pre-Release Verification

| # | Check | Result |
|---|-------|:--:|
| 1 | `python main.py start` 一次性成功 | ✅ |
| 2 | API `/health` 返回 200 | ✅ |
| 3 | 7 个 Agent 全部注册 | ✅ |
| 4 | 5 个官方插件发现 + 3 个默认启用 | ✅ |
| 5 | Plugin install/uninstall/reinstall 闭环 | ✅ |
| 6 | Studio `http://localhost:3000` 可访问 | ✅ |
| 7 | Timeline UI 组件渲染正常 | ✅ |
| 8 | PluginPanel 区分 Official/Community | ✅ |
| 9 | WorkspacePanel 项目列表正常 | ✅ |
| 10 | `python main.py agents` 列出 7 Agent | ✅ |
| 11 | `python main.py profile` 显示用户画像 | ✅ |
| 12 | `python main.py benchmark` 32/32 通过 | ✅ |

---

## Release Assets

| Asset | Status |
|-------|:--:|
| `README.md` — Quick Start + Feature Table | ✅ |
| `RELEASE_NOTES.md` — GitHub Release 正文 | ✅ |
| `DEMO.md` — 新用户首次体验流程 | ✅ |
| `FEEDBACK.md` — 用户反馈模板 | ✅ |
| `CLAUDE.md` — AI 模型入职文档 | ✅ |
| `docs/architecture/` — 8 个架构文档 | ✅ |
| `.env.example` — API Key 配置模板 | ✅ |
| `.gitignore` / `.gitattributes` — 跨平台兼容 | ✅ |

---

## Git

| # | Check | Status |
|---|-------|:--:|
| 1 | `release/v1.0.0` 分支创建 | ✅ |
| 2 | `v1.0.0` 标签指向 release HEAD | ✅ |
| 3 | 所有历史标签完整 (14 tags) | ✅ |
| 4 | `.gitignore` 覆盖 DB/backup/pycache | ✅ |
| 5 | `.gitattributes` 强制 LF | ✅ |

---

## Pre-Push (Local — awaiting remote URL)

```bash
# 1. Add remote
git remote add origin <github-repo-url>

# 2. Push release branch + all tags
git push -u origin release/v1.0.0 --tags

# 3. Create GitHub Release
#    - Tag: v1.0.0
#    - Title: Personal AI OS v1.0.0 — First Public Beta
#    - Body: copy from RELEASE_NOTES.md
#    - Attach: nothing (source-only release)
```

---

## Post-Push

| # | Action |
|---|--------|
| 1 | Create GitHub Release from v1.0.0 tag |
| 2 | Share repo link with 10-50 test users |
| 3 | Link to FEEDBACK.md in README |
| 4 | Tag feedback issues with `v1.0-feedback` |
| 5 | Review feedback weekly |
| 6 | Plan v1.1 based on user data (not assumptions) |

---

## Release Freeze Rules

**On `release/v1.0.0`:**
- ❌ No new kernel modules
- ❌ No Agent runtime changes
- ❌ No API route restructuring
- ✅ Hotfix critical bugs only
- ✅ Documentation improvements

**All new capabilities → `sprint-*` branches → Plugin Marketplace**

---

## Ready

```
Status:  AWAITING REMOTE
Branch:  release/v1.0.0
Tag:     v1.0.0
Files:   196
Commits: 20
```
