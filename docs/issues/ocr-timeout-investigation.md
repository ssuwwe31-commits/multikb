# OCR 超时问题排查报告

## 问题现象

```
2025-12-10 16:00:38 - INFO - OCR 尝试 1/3: 模型=qwen2.5vl:latest, 图片大小=260711 bytes
2025-12-10 16:05:38 - WARNING - OCR 请求错误 (尝试 1/3): Read timed out. (read timeout=300)
2025-12-10 16:05:39 - DEBUG - OCR 尝试 2/3: 模型=qwen2.5vl:latest, 图片大小=260711 bytes
```

**关键信息：**
- 图片文件大小：260711 bytes（约 255KB）
- 超时时间：300秒（5分钟）
- 模型：qwen2.5vl:latest
- 错误类型：Read timeout（读取超时）

---

## 代码排查结果

### 1. ❌ **图片预处理未实现**

**问题位置：** `app/services/image_service.py:73-84`

**发现：**
- 配置中有 `OCR_PREPROCESS_ENABLED=True` 和 `OCR_PREPROCESS_MAX_SIZE=2048`
- 但 `_perform_qwen_ocr` 方法中**完全没有使用这些配置**
- 直接发送原始图片字节给 Ollama，没有进行尺寸调整

**代码：**
```python
def _perform_qwen_ocr(self, image_bytes: bytes, image_mime: str) -> str:
    # 先验证图片
    is_valid, error_msg = self._validate_image_bytes(image_bytes, image_mime)
    if not is_valid:
        logger.warning(f"图片验证失败，跳过 OCR: {error_msg}")
        return ""
    
    service = self._get_ollama_service()
    return service.extract_text_from_image(
        image_bytes=image_bytes,  # ❌ 直接使用原始图片，未预处理
        image_mime=image_mime,
    )
```

**影响：**
- 如果图片实际分辨率很高（例如 4000x3000），即使压缩后只有 255KB，Ollama 处理时仍需要处理高分辨率图片
- 高分辨率图片会显著增加模型推理时间

---

### 2. ⚠️ **Base64 编码增加传输大小**

**问题位置：** `app/services/ollama_service.py:120`

**发现：**
- 图片先进行 base64 编码再发送
- Base64 编码会增加约 33% 的数据量
- 260KB 的图片编码后约 347KB

**代码：**
```python
encoded = base64.b64encode(image_bytes).decode("utf-8")
payload = {
    "model": target_model,
    "prompt": prompt_text,
    "images": [encoded],  # Base64 编码后的字符串
    "stream": False,
}
```

**影响：**
- 增加网络传输时间
- 增加 Ollama 服务器解析时间

---

### 3. ⚠️ **重试间隔过短**

**问题位置：** `app/services/ollama_service.py:152, 157, 162`

**发现：**
- 重试间隔只有 1 秒
- 如果服务器负载高，1 秒可能不足以恢复

**代码：**
```python
if attempt < max_retries:
    time.sleep(1)  # ❌ 只有1秒延迟
```

**影响：**
- 服务器可能还没恢复就立即重试
- 可能导致连续失败

---

### 4. ⚠️ **超时时间可能不足**

**问题位置：** `app/config/settings.py:97`

**发现：**
- 超时时间设置为 300 秒（5 分钟）
- 对于高分辨率图片或复杂图片，可能不够

**配置：**
```python
OLLAMA_OCR_TIMEOUT: int = 300  # 5分钟
```

**影响：**
- 某些大图片可能需要更长时间处理
- 5 分钟可能不足以完成 OCR

---

### 5. ✅ **重试机制正常**

**问题位置：** `app/services/ollama_service.py:128-167`

**发现：**
- 重试机制实现正确
- 最多重试 2 次（共 3 次尝试）
- 错误处理完善

**代码：**
```python
max_retries = max(0, settings.OLLAMA_OCR_MAX_RETRIES)  # 默认2次
for attempt in range(max_retries + 1):  # 总共3次尝试
    try:
        # ... OCR 请求 ...
    except requests.exceptions.RequestException as e:
        last_error = f"请求错误: {str(e)}"
        logger.warning(f"OCR 请求错误 (尝试 {attempt + 1}/{max_retries + 1}): {last_error}")
        if attempt < max_retries:
            time.sleep(1)
```

---

