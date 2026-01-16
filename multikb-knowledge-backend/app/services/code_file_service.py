"""
Code File Service
代码文件管理服务
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import hashlib
import os

from app.core.logging import logger
from app.models.code_file import CodeFile
from app.models.code_repository import CodeRepository
from app.services.nebula_code_service import get_nebula_code_service
from app.config.settings import settings


class CodeFileService:
    """代码文件管理服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_file(
        self, 
        repository_id: int,
        file_path: str,
        file_name: str,
        file_type: Optional[str] = None,
        language: Optional[str] = None,
        content: Optional[str] = None,
        **kwargs
    ) -> CodeFile:
        """
        创建代码文件记录
        
        Args:
            repository_id: 仓库ID
            file_path: 文件路径
            file_name: 文件名
            file_type: 文件类型
            language: 编程语言
            content: 文件内容（可选，用于计算哈希）
            **kwargs: 其他字段
            
        Returns:
            创建的文件对象
        """
        try:
            # 1. 检查仓库是否存在
            repo = self.db.query(CodeRepository).filter(
                CodeRepository.id == repository_id
            ).first()
            
            if not repo:
                raise ValueError(f"Repository {repository_id} not found")
            
            # 2. 检查文件是否已存在
            existing_file = self.db.query(CodeFile).filter(
                CodeFile.repository_id == repository_id,
                CodeFile.file_path == file_path
            ).first()
            
            if existing_file and not existing_file.is_deleted:
                logger.warning(f"文件已存在: {file_path}")
                return existing_file
            
            # 3. 计算内容哈希
            content_hash = None
            if content:
                content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            # 4. 创建文件记录
            file_data = {
                "repository_id": repository_id,
                "knowledge_base_id": repo.knowledge_base_id,
                "file_path": file_path,
                "file_name": file_name,
                "file_type": file_type,
                "language": language or self._detect_language(file_name),
                "content_hash": content_hash,
                **kwargs
            }
            
            code_file = CodeFile(**file_data)
            self.db.add(code_file)
            self.db.commit()
            self.db.refresh(code_file)
            
            # 不再输出每个文件的日志，减少日志量
            # 如果需要调试，可以启用下面的日志（每100个文件记录一次）
            # if code_file.id % 100 == 0:
            #     logger.debug(f"创建代码文件记录: {file_path} (ID: {code_file.id})")
            return code_file
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建代码文件记录失败: {e}")
            raise
    
    def get_file(self, file_id: int) -> Optional[CodeFile]:
        """获取文件记录"""
        return self.db.query(CodeFile).filter(
            CodeFile.id == file_id,
            CodeFile.is_deleted == False
        ).first()
    
    def get_file_by_path(self, repository_id: int, file_path: str) -> Optional[CodeFile]:
        """根据路径获取文件"""
        return self.db.query(CodeFile).filter(
            CodeFile.repository_id == repository_id,
            CodeFile.file_path == file_path,
            CodeFile.is_deleted == False
        ).first()
    
    def list_files(
        self,
        repository_id: Optional[int] = None,
        knowledge_base_id: Optional[int] = None,
        language: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        列出代码文件
        
        Args:
            repository_id: 仓库ID筛选
            knowledge_base_id: 知识库ID筛选
            language: 语言筛选
            page: 页码
            page_size: 每页大小
            
        Returns:
            分页结果
        """
        try:
            query = self.db.query(CodeFile).filter(CodeFile.is_deleted == False)
            
            # 应用筛选
            if repository_id:
                query = query.filter(CodeFile.repository_id == repository_id)
            if knowledge_base_id:
                query = query.filter(CodeFile.knowledge_base_id == knowledge_base_id)
            if language:
                query = query.filter(CodeFile.language == language)
            
            # 统计总数
            total = query.count()
            
            # 分页
            files = query.order_by(CodeFile.created_at.desc()).offset(
                (page - 1) * page_size
            ).limit(page_size).all()
            
            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "files": files
            }
            
        except Exception as e:
            logger.error(f"列出代码文件失败: {e}")
            raise
    
    def update_file(self, file_id: int, **kwargs) -> CodeFile:
        """
        更新文件记录
        
        Args:
            file_id: 文件ID
            **kwargs: 要更新的字段
            
        Returns:
            更新后的文件对象
        """
        try:
            code_file = self.get_file(file_id)
            if not code_file:
                raise ValueError(f"File {file_id} not found")
            
            # 更新字段
            for key, value in kwargs.items():
                if hasattr(code_file, key):
                    setattr(code_file, key, value)
            
            code_file.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(code_file)
            
            logger.info(f"更新代码文件成功: {code_file.file_path}")
            return code_file
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新代码文件失败: {e}")
            raise
    
    def delete_file(self, file_id: int, hard_delete: bool = False) -> bool:
        """
        删除文件记录
        
        Args:
            file_id: 文件ID
            hard_delete: 是否物理删除
            
        Returns:
            是否成功
        """
        try:
            code_file = self.get_file(file_id)
            if not code_file:
                return False
            
            if hard_delete:
                # 物理删除
                self.db.delete(code_file)
            else:
                # 软删除
                code_file.is_deleted = True
            
            self.db.commit()
            logger.info(f"删除代码文件成功: {code_file.file_path}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除代码文件失败: {e}")
            raise
    
    def batch_import_files(
        self,
        repository_id: int,
        files_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        批量导入代码文件
        
        Args:
            repository_id: 仓库ID
            files_data: 文件数据列表
            
        Returns:
            导入统计
        """
        try:
            success_count = 0
            error_count = 0
            errors = []
            
            for file_data in files_data:
                try:
                    self.create_file(repository_id=repository_id, **file_data)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    errors.append({
                        "file": file_data.get("file_path", "unknown"),
                        "error": str(e)
                    })
                    logger.error(f"导入文件失败: {e}")
            
            stats = {
                "total": len(files_data),
                "success": success_count,
                "error": error_count,
                "errors": errors
            }
            
            logger.info(f"批量导入完成: {success_count}/{len(files_data)}")
            return stats
            
        except Exception as e:
            logger.error(f"批量导入代码文件失败: {e}")
            raise
    
    async def sync_to_graph(self, file_id: int) -> Dict[str, Any]:
        """
        同步文件到知识图谱
        
        Args:
            file_id: 文件ID
            
        Returns:
            同步结果
        """
        try:
            code_file = self.get_file(file_id)
            if not code_file:
                raise ValueError(f"File {file_id} not found")
            
            # 使用 NebulaCodeService 同步
            nebula_service = get_nebula_code_service(self.db)
            result = await nebula_service.sync_code_file(file_id)
            
            logger.info(f"同步文件到图谱成功: {code_file.file_path}")
            return result
            
        except Exception as e:
            logger.error(f"同步文件到图谱失败: {e}")
            raise
    
    async def batch_sync_to_graph(
        self,
        repository_id: int
    ) -> Dict[str, Any]:
        """
        批量同步仓库的所有文件到图谱
        
        Args:
            repository_id: 仓库ID
            
        Returns:
            同步统计
        """
        try:
            # 获取所有文件
            files = self.db.query(CodeFile).filter(
                CodeFile.repository_id == repository_id,
                CodeFile.is_deleted == False
            ).all()
            
            success_count = 0
            error_count = 0
            
            nebula_service = get_nebula_code_service(self.db)
            
            for file in files:
                try:
                    await nebula_service.sync_code_file(file.id)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(f"同步文件失败 {file.file_path}: {e}")
            
            stats = {
                "total": len(files),
                "success": success_count,
                "error": error_count
            }
            
            logger.info(f"批量同步完成: {success_count}/{len(files)}")
            return stats
            
        except Exception as e:
            logger.error(f"批量同步文件到图谱失败: {e}")
            raise
    
    def detect_file_changes(self, file_id: int, new_content: str) -> bool:
        """
        检测文件是否发生变更（基于内容哈希）
        
        Args:
            file_id: 文件ID
            new_content: 新的文件内容
            
        Returns:
            是否发生变更
        """
        try:
            code_file = self.get_file(file_id)
            if not code_file:
                return False
            
            # 计算新内容的哈希
            new_hash = hashlib.sha256(new_content.encode('utf-8')).hexdigest()
            
            # 比较哈希
            if code_file.content_hash != new_hash:
                logger.info(f"检测到文件变更: {code_file.file_path}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"检测文件变更失败: {e}")
            return False
    
    def get_language_stats(self, repository_id: int) -> Dict[str, int]:
        """
        获取仓库的语言统计
        
        Args:
            repository_id: 仓库ID
            
        Returns:
            语言统计 {language: count}
        """
        try:
            result = self.db.query(
                CodeFile.language,
                func.count(CodeFile.id).label('count')
            ).filter(
                CodeFile.repository_id == repository_id,
                CodeFile.is_deleted == False
            ).group_by(CodeFile.language).all()
            
            return {row.language or 'unknown': row.count for row in result}
            
        except Exception as e:
            logger.error(f"获取语言统计失败: {e}")
            return {}
    
    def _detect_language(self, file_name: str) -> str:
        """
        根据文件扩展名检测编程语言
        
        Args:
            file_name: 文件名
            
        Returns:
            语言名称
        """
        ext = os.path.splitext(file_name)[1].lower()
        
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.m': 'objective-c',
            '.scala': 'scala',
            '.r': 'r',
            '.sql': 'sql',
            '.sh': 'shell',
            '.bash': 'shell',
            '.ps1': 'powershell',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.json': 'json',
            '.xml': 'xml',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.vue': 'vue',
            '.md': 'markdown',
        }
        
        return language_map.get(ext, 'unknown')


# ============================================
# 便捷函数
# ============================================

def get_code_file_service(db: Session) -> CodeFileService:
    """获取 CodeFile 服务实例"""
    return CodeFileService(db)
