"""
Ollama Dependencies
"""

from fastapi import Depends
from app.config.ollama import ollama_config

def get_ollama_config():
    """获取Ollama配置"""
    return ollama_config
