#!/bin/bash
# RTX 5090 PyTorch 安装脚本
# 自动处理依赖冲突问题

# 不使用 set -e，因为我们需要尝试多种安装方式

echo "=========================================="
echo "RTX 5090 PyTorch 安装脚本"
echo "=========================================="
echo ""

# 检查 CUDA 版本
echo "1. 检查 CUDA 环境..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
    echo ""
else
    echo "⚠️  警告: 未找到 nvidia-smi"
fi

# 检查 Python 版本
echo "2. 检查 Python 版本..."
python --version
echo ""

# 尝试安装方式
INSTALL_SUCCESS=false

# 方式1: 先卸载旧版本（如果存在）
echo "3. 卸载旧版本 PyTorch（如果存在）..."
pip uninstall -y torch torchvision torchaudio 2>/dev/null || true
echo ""

# 方式2: 尝试 nightly 版本 CUDA 12.4（RTX 5090 需要支持 sm_120）
echo "4. 尝试方式1: 安装 nightly 版本 (CUDA 12.4，支持 sm_120)..."
if pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu124 2>&1 | tee /tmp/pytorch_install.log; then
    INSTALL_SUCCESS=true
    echo "✅ nightly 版本安装成功"
else
    echo "❌ nightly 版本安装失败，尝试其他方式..."
fi

# 方式3: 如果 nightly 失败，尝试稳定版 CUDA 12.4
if [ "$INSTALL_SUCCESS" = false ]; then
    echo ""
    echo "5. 尝试方式2: 安装稳定版 (CUDA 12.4)..."
    if pip install torch --index-url https://download.pytorch.org/whl/cu124 2>&1 | tee /tmp/pytorch_install.log; then
        INSTALL_SUCCESS=true
        echo "✅ 稳定版安装成功"
    else
        echo "❌ 稳定版安装失败，尝试其他方式..."
    fi
fi

# 方式4: 如果都失败，尝试 CUDA 12.1 nightly
if [ "$INSTALL_SUCCESS" = false ]; then
    echo ""
    echo "6. 尝试方式3: 安装 nightly 版本 (CUDA 12.1)..."
    if pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu121 2>&1 | tee /tmp/pytorch_install.log; then
        INSTALL_SUCCESS=true
        echo "✅ CUDA 12.1 nightly 版本安装成功"
    else
        echo "❌ CUDA 12.1 nightly 安装失败"
    fi
fi

# 验证安装
if [ "$INSTALL_SUCCESS" = true ]; then
    echo ""
    echo "=========================================="
    echo "7. 验证安装..."
    echo "=========================================="
    python -c "
import torch
print(f'PyTorch 版本: {torch.__version__}')
print(f'CUDA 可用: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA 版本: {torch.version.cuda}')
    print(f'GPU 数量: {torch.cuda.device_count()}')
    for i in range(torch.cuda.device_count()):
        print(f'GPU {i}: {torch.cuda.get_device_name(i)}')
        cap = torch.cuda.get_device_capability(i)
        print(f'  计算能力: {cap[0]}.{cap[1]} (sm_{cap[0]}{cap[1]})')
    # 测试 CUDA kernel
    try:
        test = torch.tensor([1.0]).cuda()
        result = test + 1.0
        print(f'✅ CUDA kernel 测试通过')
    except Exception as e:
        print(f'❌ CUDA kernel 测试失败: {e}')
"
    echo ""
    echo "=========================================="
    echo "✅ 安装完成！"
    echo "=========================================="
else
    echo ""
    echo "=========================================="
    echo "❌ 所有安装方式都失败了"
    echo "=========================================="
    echo ""
    echo "请检查:"
    echo "1. 网络连接是否正常"
    echo "2. pip 版本是否最新: pip install --upgrade pip"
    echo "3. CUDA 驱动版本是否足够新"
    echo "4. Python 版本是否兼容"
    echo ""
    echo "详细错误信息请查看: /tmp/pytorch_install.log"
    exit 1
fi

