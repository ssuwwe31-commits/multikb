"""
Image Utils
"""

import os
from PIL import Image
import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict, Any

def get_image_info(image_path: str) -> Optional[Dict[str, Any]]:
    """获取图片信息"""
    try:
        with Image.open(image_path) as img:
            return {
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "mode": img.mode,
                "size": os.path.getsize(image_path)
            }
    except Exception as e:
        print(f"获取图片信息错误: {e}")
        return None

def resize_image(
    image_path: str, 
    output_path: str, 
    max_width: int = 1920, 
    max_height: int = 1080
) -> bool:
    """调整图片大小"""
    try:
        with Image.open(image_path) as img:
            # 计算新的尺寸
            ratio = min(max_width / img.width, max_height / img.height)
            new_width = int(img.width * ratio)
            new_height = int(img.height * ratio)
            
            # 调整大小
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            resized_img.save(output_path, quality=85)
            return True
    except Exception as e:
        print(f"调整图片大小错误: {e}")
        return False

def convert_image_format(
    image_path: str, 
    output_path: str, 
    output_format: str = "JPEG"
) -> bool:
    """转换图片格式"""
    try:
        with Image.open(image_path) as img:
            # 如果是RGBA模式，转换为RGB
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            
            img.save(output_path, format=output_format, quality=85)
            return True
    except Exception as e:
        print(f"转换图片格式错误: {e}")
        return False

def extract_image_features(image_path: str) -> Optional[np.ndarray]:
    """提取图片特征"""
    try:
        # 使用OpenCV提取特征
        img = cv2.imread(image_path)
        if img is None:
            return None
        
        # 转换为灰度图
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 使用SIFT特征提取
        sift = cv2.SIFT_create()
        keypoints, descriptors = sift.detectAndCompute(gray, None)
        
        return descriptors
    except Exception as e:
        print(f"提取图片特征错误: {e}")
        return None

def calculate_image_similarity(features1: np.ndarray, features2: np.ndarray) -> float:
    """计算图片相似度"""
    try:
        if features1 is None or features2 is None:
            return 0.0
        
        # 使用FLANN匹配器
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)
        
        matches = flann.knnMatch(features1, features2, k=2)
        
        # 应用Lowe's ratio test
        good_matches = []
        for match_pair in matches:
            if len(match_pair) == 2:
                m, n = match_pair
                if m.distance < 0.7 * n.distance:
                    good_matches.append(m)
        
        # 计算相似度
        similarity = len(good_matches) / max(len(features1), len(features2))
        return min(similarity, 1.0)
    except Exception as e:
        print(f"计算图片相似度错误: {e}")
        return 0.0

def is_valid_image(image_path: str) -> bool:
    """检查是否为有效图片"""
    try:
        with Image.open(image_path) as img:
            img.verify()
        return True
    except Exception:
        return False
