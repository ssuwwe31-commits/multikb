---
layout: home

hero:
  name: "Knowledge Base"
  text: "企业级知识库管理平台"
  tagline: 唯一集成ClamAV安全扫描、支持9种文档格式、完整多模态能力
  image:
    src: /logo.png
    alt: Knowledge Base
  actions:
    - theme: brand
      text: 快速开始
      link: /docs/getting-started
    - theme: alt
      text: 查看文档
      link: /docs/
    - theme: alt
      text: GitHub
      link: https://github.com/your-repo

features:
  - icon: 🔒
    title: 企业级安全
    details: ClamAV病毒扫描 + 恶意脚本检测，双重安全机制，满足企业合规要求
  - icon: 📄
    title: 9种文档格式
    details: PDF、DOCX、PPTX、Excel、HTML、MD、TXT、JSON、XML，全覆盖企业常见格式
  - icon: 🎨
    title: 多模态能力
    details: 文本+图片+图文混合，六种检索策略，Qwen VL高精度OCR
  - icon: 📊
    title: 版本管理
    details: 文档级+块级双层版本管理，支持版本恢复和对比
  - icon: 🔍
    title: 智能检索
    details: 向量+关键词混合检索，Rerank精排，多模态融合检索
  - icon: 🚀
    title: 生产可用
    details: 核心功能100%对齐设计文档，已通过生产环境验证

---

## 核心优势

### 企业级安全 ⭐⭐⭐⭐⭐

**ClamAV病毒扫描**：唯一集成病毒扫描的开源知识库
- 支持TCP/Socket连接
- 恶意脚本检测
- 安全扫描状态追踪
- 历史数据补扫描

### 多格式支持 ⭐⭐⭐⭐⭐

**9种文档格式全覆盖**：
- PDF、DOCX、PPTX、Excel、HTML、MD、TXT、JSON、XML
- 结构化解析，保留文档结构
- 智能分块，基于文档结构

### 多模态能力 ⭐⭐⭐⭐⭐

**完整多模态支持**：
- 文本问答、图片问答、图文混合问答
- 图片搜索（CLIP向量化）
- 高精度OCR（Qwen VL）
- 多模态融合检索

## 版本选择

### 开源基础版（免费）

**完整核心功能**：
- ✅ 9种文档格式支持
- ✅ 多模态问答
- ✅ 6种检索策略
- ✅ ClamAV安全扫描
- ✅ 版本管理
- ✅ 联网搜索

**适用场景**：
- 个人用户
- 小团队
- 开发者
- 学习和研究

[了解更多 →](/features/open-source)

### 企业版（商业许可）

**高级功能**：
- 🎯 知识图谱（自动实体提取、关系识别）
- 🎯 智能Agent（多步骤任务、自然语言命令）
- 🎯 K8s监控诊断（自动诊断、根因分析）
- 🎯 知识库共享（协作功能）
- 🎯 高级权限管理（RBAC）
- 🎯 专业支持（7×24技术支持）

**适用场景**：
- 中大型企业
- 需要高级功能
- 需要专业支持
- 需要定制开发

[了解更多 →](/features/enterprise)

## 技术架构

- **后端**：FastAPI + Celery + SQLAlchemy
- **前端**：Vue 3 + TypeScript + Vite
- **存储**：MySQL + OpenSearch + Redis + MinIO
- **AI能力**：Ollama + Qwen VL + CLIP

## 快速开始

```bash
# 克隆项目
git clone https://github.com/your-repo/knowledge-base.git

# 启动服务
cd knowledge-base
docker-compose up -d
```

[查看完整文档 →](/docs/)

## 统计数据

- **91个API接口**：完整功能覆盖
- **9种文档格式**：企业级支持
- **6种检索策略**：满足不同场景
- **18个设计文档**：透明可维护

## 社区

- [GitHub](https://github.com/your-repo)
- [Gitee](https://gitee.com/your-repo)
- [文档](/docs/)
- [博客](/blog/)

---

<div style="text-align: center; margin-top: 60px;">
  <p>开始使用 Knowledge Base，构建您的企业知识库</p>
  <a href="/docs/getting-started" style="display: inline-block; margin-top: 20px; padding: 12px 24px; background: #646cff; color: white; text-decoration: none; border-radius: 4px;">立即开始</a>
</div>

