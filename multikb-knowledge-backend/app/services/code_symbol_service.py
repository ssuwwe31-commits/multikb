"""
Code Symbol Service
代码符号分析服务 - 管理函数、类、方法等代码符号
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime

from app.core.logging import logger
from app.models.code_symbol import CodeSymbol
from app.models.code_file import CodeFile
from app.models.code_repository import CodeRepository
from app.services.nebula_code_service import get_nebula_code_service
from app.services.code_parser_service import CodeParserService


class CodeSymbolService:
    """代码符号管理服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.parser = CodeParserService()
    
    def create_symbol(
        self,
        file_id: int,
        symbol_name: str,
        symbol_type: str,
        **kwargs
    ) -> CodeSymbol:
        """
        创建代码符号记录
        
        Args:
            file_id: 文件ID
            symbol_name: 符号名称
            symbol_type: 符号类型（function/class/method/variable）
            **kwargs: 其他字段
            
        Returns:
            创建的符号对象
        """
        try:
            # 1. 检查文件是否存在
            code_file = self.db.query(CodeFile).filter(
                CodeFile.id == file_id
            ).first()
            
            if not code_file:
                raise ValueError(f"File {file_id} not found")
            
            # 2. 创建符号记录
            symbol_data = {
                "file_id": file_id,
                "repository_id": code_file.repository_id,
                "knowledge_base_id": code_file.knowledge_base_id,
                "symbol_name": symbol_name,
                "symbol_type": symbol_type,
                **kwargs
            }
            
            symbol = CodeSymbol(**symbol_data)
            self.db.add(symbol)
            self.db.commit()
            self.db.refresh(symbol)
            
            # 不再输出每个符号的日志，减少日志量
            # 如果需要调试，可以启用下面的日志（每1000个符号记录一次）
            # if symbol.id % 1000 == 0:
            #     logger.debug(f"创建代码符号: {symbol_name} ({symbol_type}), ID: {symbol.id}")
            return symbol
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建代码符号失败: {e}")
            raise
    
    def get_symbol(self, symbol_id: int) -> Optional[CodeSymbol]:
        """获取符号记录"""
        return self.db.query(CodeSymbol).filter(
            CodeSymbol.id == symbol_id,
            CodeSymbol.is_deleted == False
        ).first()
    
    def list_symbols(
        self,
        file_id: Optional[int] = None,
        repository_id: Optional[int] = None,
        symbol_type: Optional[str] = None,
        search_name: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        列出代码符号
        
        Args:
            file_id: 文件ID筛选
            repository_id: 仓库ID筛选
            symbol_type: 符号类型筛选
            search_name: 符号名称搜索
            page: 页码
            page_size: 每页大小
            
        Returns:
            分页结果
        """
        try:
            query = self.db.query(CodeSymbol).filter(CodeSymbol.is_deleted == False)
            
            # 应用筛选
            if file_id:
                query = query.filter(CodeSymbol.file_id == file_id)
            if repository_id:
                query = query.filter(CodeSymbol.repository_id == repository_id)
            if symbol_type:
                query = query.filter(CodeSymbol.symbol_type == symbol_type)
            if search_name:
                query = query.filter(
                    or_(
                        CodeSymbol.symbol_name.like(f"%{search_name}%"),
                        CodeSymbol.qualified_name.like(f"%{search_name}%")
                    )
                )
            
            # 统计总数
            total = query.count()
            
            # 分页
            symbols = query.order_by(CodeSymbol.created_at.desc()).offset(
                (page - 1) * page_size
            ).limit(page_size).all()
            
            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "symbols": symbols
            }
            
        except Exception as e:
            logger.error(f"列出代码符号失败: {e}")
            raise
    
    def update_symbol(self, symbol_id: int, **kwargs) -> CodeSymbol:
        """
        更新符号记录
        
        Args:
            symbol_id: 符号ID
            **kwargs: 要更新的字段
            
        Returns:
            更新后的符号对象
        """
        try:
            symbol = self.get_symbol(symbol_id)
            if not symbol:
                raise ValueError(f"Symbol {symbol_id} not found")
            
            # 更新字段
            for key, value in kwargs.items():
                if hasattr(symbol, key):
                    setattr(symbol, key, value)
            
            symbol.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(symbol)
            
            logger.info(f"更新代码符号成功: {symbol.symbol_name}")
            return symbol
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新代码符号失败: {e}")
            raise
    
    def delete_symbol(self, symbol_id: int, hard_delete: bool = False) -> bool:
        """
        删除符号记录
        
        Args:
            symbol_id: 符号ID
            hard_delete: 是否物理删除
            
        Returns:
            是否成功
        """
        try:
            symbol = self.get_symbol(symbol_id)
            if not symbol:
                return False
            
            if hard_delete:
                # 物理删除
                self.db.delete(symbol)
            else:
                # 软删除
                symbol.is_deleted = True
            
            self.db.commit()
            logger.info(f"删除代码符号成功: {symbol.symbol_name}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除代码符号失败: {e}")
            raise
    
    def extract_symbols_from_file(
        self,
        file_id: int,
        file_content: str
    ) -> Dict[str, Any]:
        """
        从代码文件中提取符号
        
        Args:
            file_id: 文件ID
            file_content: 文件内容
            
        Returns:
            提取统计
        """
        try:
            # 1. 获取文件信息
            code_file = self.db.query(CodeFile).filter(
                CodeFile.id == file_id
            ).first()
            
            if not code_file:
                raise ValueError(f"File {file_id} not found")
            
            # 2. 解析代码获取符号
            language = code_file.language
            if not language or language == 'unknown':
                logger.warning(f"无法解析语言: {code_file.file_path}")
                return {"total": 0, "success": 0, "error": 0}
            
            # 使用 CodeParserService 解析代码
            parse_result = self.parser.parse_code(file_content, language)
            
            if not parse_result:
                logger.warning(f"解析代码失败: {code_file.file_path}")
                return {"total": 0, "success": 0, "error": 0}
            
            # 3. 提取符号信息
            symbols_data = []
            
            # 提取函数
            if 'functions' in parse_result:
                for func in parse_result['functions']:
                    symbols_data.append({
                        "symbol_type": "function",
                        "symbol_name": func.get('name', 'unknown'),
                        "qualified_name": func.get('qualified_name'),
                        "signature": func.get('signature'),
                        "start_line": func.get('start_line'),
                        "end_line": func.get('end_line'),
                        "docstring": func.get('docstring'),
                        "parameters": func.get('parameters'),
                        "return_type": func.get('return_type'),
                        "complexity_score": func.get('complexity'),
                        "lines_count": func.get('lines_count')
                    })
            
            # 提取类
            if 'classes' in parse_result:
                for cls in parse_result['classes']:
                    # 类本身
                    class_symbol_data = {
                        "symbol_type": "class",
                        "symbol_name": cls.get('name', 'unknown'),
                        "qualified_name": cls.get('qualified_name'),
                        "signature": cls.get('signature'),
                        "start_line": cls.get('start_line'),
                        "end_line": cls.get('end_line'),
                        "docstring": cls.get('docstring'),
                        "complexity_score": cls.get('complexity'),
                        "lines_count": cls.get('lines_count')
                    }
                    symbols_data.append(class_symbol_data)
                    
                    # 类的方法
                    if 'methods' in cls:
                        for method in cls['methods']:
                            symbols_data.append({
                                "symbol_type": "method",
                                "symbol_name": method.get('name', 'unknown'),
                                "qualified_name": f"{cls.get('name')}.{method.get('name')}",
                                "signature": method.get('signature'),
                                "start_line": method.get('start_line'),
                                "end_line": method.get('end_line'),
                                "docstring": method.get('docstring'),
                                "parameters": method.get('parameters'),
                                "return_type": method.get('return_type'),
                                "complexity_score": method.get('complexity'),
                                "lines_count": method.get('lines_count')
                            })
            
            # 4. 批量创建符号记录
            success_count = 0
            error_count = 0
            
            for symbol_data in symbols_data:
                try:
                    self.create_symbol(file_id=file_id, **symbol_data)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(f"创建符号失败: {e}")
            
            # 5. 更新文件的符号统计
            code_file.symbols_count = success_count
            self.db.commit()
            
            stats = {
                "total": len(symbols_data),
                "success": success_count,
                "error": error_count
            }
            
            logger.info(f"提取符号完成: {code_file.file_path}, {success_count}/{len(symbols_data)}")
            return stats
            
        except Exception as e:
            logger.error(f"从文件提取符号失败: {e}")
            raise
    
    def batch_extract_symbols(
        self,
        repository_id: int
    ) -> Dict[str, Any]:
        """
        批量提取仓库所有文件的符号
        
        Args:
            repository_id: 仓库ID
            
        Returns:
            提取统计
        """
        try:
            # 获取所有文件
            files = self.db.query(CodeFile).filter(
                CodeFile.repository_id == repository_id,
                CodeFile.is_deleted == False
            ).all()
            
            total_symbols = 0
            success_files = 0
            error_files = 0
            
            for file in files:
                try:
                    # 读取文件内容（假设已经克隆到本地）
                    repo = self.db.query(CodeRepository).filter(
                        CodeRepository.id == repository_id
                    ).first()
                    
                    if not repo or not repo.local_path:
                        logger.warning(f"仓库未克隆到本地: {repository_id}")
                        continue
                    
                    import os
                    file_full_path = os.path.join(repo.local_path, file.file_path)
                    
                    if not os.path.exists(file_full_path):
                        logger.warning(f"文件不存在: {file_full_path}")
                        continue
                    
                    with open(file_full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 提取符号
                    result = self.extract_symbols_from_file(file.id, content)
                    total_symbols += result['success']
                    success_files += 1
                    
                except Exception as e:
                    error_files += 1
                    logger.error(f"处理文件失败 {file.file_path}: {e}")
            
            stats = {
                "total_files": len(files),
                "success_files": success_files,
                "error_files": error_files,
                "total_symbols": total_symbols
            }
            
            logger.info(f"批量提取符号完成: {success_files}/{len(files)} files, {total_symbols} symbols")
            return stats
            
        except Exception as e:
            logger.error(f"批量提取符号失败: {e}")
            raise
    
    async def sync_to_graph(self, symbol_id: int) -> Dict[str, Any]:
        """
        同步符号到知识图谱
        
        Args:
            symbol_id: 符号ID
            
        Returns:
            同步结果
        """
        try:
            symbol = self.get_symbol(symbol_id)
            if not symbol:
                raise ValueError(f"Symbol {symbol_id} not found")
            
            # 使用 NebulaCodeService 同步
            nebula_service = get_nebula_code_service(self.db)
            result = await nebula_service.sync_code_symbol(symbol_id)
            
            logger.info(f"同步符号到图谱成功: {symbol.qualified_name}")
            return result
            
        except Exception as e:
            logger.error(f"同步符号到图谱失败: {e}")
            raise
    
    async def batch_sync_to_graph(
        self,
        file_id: Optional[int] = None,
        repository_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        批量同步符号到图谱
        
        Args:
            file_id: 文件ID（同步该文件的所有符号）
            repository_id: 仓库ID（同步该仓库的所有符号）
            
        Returns:
            同步统计
        """
        try:
            query = self.db.query(CodeSymbol).filter(CodeSymbol.is_deleted == False)
            
            if file_id:
                query = query.filter(CodeSymbol.file_id == file_id)
            elif repository_id:
                query = query.filter(CodeSymbol.repository_id == repository_id)
            else:
                raise ValueError("Must provide either file_id or repository_id")
            
            symbols = query.all()
            
            success_count = 0
            error_count = 0
            
            nebula_service = get_nebula_code_service(self.db)
            
            for symbol in symbols:
                try:
                    await nebula_service.sync_code_symbol(symbol.id)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(f"同步符号失败 {symbol.symbol_name}: {e}")
            
            stats = {
                "total": len(symbols),
                "success": success_count,
                "error": error_count
            }
            
            logger.info(f"批量同步符号完成: {success_count}/{len(symbols)}")
            return stats
            
        except Exception as e:
            logger.error(f"批量同步符号到图谱失败: {e}")
            raise
    
    def get_symbol_stats(
        self,
        repository_id: Optional[int] = None,
        file_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取符号统计信息
        
        Args:
            repository_id: 仓库ID
            file_id: 文件ID
            
        Returns:
            统计信息
        """
        try:
            query = self.db.query(CodeSymbol).filter(CodeSymbol.is_deleted == False)
            
            if repository_id:
                query = query.filter(CodeSymbol.repository_id == repository_id)
            if file_id:
                query = query.filter(CodeSymbol.file_id == file_id)
            
            # 总数
            total = query.count()
            
            # 按类型统计
            type_stats = self.db.query(
                CodeSymbol.symbol_type,
                func.count(CodeSymbol.id).label('count')
            ).filter(CodeSymbol.is_deleted == False)
            
            if repository_id:
                type_stats = type_stats.filter(CodeSymbol.repository_id == repository_id)
            if file_id:
                type_stats = type_stats.filter(CodeSymbol.file_id == file_id)
            
            type_stats = type_stats.group_by(CodeSymbol.symbol_type).all()
            
            # 平均复杂度
            avg_complexity = query.filter(
                CodeSymbol.complexity_score.isnot(None)
            ).with_entities(
                func.avg(CodeSymbol.complexity_score)
            ).scalar() or 0.0
            
            return {
                "total": total,
                "by_type": {row.symbol_type: row.count for row in type_stats},
                "avg_complexity": round(float(avg_complexity), 2)
            }
            
        except Exception as e:
            logger.error(f"获取符号统计失败: {e}")
            return {"total": 0, "by_type": {}, "avg_complexity": 0.0}
    
    def search_symbols(
        self,
        keyword: str,
        repository_id: Optional[int] = None,
        symbol_type: Optional[str] = None,
        limit: int = 20
    ) -> List[CodeSymbol]:
        """
        搜索符号
        
        Args:
            keyword: 搜索关键词
            repository_id: 仓库ID筛选
            symbol_type: 符号类型筛选
            limit: 返回数量限制
            
        Returns:
            符号列表
        """
        try:
            query = self.db.query(CodeSymbol).filter(
                CodeSymbol.is_deleted == False,
                or_(
                    CodeSymbol.symbol_name.like(f"%{keyword}%"),
                    CodeSymbol.qualified_name.like(f"%{keyword}%"),
                    CodeSymbol.docstring.like(f"%{keyword}%")
                )
            )
            
            if repository_id:
                query = query.filter(CodeSymbol.repository_id == repository_id)
            if symbol_type:
                query = query.filter(CodeSymbol.symbol_type == symbol_type)
            
            symbols = query.limit(limit).all()
            return symbols
            
        except Exception as e:
            logger.error(f"搜索符号失败: {e}")
            return []


# ============================================
# 便捷函数
# ============================================

def get_code_symbol_service(db: Session) -> CodeSymbolService:
    """获取 CodeSymbol 服务实例"""
    return CodeSymbolService(db)
