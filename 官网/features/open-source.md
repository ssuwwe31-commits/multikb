# 开源基础版

> 现有已实现的功能全部开源，提供完整核心价值

---

## 核心功能

### ✅ 文档处理（9种格式）

- **PDF**：pdfplumber + PyMuPDF
- **DOCX**：python-docx，结构化解析
- **PPTX**：python-pptx，幻灯片级解析
- **Excel**：openpyxl，表格结构化
- **HTML**：BeautifulSoup，语义分块
- **Markdown**：结构化解析
- **TXT**：自动编码检测
- **JSON/XML**：结构化预览
- **CSV**：ExcelService统一处理

### ✅ 知识问答

- **文本问答**：RAG检索 + LLM生成
- **图片问答**：Qwen VL OCR识别
- **图文混合**：多模态融合问答
- **流式输出**：WebSocket实时流式
- **引用溯源**：完整的引用来源

### ✅ 搜索功能（6种策略）

- **向量搜索**：OpenSearch k-NN
- **关键词搜索**：OpenSearch全文检索
- **混合搜索**：向量+关键词融合
- **精确匹配**：短语匹配
- **模糊匹配**：容错搜索
- **多模态检索**：文本+图片融合

### ✅ 企业级安全

- **ClamAV病毒扫描**：TCP/Socket连接
- **恶意脚本检测**：规则匹配
- **安全扫描追踪**：完整状态记录
- **历史数据补扫描**：支持重新扫描

### ✅ 版本管理

- **文档级版本**：document_versions表
- **块级版本**：chunk_versions表
- **版本恢复**：支持恢复到任意版本
- **版本对比**：支持版本差异对比

### ✅ 联网搜索

- **SearxNG集成**：智能触发机制
- **结果摘要**：LLM自动生成摘要
- **缓存机制**：Redis缓存结果

### ✅ 图片管理

- **图片上传**：单张/批量上传
- **OCR识别**：Qwen VL高精度OCR
- **图片向量化**：CLIP/ResNet多模型
- **图片搜索**：向量+关键词融合

## 技术特点

- **91个API接口**：完整功能覆盖
- **18个设计文档**：透明可维护
- **分层架构**：清晰易扩展
- **生产可用**：已通过生产验证

## 适用场景

- ✅ 个人用户
- ✅ 小团队
- ✅ 开发者
- ✅ 学习和研究
- ✅ 快速原型

## 快速开始

```bash
# 克隆项目
git clone https://github.com/your-repo/knowledge-base.git

# 启动服务
cd knowledge-base
docker-compose up -d
```

[查看完整文档 →](/docs/)

## 获取开源版

- [GitHub](https://github.com/your-repo)
- [Gitee](https://gitee.com/your-repo)
- [下载](/download/)

