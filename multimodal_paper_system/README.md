# 多模态论文图谱系统

这是一个本地可持续扩展的论文学习系统。它不只管理 paper 列表，还把阅读进度、理解检查、方向掌握度和论文关系图谱放在一起。

## 现在包含什么

- 图谱主页：论文节点、关系、筛选、阅读状态、方向掌握度仪表盘
- 统一笔记页：支持响应式布局和可拖拽宽度
- 初始化笔记：新 paper 可以先走问题卡片，再做理解检查
- 理解检查：支持本地规则打分，也支持接本地后端点评
- 后端接口：为未来接入本地认证 CLI / 模型点评留好入口

## 目录结构

```text
multimodal_paper_system/
  assets/      前端脚本和样式
  backend/     理解检查后端
  data/        论文、关系、阅读进度 JSON
  notes/       笔记页和运行时笔记入口
  scripts/     本地启动脚本
  index.html   图谱主页
```

## 前端启动

```bash
cd /Users/applemima1111/Documents/自主学习/multimodal_paper_system
python3 -m http.server 8123
```

打开：

```text
http://localhost:8123
```

## 理解检查后端启动

```bash
cd /Users/applemima1111/Documents/自主学习/multimodal_paper_system
./scripts/start_study_backend.sh
```

后端默认监听：

```text
http://localhost:8130
```

健康检查：

```text
http://localhost:8130/api/health
```

## 后端点评模式

前端提交理解检查时，会优先请求本地后端：

- 如果后端已启动：使用后端点评结果
- 如果后端没启动：自动退回页面内本地规则打分

当前后端有两种工作方式：

1. 默认方式：本地规则点评  
   不依赖外部服务，离线可用。

2. CLI 代理方式：调用你本机已认证的命令行工具  
   设置环境变量 `CODEX_STUDY_CHECK_CMD` 即可。这个命令需要：
   - 从标准输入读取 JSON
   - 输出一段 JSON 结果

结果结构建议包含：

```json
{
  "score": 82,
  "pass": true,
  "details": [],
  "overallFeedback": {
    "overallReasons": ["..."],
    "nextActions": ["..."]
  }
}
```

后端文件：

- `backend/server.py`：HTTP 接口
- `backend/evaluator.py`：规则点评和 CLI 代理入口

## 数据文件

- `data/papers.json`：论文节点、PDF、笔记、关键词、阅读状态
- `data/relations.json`：论文之间的技术关系
- `data/reading_progress.json`：当前阅读进度、完成和挂起状态
- `data/relation_types.json`：关系类型说明

## 笔记系统

- `assets/paper-note.css`：统一的响应式论文笔记样式
- `assets/paper-note-resize.js`：笔记宽度拖拽
- `assets/paper-study-check.js`：理解检查逻辑
- `notes/_paper_note_template.html`：适合写完整笔记
- `notes/paper_note_runtime.html`：适合新 paper 初始化阅读

## 新增论文

1. 准备 PDF，并在 `data/papers.json` 填入路径
2. 在 `data/relations.json` 增加它和现有论文的关系
3. 如果已经有完整笔记，就在 `notes/` 新建 HTML
4. 如果暂时只想先读，可以直接使用运行时初始化笔记
5. 刷新 `http://localhost:8123`

## 仓库边界建议

这些内容建议不要直接纳入仓库：

- 本地 PDF 软链 `papers-src`
- 机器相关的绝对路径
- 个人临时导出文件
- 本地缓存和浏览器存储

仓库里保留：

- 前端页面和脚本
- 后端服务
- 数据结构
- 模板和文档

## 维护原则

- 图谱不只记录引用关系，也记录技术关系
- “完成阅读”以理解检查通过为准，不只是点了勾
- “暂时挂起”是正式状态，不和完成混在一起
- 每周阅读提醒根据 `data/reading_progress.json` 继续推进
