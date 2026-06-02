# PRAI

PRAI 是一个围绕“论文导入、路线归位、阅读笔记、理解检查、知识图谱沉淀”设计的本地研究工作台。它不是单纯的 paper 列表，也不是一组分散的笔记页面，而是把阅读过程本身产品化了。

目前这套系统重点服务于多模态论文阅读，但底层结构已经按可扩展的产品方式组织，后续可以继续接更多方向、更多 provider、以及更完整的 agent 工作流。

## 产品定位

PRAI 解决的是这几个常见问题：

- 论文 PDF 散落在目录里，导入后没有统一归位
- 读完一篇 paper 之后，只留下零碎笔记，没有路线关系
- 图谱、笔记、理解检查、阅读进度分散在多个入口
- 新论文加入时，要靠手工补标题、分类、问题和关系

PRAI 把这些事情合成一个完整流程：

1. 导入论文 PDF
2. 自动分析标题、方向、关系和初始问题
3. 生成结构化笔记
4. 在图谱中跟已有路线连接
5. 通过理解检查区分“看过”和“理解过”

## 核心功能

### 1. PRAI 首页

- 未登录首页采用品牌化入口
- 右上角登录 / 注册
- 动态展示：
  - 当前论文节点
  - 研究方向
  - 已完成阅读
- 支持本地 Hero 背景资源替换

### 2. 论文图谱工作区

- 论文节点关系图
- 研究方向筛选
- 阅读完成状态可视化
- 方向掌握度与阅读进度面板
- 右侧论文详情与快捷操作

### 3. Guided Notes 笔记系统

- 每篇论文有正式笔记文件入口
- 新 paper 可以先走初始化笔记
- 支持结构化阅读、图示解释、理解检查
- 笔记页支持响应式布局与宽度调节

### 4. 论文导入流

- 支持本地 PDF 录入
- 系统自动分析标题、年份、方向和 graph 插入建议
- 自动初始化阅读问题与笔记模板
- 导入过程有状态反馈与进度提示

### 5. 理解检查

- 区分“已打开 / 已阅读 / 已理解”
- 支持本地规则评分
- 支持接本地后端模型点评
- 理解检查通过后再计入完成态

### 6. Provider Control

- paper 分析与理解检查可以分别指定 provider
- 当前支持：
  - 本地规则
  - MiniMax
  - 预留的 Codex / agent 架构
- provider 配置统一走本地配置文件

## 使用路径

如果你是第一次使用，推荐这样进入：

1. 打开首页：`http://localhost:8123`
2. 登录或注册本地账号
3. 进入图谱工作区
4. 打开 `Add Paper`
5. 导入 PDF 并生成草稿
6. 写入系统后开始阅读与补笔记
7. 阅读完成后做理解检查

## 首页体验

当前首页分成两层：

1. 未登录时的 `PRAI` 品牌入口  
   - 右上角登录 / 注册
   - 动态统计：
     - 当前论文节点
     - 研究方向
     - 已完成阅读
   - 本地 Hero 背景图轮播

2. 登录后的研究工作区  
   - 论文图谱
   - 理解检查
   - AI provider 控制
   - 新 paper 导入

首页背景图默认从：

- `assets/hero/prai-hero-graph.png`
- `assets/hero/prai-hero-desk.png`

读取。后续如果想换成视频背景，也建议沿用这一套本地资源入口。

## 目录结构

```text
multimodal_paper_system/
  assets/      前端脚本和样式
  backend/     理解检查后端
  data/        论文、关系、阅读进度 JSON
  imported_pdfs/ 系统导入后的本地 PDF 存放区
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
- `backend/minimax_provider.py`：MiniMax 驱动的 paper 分析增强

## Provider 统一配置

现在本地 provider 统一收敛到一个文件里：

- `backend/providers.local.json`

示例文件：

- `backend/providers.local.example.json`

这里统一管理：

- `paperAnalysis.provider`
- `paperAnalysis.model`
- `studyCheck.provider`
- `studyCheck.model`
- `providers.codex`
- `providers.minimax`

后续如果接 `codex-agent / 自定义 agent`，也继续走这一个配置入口。

## MiniMax 认证与 paper 分析

paper 导入分析支持 MiniMax 作为增强 provider。认证方式参考 OpenClaw 这一类工具的 provider 模式：**本地保存 API key / Token Plan Key，由后端代调，不把密钥暴露给前端。**

配置方式：

1. 复制：
   - `backend/providers.local.example.json`
   - 到 `backend/providers.local.json`
2. 在 `providers.minimax.apiKey` 中填入你的 MiniMax key
3. 需要的话调整：
   - `providers.minimax.baseUrl`
   - `providers.minimax.model`
4. 重启后端

兼容方式：

- 国际区：`https://api.minimax.io/v1`
- 中国区：`https://api.minimaxi.com/v1`
- 模型默认：`MiniMax-M2.7`

也可以直接用环境变量：

```bash
export MINIMAX_API_KEY="..."
export MINIMAX_BASE_URL="https://api.minimax.io/v1"
export MINIMAX_MODEL="MiniMax-M2.7"
```

当 MiniMax 可用时，`/api/paper/analyze` 会优先用它来细化：

- 论文方向归类
- graph 插入理由
- 关键词
- 核心问题
- 一句话贡献
- 建议重点阅读角度

页面上也已经有了 `Paper 分析引擎` 选择器，当前支持：

- `本地规则`
- `MiniMax`
- `MiniMax 2.5 / 2.7`
- `MiniMax 3 / 自定义模型 ID`

理解检查也支持同样的 provider/model 切换。当前推荐：

- paper 分析：`MiniMax`
- 理解检查：`MiniMax` 或 `本地规则`

`Codex Agent` 已经预留在 provider 选择架构里，后续接上即可。

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

现在推荐直接走页面里的 AI 导入流程：

1. 打开 `http://localhost:8123/add_paper.html`
2. 只填 `PDF 路径`
3. 点 `分析并生成草稿`
4. 系统会自动：
   - 推断标题、年份、方向和归档目录
   - 生成初始关键词
   - 细化关键阅读问题
   - 建议插入当前 graph 的关系
   - 生成一份初始化笔记
   - 判断是否和现有节点重复
5. 确认无误后点 `写入系统`

只有当系统判断不准时，才需要展开高级字段手动补充。

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
