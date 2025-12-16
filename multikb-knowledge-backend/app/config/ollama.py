"""
Ollama Configuration
"""

import requests
from app.config.settings import settings

class OllamaConfig:
    """Ollama配置"""
    
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.embedding_model = settings.OLLAMA_EMBEDDING_MODEL
    
    def get_models(self):
        """获取可用模型列表"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取模型列表错误: {e}")
            return {}
    
    def pull_model(self, model_name: str):
        """拉取模型"""
        try:
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"拉取模型错误: {e}")
            return {}

ollama_config = OllamaConfig()
