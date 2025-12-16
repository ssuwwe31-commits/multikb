"""
Text Utils
"""

import re
from typing import List, Optional, Dict, Any

def clean_text(text: str) -> str:
    """清理文本"""
    if not text:
        return ""
    
    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text)
    
    # 移除特殊字符
    text = re.sub(r'[^\w\s\u4e00-\u9fff.,!?;:()\[\]{}"\'-]', '', text)
    
    return text.strip()

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """提取关键词"""
    if not text:
        return []
    
    # 简单的关键词提取（可以改进为更复杂的算法）
    words = re.findall(r'\b\w+\b', text.lower())
    
    # 过滤停用词
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these',
        'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him',
        'her', 'us', 'them'
    }
    
    keywords = [word for word in words if word not in stop_words and len(word) > 2]
    
    # 统计词频
    word_count = {}
    for word in keywords:
        word_count[word] = word_count.get(word, 0) + 1
    
    # 按词频排序并返回前N个
    sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
    return [word for word, count in sorted_words[:max_keywords]]

def split_text_into_chunks(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """将文本分割成块"""
    if not text:
        return []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        if end >= len(text):
            chunks.append(text[start:])
            break
        
        # 尝试在句号、问号、感叹号处分割
        last_sentence = text.rfind('.', start, end)
        if last_sentence > start:
            end = last_sentence + 1
        
        chunks.append(text[start:end])
        start = end - overlap
    
    return chunks

def calculate_text_similarity(text1: str, text2: str) -> float:
    """计算文本相似度（简单的Jaccard相似度）"""
    if not text1 or not text2:
        return 0.0
    
    words1 = set(re.findall(r'\b\w+\b', text1.lower()))
    words2 = set(re.findall(r'\b\w+\b', text2.lower()))
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    if not union:
        return 0.0
    
    return len(intersection) / len(union)

def extract_sentences(text: str) -> List[str]:
    """提取句子"""
    if not text:
        return []
    
    # 简单的句子分割
    sentences = re.split(r'[.!?]+', text)
    return [s.strip() for s in sentences if s.strip()]
