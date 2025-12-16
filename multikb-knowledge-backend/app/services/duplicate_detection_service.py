"""
Duplicate Detection Service
根据文档处理流程设计实现重复检测功能
"""

from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.document import Document
from app.core.logging import logger
from app.core.exceptions import CustomException, ErrorCode

class DuplicateDetectionService:
    """重复检测服务 - 严格按照设计文档实现"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def check_duplicate_by_hash(self, file_hash: str) -> Optional[Document]:
        """基于文件哈希的重复检测 - 根据设计文档实现"""
        try:
            logger.info(f"开始基于哈希的重复检测: {file_hash[:8]}...")
            
            # 根据设计文档要求：
            # 1. 文件哈希对比: 基于文件内容的MD5/SHA256
            # 2. 文件名+大小对比: 防止同名不同内容文件
            
            existing_doc = self.db.query(Document).filter(
                Document.file_hash == file_hash
            ).first()
            
            if existing_doc:
                logger.warning(f"发现重复文件: {existing_doc.original_filename} (ID: {existing_doc.id})")
                return existing_doc
            else:
                logger.info(f"未发现重复文件: {file_hash[:8]}...")
                return None
                
        except Exception as e:
            logger.error(f"重复检测错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"重复检测失败: {str(e)}"
            )
    
    def check_duplicate_by_name_and_size(self, filename: str, file_size: int) -> Optional[Document]:
        """基于文件名和大小的重复检测 - 根据设计文档实现"""
        try:
            logger.info(f"开始基于文件名和大小的重复检测: {filename}")
            
            existing_doc = self.db.query(Document).filter(
                Document.original_filename == filename,
                Document.file_size == file_size
            ).first()
            
            if existing_doc:
                logger.warning(f"发现同名同大小文件: {filename} (ID: {existing_doc.id})")
                return existing_doc
            else:
                logger.info(f"未发现同名同大小文件: {filename}")
                return None
                
        except Exception as e:
            logger.error(f"重复检测错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"重复检测失败: {str(e)}"
            )
    
    def check_duplicate_comprehensive(self, filename: str, file_size: int, file_hash: str) -> Dict[str, Any]:
        """综合重复检测 - 根据设计文档实现"""
        try:
            logger.info(f"开始综合重复检测: {filename}")
            
            # 1. 基于哈希检测
            hash_duplicate = self.check_duplicate_by_hash(file_hash)
            
            # 2. 基于文件名和大小检测
            name_size_duplicate = self.check_duplicate_by_name_and_size(filename, file_size)
            
            # 分析检测结果
            duplicate_type = None
            duplicate_doc = None
            
            if hash_duplicate and name_size_duplicate:
                if hash_duplicate.id == name_size_duplicate.id:
                    duplicate_type = "exact_match"  # 完全匹配
                    duplicate_doc = hash_duplicate
                else:
                    duplicate_type = "hash_match_different_name"  # 哈希匹配但文件名不同
                    duplicate_doc = hash_duplicate
            elif hash_duplicate:
                duplicate_type = "hash_match"  # 仅哈希匹配
                duplicate_doc = hash_duplicate
            elif name_size_duplicate:
                duplicate_type = "name_size_match"  # 仅文件名和大小匹配
                duplicate_doc = name_size_duplicate
            
            result = {
                "is_duplicate": duplicate_doc is not None,
                "duplicate_type": duplicate_type,
                "duplicate_document": duplicate_doc,
                "hash_match": hash_duplicate is not None,
                "name_size_match": name_size_duplicate is not None,
                "detection_timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            if duplicate_doc:
                logger.warning(f"检测到重复文件: {filename}, 类型: {duplicate_type}, 重复文档ID: {duplicate_doc.id}")
            else:
                logger.info(f"未检测到重复文件: {filename}")
            
            return result
            
        except Exception as e:
            logger.error(f"综合重复检测错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"综合重复检测失败: {str(e)}"
            )
    
    def handle_duplicate_detection(self, duplicate_result: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """处理重复检测结果 - 根据设计文档实现"""
        try:
            logger.info(f"开始处理重复检测结果: {filename}")
            
            if not duplicate_result["is_duplicate"]:
                return {
                    "action": "proceed",
                    "message": "未检测到重复文件，可以继续上传"
                }
            
            duplicate_type = duplicate_result["duplicate_type"]
            duplicate_doc = duplicate_result["duplicate_document"]
            
            # 根据重复类型决定处理策略
            if duplicate_type == "exact_match":
                # 完全匹配 - 拒绝上传
                logger.warning(f"完全重复文件，拒绝上传: {filename}")
                raise CustomException(
                    code=ErrorCode.DOCUMENT_ALREADY_EXISTS,
                    message=f"文件 '{filename}' 已存在 (ID: {duplicate_doc.id})，内容完全相同"
                )
            
            elif duplicate_type == "hash_match":
                # 哈希匹配但文件名不同 - 警告但允许上传
                logger.warning(f"哈希匹配但文件名不同: {filename} vs {duplicate_doc.original_filename}")
                return {
                    "action": "warning",
                    "message": f"检测到内容相同的文件 '{duplicate_doc.original_filename}' (ID: {duplicate_doc.id})，但文件名不同",
                    "duplicate_document_id": duplicate_doc.id,
                    "allow_upload": True
                }
            
            elif duplicate_type == "name_size_match":
                # 文件名和大小匹配但内容不同 - 警告但允许上传
                logger.warning(f"文件名和大小匹配但内容不同: {filename}")
                return {
                    "action": "warning",
                    "message": f"检测到同名同大小的文件 '{duplicate_doc.original_filename}' (ID: {duplicate_doc.id})，但内容不同",
                    "duplicate_document_id": duplicate_doc.id,
                    "allow_upload": True
                }
            
            else:
                # 其他情况 - 允许上传
                return {
                    "action": "proceed",
                    "message": "检测到相似文件但允许上传"
                }
                
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"处理重复检测结果错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"处理重复检测结果失败: {str(e)}"
            )
