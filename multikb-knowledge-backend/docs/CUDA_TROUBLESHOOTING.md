# CUDA 兼容性问题排查指南

## 问题症状

错误信息：
```
CUDA error: no kernel image is available for execution on the device
```

## 问题原因

这个错误通常表示：
1. **PyTorch 编译时支持的 CUDA 架构与当前 GPU 不匹配**
   - PyTorch 预编译版本只支持特定的 GPU 架构（如 sm_75, sm_80, sm_86）
   - 如果您的 GPU 架构不在支持列表中，就会出现此错误

2. **CUDA 驱动版本不匹配**
   - PyTorch 需要特定版本的 CUDA 驱动
   - 驱动版本过低可能导致兼容性问题

## 诊断步骤

### 1. 运行诊断脚本

```bash
cd multikb-knowledge-backend
python scripts/check_cuda_compatibility.py
```

这个脚本会检查：
- GPU 信息（nvidia-smi）
- PyTorch 版本和 CUDA 版本
- GPU 计算能力
- CUDA kernel 兼容性

### 2. 手动检查 GPU 信息

```bash
# 检查 GPU
nvidia-smi

# 检查 GPU 计算能力
python -c "import torch; print(f'GPU: {torch.cuda.get_device_name(0)}'); print(f'计算能力: {torch.cuda.get_device_capability(0)}')"
```

### 3. 检查 PyTorch 版本

```bash
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA: {torch.version.cuda}')"
```

## 解决方案

### 方案 1: 安装匹配的 PyTorch 版本（推荐）

1. **确定您的 GPU 计算能力**
   - 运行诊断脚本或查看 nvidia-smi 输出
   - 例如：sm_60, sm_75, sm_80, sm_86 等

2. **选择匹配的 PyTorch 版本**
   - 访问 https://pytorch.org/get-started/locally/
   - 选择对应的 CUDA 版本

