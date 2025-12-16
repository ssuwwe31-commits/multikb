#!/usr/bin/env python3
"""
CUDA兼容性检查脚本
用于诊断 PyTorch CUDA 与 GPU 的兼容性问题
"""

import sys
import subprocess

def check_nvidia_smi():
    """检查 nvidia-smi 是否可用"""
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("=" * 60)
            print("✅ NVIDIA GPU 信息:")
            print("=" * 60)
            print(result.stdout)
            return True
        else:
            print("❌ nvidia-smi 执行失败")
            return False
    except FileNotFoundError:
        print("❌ nvidia-smi 未找到，请确保已安装 NVIDIA 驱动")
        return False
    except Exception as e:
        print(f"❌ 检查 GPU 时出错: {e}")
        return False

def check_pytorch():
    """检查 PyTorch 和 CUDA 版本"""
    try:
        import torch
        print("=" * 60)
        print("✅ PyTorch 信息:")
        print("=" * 60)
        print(f"PyTorch 版本: {torch.__version__}")
        print(f"CUDA 可用: {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            print(f"CUDA 版本: {torch.version.cuda}")
            print(f"cuDNN 版本: {torch.backends.cudnn.version()}")
            print(f"GPU 数量: {torch.cuda.device_count()}")
            
            for i in range(torch.cuda.device_count()):
                print(f"\nGPU {i}:")
                print(f"  名称: {torch.cuda.get_device_name(i)}")
                print(f"  计算能力: {torch.cuda.get_device_capability(i)}")
                print(f"  总内存: {torch.cuda.get_device_properties(i).total_memory / 1024**3:.2f} GB")
        else:
            print("⚠️ CUDA 不可用")
            
        return True
    except ImportError:
        print("❌ PyTorch 未安装")
        return False
    except Exception as e:
        print(f"❌ 检查 PyTorch 时出错: {e}")
        return False

def test_cuda_kernel():
    """测试 CUDA kernel 是否可用"""
    try:
        import torch
        if not torch.cuda.is_available():
            print("⚠️ CUDA 不可用，跳过 kernel 测试")
            return False
            
        print("=" * 60)
        print("🧪 测试 CUDA Kernel 兼容性:")
        print("=" * 60)
        
        try:
            # 测试简单的 CUDA 操作
            test_tensor = torch.tensor([1.0, 2.0, 3.0]).cuda()
            result = test_tensor + 1.0
            print(f"✅ CUDA kernel 测试通过")
            print(f"   测试结果: {result.cpu().numpy()}")
            del test_tensor, result
            torch.cuda.empty_cache()
            return True
        except Exception as e:
            error_msg = str(e).lower()
            print(f"❌ CUDA kernel 测试失败:")
            print(f"   错误: {e}")
            
            if "no kernel image" in error_msg:
                print("\n" + "=" * 60)
                print("🔧 问题诊断:")
                print("=" * 60)
                print("PyTorch 编译时支持的 CUDA 架构与当前 GPU 不匹配")
                print("\n解决方案:")
                print("1. 检查 GPU 计算能力:")
                if torch.cuda.is_available():
                    for i in range(torch.cuda.device_count()):
                        cap = torch.cuda.get_device_capability(i)
                        print(f"   GPU {i}: {cap[0]}.{cap[1]} (sm_{cap[0]}{cap[1]})")
                
                print("\n2. 安装匹配的 PyTorch 版本:")
                print("   访问 https://pytorch.org/get-started/locally/")
                print("   选择对应的 CUDA 版本和 GPU 架构")
                
                # 检查是否是 RTX 5090 (sm_100)
                try:
                    import torch
                    if torch.cuda.is_available():
                        cap = torch.cuda.get_device_capability(0)
                        if cap[0] >= 10:
                            print("\n   ⚠️  检测到 Blackwell 架构 (RTX 5090)，需要最新版本:")
                            print("   pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu124")
                            print("   或")
                            print("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124")
                        else:
                            print("\n   对于 CUDA 12.4 (推荐，支持最新 GPU):")
                            print("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124")
                            print("\n   对于 CUDA 12.1:")
                            print("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
                            print("\n   对于 CUDA 11.8:")
                            print("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
                except:
                    print("\n   对于 CUDA 12.4 (推荐):")
                    print("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124")
                    print("\n   对于 CUDA 12.1:")
                    print("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
                
            return False
            
    except ImportError:
        print("❌ PyTorch 未安装，无法测试")
        return False
    except Exception as e:
        print(f"❌ 测试 CUDA kernel 时出错: {e}")
        return False

def check_pytorch_arch():
    """检查 PyTorch 支持的架构"""
    try:
        import torch
        if not torch.cuda.is_available():
            return
            
        print("=" * 60)
        print("📋 PyTorch 编译信息:")
        print("=" * 60)
        
        # 尝试获取编译信息
        try:
            # PyTorch 2.0+ 支持
            if hasattr(torch.version, 'cuda'):
                print(f"CUDA 版本: {torch.version.cuda}")
        except:
            pass
            
        # 检查支持的架构（通过尝试不同架构的 kernel）
        print("\n支持的架构检测:")
        try:
            # 这个方法不直接可用，但我们可以通过错误信息推断
            print("(需要通过实际运行来检测)")
        except:
            pass
            
    except ImportError:
        pass

def main():
    print("=" * 60)
    print("CUDA 兼容性诊断工具")
    print("=" * 60)
    print()
    
    # 1. 检查 GPU
    has_gpu = check_nvidia_smi()
    print()
    
    # 2. 检查 PyTorch
    has_pytorch = check_pytorch()
    print()
    
    # 3. 测试 CUDA kernel
    if has_pytorch:
        kernel_ok = test_cuda_kernel()
        print()
        
        # 4. 检查架构信息
        check_pytorch_arch()
        print()
        
        if not kernel_ok:
            print("=" * 60)
            print("💡 建议:")
            print("=" * 60)
            print("1. 如果 GPU 计算能力较低（如 sm_60），可能需要安装支持更多架构的 PyTorch")
            print("2. 或者使用 CPU 版本（性能较慢但稳定）")
            print("3. 检查 CUDA 驱动版本是否与 PyTorch 要求的版本匹配")
            print()
            sys.exit(1)
    else:
        print("⚠️ 请先安装 PyTorch")
        sys.exit(1)
    
    print("=" * 60)
    print("✅ 所有检查通过，CUDA 可用")
    print("=" * 60)

if __name__ == "__main__":
    main()

