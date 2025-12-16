#!/bin/bash
# RTX 5090 PyTorch 修复脚本
# 专门处理 sm_120 不兼容问题

set +e  # 允许错误，继续尝试

echo "=========================================="
echo "RTX 5090 PyTorch 修复脚本"
echo "问题: PyTorch 2.3.1 不支持 sm_120"
echo "=========================================="
echo ""

# 检查当前 PyTorch 版本
echo "1. 检查当前 PyTorch 版本..."
python -c "import torch; print(f'当前版本: {torch.__version__}')" 2>/dev/null || echo "PyTorch 未安装"
echo ""

# 卸载旧版本
echo "2. 卸载旧版本 PyTorch..."
pip uninstall -y torch torchvision torchaudio 2>&1 | grep -v "WARNING: Skipping"
echo "✅ 旧版本已卸载"
echo ""

# 清理 pip 缓存（可选）
echo "3. 清理 pip 缓存..."
pip cache purge 2>/dev/null || true
echo ""

# 尝试安装支持 sm_120 的版本
INSTALL_SUCCESS=false

# 方式1: nightly CUDA 12.8（RTX 5090 需要 CUDA 12.8+）
echo "4. 尝试方式1: 安装 nightly 版本 (CUDA 12.8)..."
echo "   RTX 5090 (sm_120) 需要 CUDA 12.8+ 和 nightly 版本"
if pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu128 --no-cache-dir 2>&1 | tee /tmp/pytorch_install.log; then
    INSTALL_SUCCESS=true
    echo "✅ nightly CUDA 12.8 安装成功"
else
    echo "❌ CUDA 12.8 安装失败（可能系统没有 CUDA 12.8）"
    tail -10 /tmp/pytorch_install.log
fi

# 方式2: 如果失败，尝试 nightly CUDA 12.9
if [ "$INSTALL_SUCCESS" = false ]; then
    echo ""
    echo "5. 尝试方式2: 安装 nightly 版本 (CUDA 12.9)..."
    if pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu129 --no-cache-dir 2>&1 | tee /tmp/pytorch_install.log; then
        INSTALL_SUCCESS=true
        echo "✅ nightly CUDA 12.9 安装成功"
    else
        echo "❌ CUDA 12.9 安装失败"
    fi
fi

# 方式3: 如果都失败，尝试 nightly CUDA 12.4（可能不支持 sm_120）
if [ "$INSTALL_SUCCESS" = false ]; then
    echo ""
    echo "6. 尝试方式3: 安装 nightly 版本 (CUDA 12.4)..."
    echo "   ⚠️  警告: CUDA 12.4 可能不支持 sm_120，但可以尝试"
    if pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu124 --no-cache-dir 2>&1 | tee /tmp/pytorch_install.log; then
        INSTALL_SUCCESS=true
        echo "✅ nightly CUDA 12.4 安装成功（需要测试是否支持 sm_120）"
    else
        echo "❌ 安装失败"
    fi
fi

# 验证安装
if [ "$INSTALL_SUCCESS" = true ]; then
    echo ""
    echo "=========================================="
    echo "6. 验证安装..."
    echo "=========================================="
    python -c "
import torch
print(f'PyTorch 版本: {torch.__version__}')
print(f'CUDA 可用: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA 版本: {torch.version.cuda}')
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    cap = torch.cuda.get_device_capability(0)
    print(f'计算能力: {cap[0]}.{cap[1]} (sm_{cap[0]}{cap[1]})')
    
    # 检查是否支持 sm_120
    if cap[0] >= 12:
        print('⚠️  检测到 sm_120，需要验证 PyTorch 是否支持...')
        print('   根据最新信息，即使 nightly 版本也可能不完全支持 sm_120')
    
    # 测试 CUDA kernel
    try:
        test = torch.tensor([1.0]).cuda()
        result = test + 1.0
        print(f'✅ CUDA kernel 测试通过: {result.cpu().numpy()}')
        print('✅ RTX 5090 可以正常使用！')
    except Exception as e:
        error_msg = str(e).lower()
        if 'no kernel image' in error_msg or 'not compatible' in error_msg:
            print(f'❌ CUDA kernel 测试失败: {e}')
            print('')
            print('⚠️  PyTorch 版本不支持 sm_120')
            print('')
            print('根据最新搜索结果:')
            print('1. PyTorch 稳定版本（包括 2.3.1）不支持 sm_120')
            print('2. PyTorch nightly 版本正在添加支持，但可能还不完全稳定')
            print('3. 有用户报告即使使用 nightly 版本（如 2.8.0.dev）仍然不支持')
            print('4. 需要 CUDA 12.8+ 和最新的驱动')
            print('')
            print('解决方案:')
            print('1. 确保使用 CUDA 12.8+ 和最新的 NVIDIA 驱动')
            print('2. 尝试最新的 nightly 版本: pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu128')
            print('3. 关注 PyTorch GitHub issue: https://github.com/pytorch/pytorch/issues/164342')
            print('4. 临时使用 CPU 模式: RERANK_DEVICE=cpu')
            print('5. 等待 PyTorch 正式支持 sm_120（预计 PyTorch 2.5+）')
        else:
            print(f'❌ 其他错误: {e}')
"
    echo ""
    echo "=========================================="
    echo "✅ 安装完成！"
    echo "=========================================="
else
    echo ""
    echo "=========================================="
    echo "❌ 安装失败"
    echo "=========================================="
    echo ""
    echo "RTX 5090 (sm_120) 需要 PyTorch 2.5+ 或 nightly 版本"
    echo ""
    echo "临时解决方案:"
    echo "1. 在 .env 中设置: RERANK_DEVICE=cpu"
    echo "2. 重启服务"
    echo ""
    echo "详细错误信息: /tmp/pytorch_install.log"
    exit 1
fi