3. **安装 PyTorch**

   **CUDA 12.1（推荐，支持更多架构）:**
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```

   **CUDA 11.8（兼容性更好）:**
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

   **CUDA 12.4（推荐，支持 RTX 5090）:**
   ```bash
   # 方式1: 稳定版（推荐，避免依赖冲突）
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
   
   # 方式2: 如果稳定版不支持 RTX 5090，只安装 torch（rerank 不需要 torchvision）
   pip install torch --index-url https://download.pytorch.org/whl/cu124
   
   # 方式3: nightly 版本（如果必须，需要指定匹配版本）
   # ⚠️ 注意：nightly 版本可能有依赖冲突，建议先尝试稳定版
   pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu124
   ```
   
   **如果遇到依赖冲突错误**:
   ```bash
   # 错误: Cannot install torch and torchvision... because these package versions have conflicting dependencies
   # 解决方案1: 只安装 torch（推荐，rerank 服务不需要 torchvision）
   pip install torch --index-url https://download.pytorch.org/whl/cu124
   
   # 解决方案2: 使用稳定版而不是 nightly
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
   
   # 解决方案3: 使用自动安装脚本
   bash scripts/install_pytorch_rtx5090.sh
   ```

4. **验证安装**
   ```bash
   python scripts/check_cuda_compatibility.py
   ```

### 方案 2: 从源码编译 PyTorch（高级）

如果预编译版本都不支持您的 GPU，可以：
1. 从源码编译 PyTorch，包含您 GPU 的架构
2. 参考：https://github.com/pytorch/pytorch#from-source

### 方案 3: 使用 CPU 模式（临时方案）

如果暂时无法修复 CUDA 兼容性：
1. 在 `.env` 文件中设置：
   ```bash
   RERANK_DEVICE=cpu
   ```
2. 重启服务
3. **注意**：CPU 模式性能较慢，但可以正常工作

## 常见 GPU 架构支持情况

| GPU 架构 | 计算能力 | PyTorch 支持 | 推荐版本 |
|---------|---------|------------|---------|
| Pascal (GTX 10xx) | sm_60, sm_61 | ✅ 需要较旧版本 | PyTorch 2.0+ |
| Volta (V100) | sm_70 | ✅ | PyTorch 2.0+ |
| Turing (RTX 20xx) | sm_75 | ✅ | PyTorch 2.0+ |
| Ampere (RTX 30xx, A100) | sm_80, sm_86 | ✅ | PyTorch 2.0+ |
| Ada Lovelace (RTX 40xx) | sm_89 | ✅ 需要较新版本 | PyTorch 2.1+ |
| Hopper (H100) | sm_90 | ✅ 需要最新版本 | PyTorch 2.3+ |
| **Blackwell (RTX 5090)** | **sm_120** | ✅ **必须使用最新版本** | **PyTorch 2.5+ 或 nightly（2.3.1 不支持）** |

### RTX 5090 特别说明

RTX 5090 采用 Blackwell 架构（计算能力 sm_120），是 NVIDIA 最新的消费级 GPU。

**⚠️ 重要提示：**
- PyTorch **稳定版本**（包括 2.3.1）**不支持** sm_120
- PyTorch **nightly 版本**正在添加对 sm_120 的支持，但**可能还不完全稳定**
- 有用户报告即使使用 nightly 版本（如 2.8.0.dev）仍然遇到不支持 sm_120 的问题
- 需要 **CUDA 12.8+** 和最新的 NVIDIA 驱动

要使用 RTX 5090，需要：

1. **最新的 NVIDIA 驱动**（建议 560+，支持 CUDA 12.8+）
   ```bash
   nvidia-smi  # 检查驱动版本
   ```

2. **PyTorch nightly 版本 + CUDA 12.8+**
   - **必须使用**: PyTorch nightly 版本
   - **CUDA 版本**: 12.8 或 12.9（12.4 可能不够）
   - **注意**: 即使 nightly 版本也可能不完全支持，需要测试验证

3. **安装命令**:
   ```bash
   # ⚠️ 重要：RTX 5090 (sm_120) 需要 CUDA 12.8+ 和 nightly 版本
   # 根据最新搜索，即使 nightly 版本也可能不完全支持 sm_120
   
   # 方式1: 安装 nightly 版本 + CUDA 12.8（推荐尝试）
   pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu128
   
   # 方式2: 如果 CUDA 12.8 不可用，尝试 CUDA 12.9
   pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu129
   
   # 方式3: 如果只有 CUDA 12.4，尝试 nightly（可能不支持 sm_120）
   pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu124
   
   # ⚠️ 注意：
   # - 只安装 torch（rerank 不需要 torchvision）
   # - 即使 nightly 版本也可能不完全支持 sm_120
   # - 如果都不行，建议使用 CPU 模式或等待正式支持
   ```

4. **验证 RTX 5090 支持**:
   ```bash
   python -c "
   import torch
   print(f'PyTorch: {torch.__version__}')
   print(f'CUDA 可用: {torch.cuda.is_available()}')
   if torch.cuda.is_available():
       print(f'GPU: {torch.cuda.get_device_name(0)}')
       cap = torch.cuda.get_device_capability(0)
       print(f'计算能力: {cap[0]}.{cap[1]} (sm_{cap[0]}{cap[1]})')
       if cap[0] >= 10:
           print('✅ 检测到 Blackwell 架构 (RTX 5090)')
       # 测试 CUDA kernel
       test = torch.tensor([1.0]).cuda()
       result = test + 1.0
       print(f'✅ CUDA kernel 测试通过')
   "
   ```

## 验证修复

修复后，运行以下命令验证：

```bash
python -c "
import torch
print(f'PyTorch: {torch.__version__}')
print(f'CUDA 可用: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA 版本: {torch.version.cuda}')
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'计算能力: {torch.cuda.get_device_capability(0)}')
    # 测试 CUDA kernel
    test = torch.tensor([1.0]).cuda()
    result = test + 1.0
    print(f'✅ CUDA kernel 测试通过: {result.cpu().numpy()}')
"
```

## 相关资源

- PyTorch 官方安装指南: https://pytorch.org/get-started/locally/
- CUDA 兼容性矩阵: https://pytorch.org/get-started/previous-versions/
- NVIDIA GPU 计算能力列表: https://developer.nvidia.com/cuda-gpus

## 注意事项

1. **Docker 环境**: 如果使用 Docker，确保：
   - 使用 `--gpus all` 或 `--device=/dev/dri` 参数
   - 基础镜像包含 CUDA 支持
   - 主机 CUDA 驱动版本匹配

2. **虚拟环境**: 确保在正确的 Python 虚拟环境中安装 PyTorch

3. **依赖冲突**: 如果遇到依赖冲突，考虑：
   - 使用新的虚拟环境
   - 或使用 conda 管理依赖

