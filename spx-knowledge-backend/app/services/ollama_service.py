"""
Ollama Service
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import requests
import json
import time
from app.config.settings import settings
from app.core.logging import logger
import base64

class OllamaService:
    """Ollama服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.base_url = settings.OLLAMA_BASE_URL
    
    async def generate_text(
        self, 
        prompt: str, 
        model: str = settings.OLLAMA_MODEL,
        format: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> str:
        """生成文本
        
        Args:
            prompt: 提示词
            model: 模型名称
            format: 输出格式，如 "json" 用于强制 JSON 输出（Ollama 支持）
            timeout: 超时时间（秒），默认使用 OLLAMA_TIMEOUT 配置
        """
        request_timeout = timeout or getattr(settings, 'OLLAMA_TIMEOUT', 300)
        prompt_length = len(prompt)
        
        try:
            logger.info(f"开始调用Ollama生成文本: 模型={model}, 提示词长度={prompt_length} 字符, 超时={request_timeout}秒, format={format}")
            
            request_data = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }
            # 如果指定了 format，添加到请求中（Ollama 支持 format 参数强制 JSON 输出）
            if format:
                request_data["format"] = format
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=request_data,
                timeout=request_timeout
            )
            response.raise_for_status()
            result = response.json()
            response_text = result.get("response", "")
            response_length = len(response_text)
            logger.info(f"Ollama文本生成完成: 响应长度={response_length} 字符")
            return response_text
        except requests.exceptions.Timeout as e:
            logger.error(f"Ollama文本生成超时: 模型={model}, 超时时间={request_timeout}秒, 提示词长度={prompt_length} 字符")
            raise Exception(f"Ollama请求超时（{request_timeout}秒）")
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama文本生成请求错误: {e}, 模型={model}, 提示词长度={prompt_length} 字符")
            raise Exception(f"Ollama请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"Ollama文本生成错误: {e}, 模型={model}, 提示词长度={prompt_length} 字符", exc_info=True)
            raise Exception(f"Ollama文本生成失败: {str(e)}")
    
    async def generate_embedding(
        self, 
        text: str, 
        model: str = settings.OLLAMA_EMBEDDING_MODEL
    ) -> List[float]:
        """生成嵌入向量"""
        try:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": model,
                    "prompt": text
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("embedding", [])
        except Exception as e:
            print(f"Ollama向量生成错误: {e}")
            return []
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str = settings.OLLAMA_MODEL
    ) -> str:
        """聊天完成"""
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("message", {}).get("content", "")
        except Exception as e:
            print(f"Ollama聊天完成错误: {e}")
            return ""
    
    async def generate_answer(self, prompt: str, model: str = settings.OLLAMA_MODEL) -> str:
        """生成答案（generate_text的别名，用于兼容）"""
        try:
            return await self.generate_text(prompt, model)
        except Exception as e:
            print(f"Ollama生成答案错误: {e}")
            return ""
    
    def extract_text_from_image(
        self,
        image_bytes: bytes,
        image_mime: str = "image/png",
        prompt: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> str:
        """调用 Ollama 多模态模型识别图片文字"""
        prompt_text = prompt or "请识别这张图片中的所有文字，保持段落与换行。"
        target_model = model or settings.OLLAMA_OCR_MODEL or settings.OLLAMA_MODEL
        base_url = settings.OLLAMA_OCR_BASE_URL or self.base_url
        request_timeout = timeout or settings.OLLAMA_OCR_TIMEOUT
        max_retries = max(0, settings.OLLAMA_OCR_MAX_RETRIES)
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        payload = {
            "model": target_model,
            "prompt": prompt_text,
            "images": [encoded],
            "stream": False,
        }
        last_error: Optional[str] = None
        is_timeout_error = False
        
        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"OCR 尝试 {attempt + 1}/{max_retries + 1}: 模型={target_model}, 图片大小={len(image_bytes)} bytes")
                response = requests.post(
                    f"{base_url}/api/generate",
                    json=payload,
                    timeout=request_timeout,
                )
                response.raise_for_status()
                result = response.json()
                content = result.get("response", "")
                logger.debug(f"OCR 成功: 返回内容长度={len(content)}")
                return (content or "").strip()
            except requests.exceptions.Timeout as e:
                # 超时错误：使用更长的重试间隔
                is_timeout_error = True
                last_error = f"请求超时: {str(e)}"
                logger.warning(f"OCR 请求超时 (尝试 {attempt + 1}/{max_retries + 1}): {last_error}")
                if attempt < max_retries:
                    # 指数退避：超时错误使用更长的等待时间
                    # 第1次重试：5秒，第2次重试：15秒
                    wait_time = 5 * (2 ** attempt) if attempt > 0 else 5
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
            except requests.exceptions.HTTPError as e:
                # HTTP 错误，记录详细错误信息
                is_timeout_error = False
                error_detail = f"HTTP {e.response.status_code}"
                try:
                    error_body = e.response.json()
                    error_detail += f": {error_body}"
                except:
                    error_detail += f": {e.response.text[:200]}"
                last_error = f"{error_detail} (URL: {base_url}/api/generate)"
                logger.warning(f"OCR HTTP 错误 (尝试 {attempt + 1}/{max_retries + 1}): {last_error}")
                if attempt < max_retries:
                    # 指数退避：1秒、2秒、4秒
                    wait_time = 2 ** attempt
                    logger.debug(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
            except requests.exceptions.RequestException as e:
                # 其他请求错误（包括连接错误等）
                is_timeout_error = False
                last_error = f"请求错误: {str(e)}"
                logger.warning(f"OCR 请求错误 (尝试 {attempt + 1}/{max_retries + 1}): {last_error}")
                if attempt < max_retries:
                    # 指数退避：1秒、2秒、4秒
                    wait_time = 2 ** attempt
                    logger.debug(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
            except Exception as exc:
                # 未知错误
                is_timeout_error = False
                last_error = f"未知错误: {str(exc)}"
                logger.warning(f"OCR 未知错误 (尝试 {attempt + 1}/{max_retries + 1}): {last_error}")
                if attempt < max_retries:
                    # 指数退避：1秒、2秒、4秒
                    wait_time = 2 ** attempt
                    logger.debug(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
        
        # 所有重试都失败
        error_msg = f"OCR识别失败: {last_error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = settings.OLLAMA_MODEL
    ):
        """流式聊天完成"""
        import asyncio
        from typing import AsyncGenerator
        
        try:
            # 在线程池中执行同步请求，避免阻塞事件循环
            loop = asyncio.get_event_loop()
            
            def _make_stream_request():
                """在线程池中执行的同步请求"""
                response = requests.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": True
                    },
                    stream=True,
                    timeout=300
                )
                response.raise_for_status()
                return response
            
            # 在线程池中执行请求
            response = await loop.run_in_executor(None, _make_stream_request)
            
            # 在线程池中读取流式响应
            def _read_stream():
                """在线程池中读取流式数据"""
                chunks = []
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            content = data.get("message", {}).get("content", "")
                            done = data.get("done", False)
                            chunks.append((content, done))
                            if done:
                                break
                        except json.JSONDecodeError:
                            continue
                return chunks
            
            # 在线程池中读取流
            chunks = await loop.run_in_executor(None, _read_stream)
            
            # 异步yield结果
            for content, done in chunks:
                if content:
                    yield content
                if done:
                    break
                    
        except Exception as e:
            import traceback
            print(f"Ollama流式聊天完成错误: {e}")
            print(traceback.format_exc())
            yield f"错误: {str(e)}"
