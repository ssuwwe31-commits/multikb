"""
Rerank Service
使用bge-reranker模型对搜索结果进行重新排序
"""

from typing import List, Dict, Any, Optional, Tuple
import os
import threading
from app.core.logging import logger
from app.core.exceptions import CustomException, ErrorCode
from app.config.settings import settings


class RerankService:
    """Rerank服务 - 使用bge-reranker模型对搜索结果重新排序（单例模式）"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(RerankService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化Rerank模型（仅执行一次）"""
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            
            self.model = None
            self.tokenizer = None
            self.enabled = settings.RERANK_ENABLED
            self.model_name = settings.RERANK_MODEL_NAME
            self.model_path = settings.RERANK_MODEL_PATH
            # 自动检测GPU可用性，如果配置为cuda但GPU不可用，降级到cpu
            self.device = self._get_device(settings.RERANK_DEVICE)
            self._initialize_model()
            self._initialized = True
    
    def _get_device(self, configured_device: str) -> str:
        """获取实际使用的设备，自动检测GPU可用性和兼容性
        
        Args:
            configured_device: 配置的设备（cpu/cuda）
            
        Returns:
            实际使用的设备（cpu/cuda）
        """
        # 如果配置为cpu，直接返回
        if configured_device.lower() == "cpu":
            return "cpu"
        
        # 如果配置为cuda，检查GPU是否可用且兼容
        if configured_device.lower() == "cuda":
            try:
                import torch
                if not torch.cuda.is_available():
                    logger.warning(f"配置为CUDA但GPU不可用，自动降级到CPU")
                    return "cpu"
                
                # 尝试创建一个简单的tensor来测试CUDA兼容性
                try:
                    test_tensor = torch.tensor([1.0]).cuda()
                    _ = test_tensor + 1.0  # 简单计算测试
                    del test_tensor
                    torch.cuda.empty_cache()
                    logger.info(f"✅ CUDA兼容性测试通过，使用CUDA设备")
                    return "cuda"
                except Exception as cuda_test_error:
                    error_msg = str(cuda_test_error).lower()
                    if "no kernel image" in error_msg:
                        logger.error(f"⚠️ CUDA兼容性测试失败: {cuda_test_error}")
                        logger.error("=" * 60)
                        logger.error("🔧 CUDA 架构不匹配问题诊断:")
                        logger.error("=" * 60)
                        try:
                            import torch
                            if torch.cuda.is_available():
                                for i in range(torch.cuda.device_count()):
                                    cap = torch.cuda.get_device_capability(i)
                                    gpu_name = torch.cuda.get_device_name(i)
                                    logger.error(f"GPU {i}: {gpu_name}")
                                    logger.error(f"  计算能力: {cap[0]}.{cap[1]} (sm_{cap[0]}{cap[1]})")
                                logger.error(f"PyTorch CUDA版本: {torch.version.cuda}")
                                logger.error("\n解决方案:")
                                logger.error("1. 运行诊断脚本: python scripts/check_cuda_compatibility.py")
                                logger.error("2. 安装匹配的PyTorch版本（支持您的GPU架构）")
                                
                                # 检查是否是 RTX 5090
                                cap = torch.cuda.get_device_capability(i)
                                if cap[0] >= 10:
                                    logger.error("3. ⚠️ 检测到 Blackwell 架构 (RTX 5090)，需要最新版本:")
                                    logger.error("   pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu124")
                                    logger.error("   或")
                                    logger.error("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124")
                                else:
                                    logger.error("3. 访问 https://pytorch.org/get-started/locally/ 选择正确的版本")
                                    logger.error("4. 例如 CUDA 12.4: pip install torch --index-url https://download.pytorch.org/whl/cu124")
                                    logger.error("   或 CUDA 12.1: pip install torch --index-url https://download.pytorch.org/whl/cu121")
                        except:
                            pass
                        logger.error("=" * 60)
                        logger.warning("🔄 自动降级到CPU模式（性能较慢但稳定）")
                        logger.warning("💡 如需使用GPU，请修复CUDA兼容性问题后重启服务")
                        return "cpu"
                    elif "cuda" in error_msg:
                        logger.error(f"⚠️ CUDA错误: {cuda_test_error}")
                        logger.warning("🔄 自动降级到CPU")
                        return "cpu"
                    else:
                        # 其他错误，也降级到CPU
                        logger.warning(f"CUDA测试出错: {cuda_test_error}，降级到CPU")
                        return "cpu"
                        
            except ImportError:
                logger.warning(f"PyTorch未安装，无法使用CUDA，使用CPU")
                return "cpu"
            except Exception as e:
                logger.warning(f"检测GPU可用性失败: {e}，使用CPU")
                return "cpu"
        
        # 其他情况默认使用cpu
        logger.warning(f"未知的设备配置: {configured_device}，使用CPU")
        return "cpu"
    
    def _initialize_model(self):
        """初始化rerank模型 - 优先使用本地缓存，没有才联网下载"""
        if not self.enabled:
            logger.info("Rerank模型未启用，跳过初始化")
            return
        
        try:
            logger.info(f"开始初始化Rerank模型: {self.model_name}")
            
            # ⚠️ 关键：在检查模型之前设置 HF_HOME，确保模型下载到配置的目录
            # 优先使用 settings 中配置的 HF_HOME，否则使用 CLIP_CACHE_DIR 的父目录（如果存在）
            # 这样 FlagEmbedding 和 huggingface_hub 都会使用配置的缓存目录
            hf_home = None
            if settings.HF_HOME:
                hf_home = settings.HF_HOME
                logger.info(f"📁 使用配置的 HF_HOME: {hf_home}")
            elif settings.CLIP_CACHE_DIR:
                # 如果没有配置 HF_HOME，使用 CLIP_CACHE_DIR 的父目录（与CLIP模型保持一致）
                hf_home = os.path.dirname(settings.CLIP_CACHE_DIR)
                logger.info(f"📁 未配置 HF_HOME，使用 CLIP_CACHE_DIR 的父目录作为 HF_HOME: {hf_home}")
            else:
                hf_home = os.path.expanduser("~/.cache/huggingface")
                logger.info(f"📁 使用系统默认 HF_HOME: {hf_home}")
            
            # ⚠️ 关键：强制设置 HF_HOME 环境变量，确保模型下载到配置的目录
            os.environ["HF_HOME"] = hf_home  # 使用 = 而不是 setdefault，确保覆盖
            logger.info(f"✅ 已设置 HF_HOME 环境变量: {hf_home}")
            
            # 延迟导入，避免未安装时出错
            try:
                from FlagEmbedding import FlagReranker
            except ImportError:
                logger.warning(
                    "FlagEmbedding未安装，rerank功能将不可用。"
                    "请安装: pip install FlagEmbedding"
                )
                self.enabled = False
                return
            
            # ⚠️ 关键：优先检查本地缓存，按以下顺序：
            # 1. 配置的本地路径（如果存在）
            # 2. HF缓存目录（配置的或系统默认的）
            # 3. 最后才从网络下载
            
            model_found = False
            model_location = None
            
            # 1. 优先检查配置的本地路径
            if self.model_path:
                from pathlib import Path
                local_path = Path(self.model_path).resolve()
                if local_path.is_dir():
                    expected_files = [
                        "config.json",
                        "tokenizer.json",
                        "tokenizer_config.json",
                        "special_tokens_map.json",
                        "model.safetensors"
                    ]

                    candidate_dirs = [local_path]
                    # 如果目录下只有一个子目录，尝试进入子目录（常见结构 models/rerank/<model-name>/）
                    try:
                        subdirs = [d for d in local_path.iterdir() if d.is_dir()]
                        if len(subdirs) == 1:
                            candidate_dirs.insert(0, subdirs[0])
                        else:
                            candidate_dirs.extend(subdirs)
                    except Exception:
                        pass

                    for candidate in candidate_dirs:
                        if all((candidate / fname).exists() for fname in expected_files):
                            model_found = True
                            model_location = str(candidate)
                            logger.info(f"✅ 在配置的本地路径中发现Rerank模型: {model_location}")
                            logger.info(f"🔧 正在从本地路径加载Rerank模型: {model_location}，设备: {self.device}")
                            self.model = FlagReranker(model_location, use_fp16=False)
                            break
                    else:
                        logger.warning(
                            f"⚠️ 本地模型目录存在但未找到完整的 HuggingFace 模型文件: {local_path}，"
                            "将继续检查缓存或下载。"
                        )
                else:
                    logger.warning(f"⚠️ 配置的本地模型路径不存在: {local_path}")
            if not model_found:
                # 2. 检查HF缓存目录（配置的或系统默认的）
                # FlagEmbedding 使用 huggingface_hub，会自动检查 HF_HOME 下的缓存
                # 如果模型已下载，FlagReranker 会自动使用缓存
                # 但我们需要先检查是否已缓存，避免不必要的网络请求
                hf_cache_dir = hf_home
                cached_model_path = None
                
                # 尝试在HF缓存目录中查找模型
                # HF缓存结构: ~/.cache/huggingface/hub/models--BAAI--bge-reranker-v2-m3/snapshots/xxx/
                if os.path.exists(hf_cache_dir):
                    try:
                        # 查找模型目录（FlagEmbedding使用huggingface_hub的缓存结构）
                        model_dir_name = self.model_name.replace("/", "--")  # BAAI/bge-reranker-v2-m3 -> BAAI--bge-reranker-v2-m3
                        hub_dir = os.path.join(hf_cache_dir, "hub")
                        if os.path.exists(hub_dir):
                            model_cache_dir = os.path.join(hub_dir, f"models--{model_dir_name}")
                            if os.path.exists(model_cache_dir):
                                # 查找snapshots目录
                                snapshots_dir = os.path.join(model_cache_dir, "snapshots")
                                if os.path.exists(snapshots_dir):
                                    # 获取最新的snapshot
                                    snapshots = [d for d in os.listdir(snapshots_dir) if os.path.isdir(os.path.join(snapshots_dir, d))]
                                    if snapshots:
                                        latest_snapshot = sorted(snapshots)[-1]
                                        cached_model_path = os.path.join(snapshots_dir, latest_snapshot)
                                        model_found = True
                                        model_location = cached_model_path
                                        logger.info(f"✅ 在HF缓存目录中发现Rerank模型: {cached_model_path}")
                                        logger.info(f"💡 FlagReranker将自动使用缓存中的模型，无需重新下载")
                    except Exception as e:
                        logger.debug(f"检查HF缓存目录时出错: {e}")
                
                # 3. 如果找到缓存，使用缓存（FlagReranker会自动使用）
                if model_found:
                    logger.info(f"🔧 正在从缓存加载Rerank模型: {self.model_name}，设备: {self.device}")
                    # FlagReranker会自动使用HF_HOME下的缓存，不需要指定路径
                    self.model = FlagReranker(self.model_name, use_fp16=False)
                if not model_found:
                    # 4. 如果本地缓存不存在，才从网络下载
                    if self.model_path:
                        logger.warning(f"⚠️ 本地模型目录不可用: {self.model_path}，将尝试联网下载")
                    logger.info(f"⚠️ 本地缓存中未发现Rerank模型: {self.model_name}")
                    logger.info(f"🌐 将允许联网下载模型（本地模型不存在）")
                    logger.info(f"💾 下载后的模型将保存到缓存目录: {hf_home}")
                    logger.info(f"🔧 正在从HuggingFace下载并加载Rerank模型: {self.model_name}，设备: {self.device}")
                    # FlagReranker会自动下载并保存到HF_HOME下的缓存目录
                    self.model = FlagReranker(self.model_name, use_fp16=False)
                    logger.info(f"✅ Rerank模型下载完成，已保存到: {hf_home}")
            
            # 如果模型支持手动设置设备，尝试设置（FlagReranker内部会自动处理）
            # 这里主要是记录实际使用的设备
            logger.info(f"✅ Rerank模型初始化成功: {self.model_name}，实际使用设备: {self.device}")
            if model_location:
                logger.info(f"📍 模型位置: {model_location}")
            
        except Exception as e:
            logger.error(f"Rerank模型初始化失败: {e}", exc_info=True)
            logger.warning("Rerank功能将不可用，将使用简单排序")
            self.enabled = False
            self.model = None
    
    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """使用rerank模型对搜索结果重新排序
        
        Args:
            query: 查询文本
            candidates: 候选结果列表，每个结果包含 'content' 字段
            top_k: 返回前k个结果（如果为None，使用配置的默认值）
            
        Returns:
            重新排序后的结果列表
        """
        if not self.enabled or self.model is None:
            logger.debug("Rerank未启用或模型未加载，使用原始排序")
            # 降级：按原始分数排序
            sorted_candidates = sorted(
                candidates,
                key=lambda x: x.get("score", 0.0),
                reverse=True
            )
            top_k = top_k or settings.RERANK_TOP_K
            return sorted_candidates[:top_k]
        
        if not candidates:
            return []
        
        try:
            logger.info(f"开始Rerank排序，查询: {query[:50]}..., 候选数量: {len(candidates)}")
            
            # 准备rerank输入：query + 每个候选的content
            pairs = []
            for candidate in candidates:
                content = candidate.get("content", "")
                if not content:
                    continue
                pairs.append([query, content])
            
            if not pairs:
                logger.warning("没有有效的候选内容，返回空结果")
                return []
            
            # 使用rerank模型计算分数
            # FlagReranker.compute_score() 接受列表，返回numpy数组或列表
            import numpy as np
            try:
                # 方式1：批量计算（推荐）
                scores = self.model.compute_score(pairs, normalize=True)
                
                # 转换为列表
                if isinstance(scores, np.ndarray):
                    scores = scores.tolist()
                elif isinstance(scores, (list, tuple)):
                    scores = [float(s) for s in scores]
                elif isinstance(scores, (int, float)):
                    # 如果只有一个分数，转换为列表
                    scores = [float(scores)] * len(pairs)
                else:
                    logger.warning(f"Rerank返回的分数格式不支持: {type(scores)}")
                    scores = [0.0] * len(pairs)
                    
            except Exception as e:
                # 检查是否是CUDA兼容性错误
                error_msg = str(e).lower()
                is_cuda_error = "cuda" in error_msg or "no kernel image" in error_msg
                
                if is_cuda_error and self.device == "cuda":
                    logger.error(f"⚠️ 检测到CUDA兼容性错误: {e}")
                    logger.warning("🔄 自动降级到CPU模式，重新初始化模型...")
                    # 强制切换到CPU并重新初始化
                    self.device = "cpu"
                    try:
                        # 重新初始化模型到CPU
                        from FlagEmbedding import FlagReranker
                        self.model = FlagReranker(self.model_name, use_fp16=False)
                        logger.info("✅ 模型已重新加载到CPU模式")
                        # 重新尝试批量计算
                        scores = self.model.compute_score(pairs, normalize=True)
                        if isinstance(scores, np.ndarray):
                            scores = scores.tolist()
                        elif isinstance(scores, (list, tuple)):
                            scores = [float(s) for s in scores]
                        elif isinstance(scores, (int, float)):
                            scores = [float(scores)] * len(pairs)
                        else:
                            scores = [0.0] * len(pairs)
                    except Exception as e3:
                        logger.error(f"CPU模式重新初始化失败: {e3}")
                        scores = [0.0] * len(pairs)
                else:
                    logger.warning(f"Rerank批量计算失败，尝试逐个计算: {e}")
                    # 降级：逐个计算
                    scores = []
                    for pair in pairs:
                        query_text, passage_text = pair
                        try:
                            score = self.model.compute_score([pair], normalize=True)
                            if isinstance(score, np.ndarray):
                                score = float(score[0])
                            elif isinstance(score, (list, tuple)):
                                score = float(score[0])
                            else:
                                score = float(score)
                            scores.append(score)
                        except Exception as e2:
                            # 检查单个pair计算时的CUDA错误
                            error_msg2 = str(e2).lower()
                            if ("cuda" in error_msg2 or "no kernel image" in error_msg2) and self.device == "cuda":
                                logger.error(f"⚠️ 单个pair计算时检测到CUDA错误: {e2}")
                                logger.warning("🔄 跳过此pair，使用默认分数")
                            else:
                                logger.warning(f"单个pair计算失败: {e2}")
                            scores.append(0.0)
            
            # 更新候选结果的分数
            valid_candidates = []
            score_idx = 0
            for candidate in candidates:
                content = candidate.get("content", "")
                if not content:
                    continue
                
                # 更新rerank分数
                rerank_score = float(scores[score_idx]) if score_idx < len(scores) else 0.0
                # 保存原始分数（融合分数）
                original_score = candidate.get("score", 0.0)
                candidate["original_score"] = original_score
                # 更新rerank分数
                candidate["rerank_score"] = rerank_score
                # 使用rerank分数作为最终分数
                candidate["score"] = rerank_score
                
                valid_candidates.append(candidate)
                score_idx += 1
            
            # 按rerank分数排序
            sorted_candidates = sorted(
                valid_candidates,
                key=lambda x: x.get("rerank_score", 0.0),
                reverse=True
            )
            
            # 返回top_k个结果
            top_k = top_k or settings.RERANK_TOP_K
            result = sorted_candidates[:top_k]
            
            logger.info(f"Rerank排序完成，返回 {len(result)} 个结果")
            return result
            
        except Exception as e:
            logger.error(f"Rerank排序失败: {e}", exc_info=True)
            logger.warning("Rerank失败，降级到简单排序")
            # 降级：按原始分数排序
            sorted_candidates = sorted(
                candidates,
                key=lambda x: x.get("score", 0.0),
                reverse=True
            )
            top_k = top_k or settings.RERANK_TOP_K
            return sorted_candidates[:top_k]
    
    def is_available(self) -> bool:
        """检查rerank模型是否可用"""
        return self.enabled and self.model is not None
