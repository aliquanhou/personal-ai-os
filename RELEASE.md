# Release Process

> Personal AI OS 发布管理规范

---

## 版本号规则

```
MAJOR.MINOR-SPRINT
  │      │      └── Sprint tag: sprint2, sprint3, docs-freeze, repo-engineering
  │      └───────── 功能迭代 (0=初始, 5=治理层)
  └──────────────── 架构跃迁 (0=初始, 1=Multi User)
```

## 发布检查清单

每次打 Git Tag 前，执行以下检查：

### 代码质量
- [ ] `pytest tests/ -v` 全部通过
- [ ] Scenario tests 全部通过
- [ ] `python main.py serve` 启动无错误
- [ ] `curl localhost:8001/health` 返回 200
- [ ] `python main.py agents` 列出所有 Agent

### 文档
- [ ] `CHANGELOG.md` 已更新
- [ ] `VERSION.md` 版本号正确
- [ ] `docs/architecture/` 已更新（如有架构变更）
- [ ] `CLAUDE.md` 已更新（如有模块变动）

### Git
- [ ] `git status` 无意外未提交文件
- [ ] `.gitignore` 覆盖所有生成文件
- [ ] Commit message 格式：`feat:` / `fix:` / `docs:` / `chore:`

### 发布命令

```bash
# 1. 确认状态
git status
git log --oneline -5

# 2. 运行测试
python -m pytest tests/ -v

# 3. 打标签
git tag v0.X-sprintY -m "Personal AI OS v0.X — <描述>"

# 4. 验证
git tag -l
git log --oneline --graph --all

# 5. 推送（远程仓库配置后）
git push origin sprint-5 --tags
```

---

## 已发布版本

| Tag | 日期 | 描述 | Commit |
|-----|------|------|--------|
| `v0.5-docs-freeze` | 2026-08-02 | Architecture docs + CLAUDE.md | `47d65cb` |
| `v0.5-sprint5` | 2026-08-02 | Governance Layer | `2bef484` |
| `v0.4-sprint4` | 2026-08-02 | Communication Layer | `f4d2980` |
| `v0.3-sprint3` | 2026-08-02 | Organization Layer | `bcde0d2` |
| `v0.2-sprint2` | 2026-08-02 | Reliability Layer | `343d2b3` |

---

## 回滚指南

如需回滚到某个版本：

```bash
# 查看某个 Tag 的代码
git checkout v0.2-sprint2

# 从 Tag 创建修复分支
git checkout -b hotfix-xxx v0.5-sprint5

# 查看两个版本间的差异
git diff v0.4-sprint4..v0.5-sprint5 --stat
```

## 分支策略

```
main (未来，远程推送后)
  │
  ├── sprint-5 (当前活跃)
  │     └── Sprint 5.x 开发
  │
  ├── (未来: sprint-6)
  │     └── Sprint 6 开发
  │
  └── (未来: release/v0.5)
        └── 稳定版本维护
```