### 6. ✅ **图片验证正常**

**问题位置：** `app/services/image_service.py:50-71`

**发现：**
- 图片验证逻辑正常
- 会检查图片大小、尺寸等

---

## 根本原因分析

### 主要原因：**图片预处理未实现**

1. **配置存在但未使用**
   - `OCR_PREPROCESS_ENABLED=True` 配置存在
   - `OCR_PREPROCESS_MAX_SIZE=2048` 配置存在
   - 但代码中完全没有使用这些配置

2. **直接发送原始图片**
   - 如果图片实际分辨率很高（例如 4000x3000），即使文件大小只有 255KB
   - Ollama 需要处理高分辨率图片，推理时间会显著增加
   - 可能导致超时

3. **Base64 编码增加开销**
   - 编码后的数据量增加约 33%
   - 增加网络传输和解析时间

### 次要原因

1. **重试间隔过短**：1 秒可能不足以让服务器恢复
2. **超时时间可能不足**：300 秒对于某些复杂图片可能不够

---

## 问题影响

### 1. 性能影响
- OCR 处理时间过长（>5分钟）
- 可能导致任务超时失败
- 影响文档处理整体速度

### 2. 资源消耗
- 占用 Ollama 服务器资源时间过长
- 可能影响其他并发任务
- 增加服务器负载

### 3. 用户体验
- 文档处理时间延长
- 可能出现 OCR 失败的情况
- 影响系统可用性

---

## 建议的解决方案

### 🔴 **高优先级：实现图片预处理**

**修改位置：** `app/services/image_service.py:_perform_qwen_ocr`

**建议：**
1. 在 OCR 前检查 `OCR_PREPROCESS_ENABLED` 配置
2. 如果启用，将图片缩放到 `OCR_PREPROCESS_MAX_SIZE`（2048px）
3. 保持宽高比，避免图片变形
4. 优化图片质量，平衡文件大小和清晰度

**预期效果：**
- 减少图片分辨率，显著降低 OCR 处理时间
- 提高 OCR 成功率
- 减少超时情况

### 🟡 **中优先级：优化重试策略**

**修改位置：** `app/services/ollama_service.py`

**建议：**
1. 增加重试间隔（例如：指数退避：1秒、5秒、15秒）
2. 或者根据错误类型调整重试间隔
3. 超时错误使用更长的重试间隔

**预期效果：**
- 给服务器更多恢复时间
- 提高重试成功率

### 🟡 **中优先级：增加超时时间**

**修改位置：** `app/config/settings.py`

**建议：**
1. 将 `OLLAMA_OCR_TIMEOUT` 增加到 600 秒（10分钟）
2. 或者根据图片大小动态调整超时时间

**预期效果：**
- 给大图片更多处理时间
- 减少超时失败

### 🟢 **低优先级：优化 Base64 编码**

**建议：**
1. 考虑使用流式传输（如果 Ollama 支持）
2. 或者先压缩图片再编码

**预期效果：**
- 减少传输数据量
- 提高传输速度

---

## 需要进一步确认的信息

1. **图片实际分辨率**
   - 日志中的图片实际像素尺寸是多少？
   - 是否超过 2048px？

2. **Ollama 服务器状态**
   - 服务器 CPU/GPU 使用率如何？
   - 是否有其他并发任务？
   - 模型加载是否正常？

3. **超时频率**
   - 是所有图片都超时，还是只有特定图片？
   - 超时图片的共同特征是什么？

4. **模型性能**
   - qwen2.5vl 模型处理类似图片的正常时间是多少？
   - 是否有性能基准数据？

---

## 代码检查清单

- [x] 检查 OCR 预处理配置是否使用
- [x] 检查图片预处理逻辑
- [x] 检查超时配置
- [x] 检查重试机制
- [x] 检查错误处理
- [x] 检查 Base64 编码
- [ ] 检查图片实际分辨率（需要运行时数据）
- [ ] 检查 Ollama 服务器状态（需要运维数据）

---

## 总结

**核心问题：** 图片预处理配置存在但未实现，导致高分辨率图片直接发送给 Ollama，处理时间过长导致超时。

**建议优先级：**
1. 🔴 **立即修复**：实现图片预处理功能
2. 🟡 **尽快优化**：增加重试间隔和超时时间
3. 🟢 **后续优化**：优化传输方式

