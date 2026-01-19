"""
代码导航服务
提供类似 LSP 的代码导航功能：Go to Definition, Find References, Hover Info
"""

import os
import re
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.logging import logger
from app.models.code_symbol import CodeSymbol
from app.models.code_file import CodeFile
from app.models.code_dependency import CodeDependency
from app.services.code_parser_service import CodeParserService


class CodeNavigationService:
    """代码导航服务（类似 LSP）"""
    
    def __init__(self, db: Session):
        """
        初始化代码导航服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.parser_service = CodeParserService()
    
    def get_definition(
        self,
        repository_id: int,
        file_path: str,
        line: int,
        column: int
    ) -> Optional[Dict[str, Any]]:
        """
        获取符号定义位置（Go to Definition）
        
        Args:
            repository_id: 仓库ID
            file_path: 文件路径（相对路径）
            line: 行号（1-based）
            column: 列号（0-based）
            
        Returns:
            定义位置信息，如果未找到则返回 None
            {
                "file_path": "app/services/user_service.py",
                "line": 42,
                "column": 4,
                "symbol_name": "get_user",
                "qualified_name": "app.services.user_service.get_user",
                "symbol_type": "function",
                "signature": "def get_user(user_id: int) -> User"
            }
        """
        try:
            # 1. 解析当前位置的符号
            symbol = self._parse_symbol_at_position(
                repository_id, file_path, line, column
            )
            
            if not symbol:
                logger.debug(f"未找到位置 ({line}, {column}) 的符号")
                return None
            
            # 2. 查找符号定义
            definition = self._find_symbol_definition(
                repository_id, symbol['name'], symbol.get('qualified_name')
            )
            
            if definition:
                # 获取文件路径
                def_file_path = file_path  # 使用传入的文件路径作为默认值
                if definition.file_id:
                    def_file = self.db.query(CodeFile).filter(
                        CodeFile.id == definition.file_id
                    ).first()
                    if def_file:
                        def_file_path = def_file.file_path
                
                # 检查是否就是当前位置（如果是定义本身，返回提示信息）
                def_line = definition.start_line or 0
                is_same_location = (
                    def_file_path == file_path and 
                    def_line == line
                )
                
                if is_same_location:
                    # 当前位置就是定义位置，返回提示信息
                    logger.debug(f"当前位置就是定义位置: {file_path}:{line}")
                    return {
                        "file_path": def_file_path,
                        "line": def_line,
                        "column": 0,
                        "symbol_name": definition.symbol_name,
                        "qualified_name": definition.qualified_name or definition.symbol_name,
                        "symbol_type": definition.symbol_type,
                        "signature": definition.signature or "",
                        "is_definition": True,  # 标记这是定义位置
                        "message": "当前位置就是定义位置，请使用"查找引用"查看该符号的所有引用"
                    }
                
                return {
                    "file_path": def_file_path,
                    "line": def_line,
                    "column": 0,  # 列号需要从代码中解析
                    "symbol_name": definition.symbol_name,
                    "qualified_name": definition.qualified_name or definition.symbol_name,
                    "symbol_type": definition.symbol_type,
                    "signature": definition.signature or "",
                    "is_definition": False
                }
            
            return None
            
        except Exception as e:
            logger.error(f"获取定义位置失败: {e}", exc_info=True)
            return None
    
    def get_references(
        self,
        repository_id: int,
        file_path: str,
        line: int,
        column: int,
        include_definition: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取符号的所有引用位置（Find References）
        
        Args:
            repository_id: 仓库ID
            file_path: 文件路径（相对路径）
            line: 行号（1-based）
            column: 列号（0-based）
            include_definition: 是否包含定义位置
            
        Returns:
            引用位置列表
            [
                {
                    "file_path": "app/services/user_service.py",
                    "line": 42,
                    "column": 4,
                    "context": "def get_user(...)"
                },
                ...
            ]
        """
        try:
            # 1. 解析当前位置的符号
            symbol = self._parse_symbol_at_position(
                repository_id, file_path, line, column
            )
            
            if not symbol:
                return []
            
            # 2. 查找符号定义
            definition = self._find_symbol_definition(
                repository_id, symbol['name'], symbol.get('qualified_name')
            )
            
            if not definition:
                return []
            
            # 3. 查找所有引用
            references = []
            
            # 获取定义位置和当前位置（用于排除）
            def_file_path = file_path
            def_line = 0
            if definition.file_id:
                def_file = self.db.query(CodeFile).filter(
                    CodeFile.id == definition.file_id
                ).first()
                if def_file:
                    def_file_path = def_file.file_path
                    def_line = definition.start_line or 0
            
            current_file_path = file_path
            current_line = line
            
            # 3.1 通过 CodeDependency 查找引用（调用关系）
            dependencies = self.db.query(CodeDependency).filter(
                CodeDependency.repository_id == repository_id,
                CodeDependency.target_symbol_id == definition.id,
                CodeDependency.dependency_type.in_(['call', 'reference', 'import'])
            ).all()
            
            for dep in dependencies:
                if dep.source_symbol_id:
                    source_symbol = self.db.query(CodeSymbol).filter(
                        CodeSymbol.id == dep.source_symbol_id
                    ).first()
                    
                    if source_symbol and source_symbol.file_id:
                        source_file = self.db.query(CodeFile).filter(
                            CodeFile.id == source_symbol.file_id
                        ).first()
                        
                        if source_file:
                            ref_line = dep.line_number or source_symbol.start_line or 0
                            # 排除定义位置和当前位置
                            is_definition = (source_file.file_path == def_file_path and ref_line == def_line)
                            is_current = (source_file.file_path == current_file_path and ref_line == current_line)
                            
                            if not is_definition and not is_current:
                                references.append({
                                    "file_path": source_file.file_path,
                                    "line": ref_line,
                                    "column": 0,
                                    "context": self._get_line_context(
                                        repository_id, source_file.file_path, ref_line
                                    ),
                                    "type": "call" if dep.dependency_type == 'call' else "reference"
                                })
            
            # 3.2 通过符号名搜索（排除定义和当前位置）
            similar_symbols = self.db.query(CodeSymbol).filter(
                CodeSymbol.repository_id == repository_id,
                or_(
                    CodeSymbol.symbol_name == definition.symbol_name,
                    CodeSymbol.qualified_name == definition.qualified_name
                )
            ).all()
            
            for sym in similar_symbols:
                # 跳过定义本身（除非明确要求包含）
                if sym.id == definition.id:
                    if include_definition:
                        # 添加定义位置（但排除当前位置）
                        if sym.file_id:
                            sym_file = self.db.query(CodeFile).filter(
                                CodeFile.id == sym.file_id
                            ).first()
                            
                            if sym_file:
                                sym_line = sym.start_line or 0
                                is_current = (sym_file.file_path == current_file_path and sym_line == current_line)
                                if not is_current:
                                    references.append({
                                        "file_path": sym_file.file_path,
                                        "line": sym_line,
                                        "column": 0,
                                        "context": self._get_line_context(
                                            repository_id, sym_file.file_path, sym_line
                                        ),
                                        "type": "definition"
                                    })
                    continue
                
                # 添加其他位置的引用（排除定义和当前位置）
                if sym.file_id:
                    sym_file = self.db.query(CodeFile).filter(
                        CodeFile.id == sym.file_id
                    ).first()
                    
                    if sym_file:
                        sym_line = sym.start_line or 0
                        is_definition = (sym_file.file_path == def_file_path and sym_line == def_line)
                        is_current = (sym_file.file_path == current_file_path and sym_line == current_line)
                        
                        # 检查是否是真正的引用（通过 qualified_name 匹配）
                        if (sym.qualified_name == definition.qualified_name and 
                            not is_definition and not is_current):
                            references.append({
                                "file_path": sym_file.file_path,
                                "line": sym_line,
                                "column": 0,
                                "context": self._get_line_context(
                                    repository_id, sym_file.file_path, sym_line
                                ),
                                "type": "reference"
                            })
            
            # 去重
            seen = set()
            unique_references = []
            for ref in references:
                key = (ref['file_path'], ref['line'])
                if key not in seen:
                    seen.add(key)
                    unique_references.append(ref)
            
            return unique_references
            
        except Exception as e:
            logger.error(f"获取引用位置失败: {e}", exc_info=True)
            return []
    
    def get_hover_info(
        self,
        repository_id: int,
        file_path: str,
        line: int,
        column: int
    ) -> Optional[Dict[str, Any]]:
        """
        获取悬停信息（Hover Info，类似 LSP hover）
        
        Args:
            repository_id: 仓库ID
            file_path: 文件路径（相对路径）
            line: 行号（1-based）
            column: 列号（0-based）
            
        Returns:
            悬停信息，如果未找到则返回 None
            {
                "symbol_name": "get_user",
                "qualified_name": "app.services.user_service.get_user",
                "symbol_type": "function",
                "signature": "def get_user(user_id: int) -> User",
                "docstring": "获取用户信息...",
                "file_path": "app/services/user_service.py",
                "line": 42
            }
        """
        try:
            # 1. 解析当前位置的符号
            symbol = self._parse_symbol_at_position(
                repository_id, file_path, line, column
            )
            
            if not symbol:
                return None
            
            # 2. 查找符号定义
            definition = self._find_symbol_definition(
                repository_id, symbol['name'], symbol.get('qualified_name')
            )
            
            if not definition:
                return None
            
            # 3. 获取符号详细信息
            info = {
                "symbol_name": definition.symbol_name,
                "qualified_name": definition.qualified_name or definition.symbol_name,
                "symbol_type": definition.symbol_type,
                "signature": definition.signature or "",
                "docstring": definition.docstring or "",
            }
            
            # 添加定义位置
            if definition.file_id:
                sym_file = self.db.query(CodeFile).filter(
                    CodeFile.id == definition.file_id
                ).first()
                
                if sym_file:
                    info["file_path"] = sym_file.file_path
                    info["line"] = definition.start_line or 0
            
            return info
            
        except Exception as e:
            logger.error(f"获取悬停信息失败: {e}", exc_info=True)
            return None
    
    def _parse_symbol_at_position(
        self,
        repository_id: int,
        file_path: str,
        line: int,
        column: int
    ) -> Optional[Dict[str, Any]]:
        """
        解析指定位置的符号
        
        Args:
            repository_id: 仓库ID
            file_path: 文件路径
            line: 行号（1-based）
            column: 列号（0-based）
            
        Returns:
            符号信息，如果未找到则返回 None
        """
        try:
            # 1. 查找文件
            file_obj = self.db.query(CodeFile).filter(
                CodeFile.repository_id == repository_id,
                CodeFile.file_path == file_path
            ).first()
            
            if not file_obj:
                return None
            
            # 2. 查找该位置附近的符号（通过行号范围）
            symbols = self.db.query(CodeSymbol).filter(
                CodeSymbol.repository_id == repository_id,
                CodeSymbol.file_id == file_obj.id,
                CodeSymbol.start_line <= line,
                CodeSymbol.end_line >= line
            ).order_by(
                CodeSymbol.start_line.desc()
            ).all()
            
            # 3. 选择最匹配的符号（行号最接近，且包含列号范围）
            best_symbol = None
            for symbol in symbols:
                # 如果符号有列号信息，检查是否包含当前位置
                # 否则选择行号匹配的符号
                if symbol.start_line <= line <= symbol.end_line:
                    if best_symbol is None or symbol.start_line > best_symbol.start_line:
                        best_symbol = symbol
            
            if best_symbol:
                return {
                    "name": best_symbol.symbol_name,
                    "qualified_name": best_symbol.qualified_name,
                    "type": best_symbol.symbol_type,
                    "line": best_symbol.start_line
                }
            
            # 4. 如果数据库中没有找到，尝试从文件内容解析
            # 获取仓库路径
            from app.models.code_repository import CodeRepository
            repo = self.db.query(CodeRepository).filter(
                CodeRepository.id == repository_id
            ).first()
            
            if not repo or not repo.local_path:
                return None
            
            full_path = os.path.join(repo.local_path, file_path)
            if not os.path.exists(full_path):
                return None
            
            # 读取文件内容
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            if line > len(lines):
                return None
            
            # 解析当前行的符号
            current_line = lines[line - 1]
            
            # 尝试提取标识符（简单方法：提取当前位置的单词）
            # 更精确的方法需要完整的 AST 解析
            word_pattern = r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'
            matches = list(re.finditer(word_pattern, current_line))
            
            for match in matches:
                if match.start() <= column < match.end():
                    symbol_name = match.group(0)
                    return {
                        "name": symbol_name,
                        "qualified_name": None,
                        "type": None,
                        "line": line
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"解析位置符号失败: {e}", exc_info=True)
            return None
    
    def _find_symbol_definition(
        self,
        repository_id: int,
        symbol_name: str,
        qualified_name: Optional[str] = None
    ) -> Optional[CodeSymbol]:
        """
        查找符号定义
        
        Args:
            repository_id: 仓库ID
            symbol_name: 符号名
            qualified_name: 完整限定名（可选）
            exclude_file_path: 排除的文件路径（可选，用于排除当前位置）
            exclude_line: 排除的行号（可选，用于排除当前位置）
            
        Returns:
            符号定义，如果未找到则返回 None
        """
        try:
            # 优先使用 qualified_name 精确匹配
            if qualified_name:
                query = self.db.query(CodeSymbol).filter(
                    CodeSymbol.repository_id == repository_id,
                    CodeSymbol.qualified_name == qualified_name,
                    CodeSymbol.symbol_type.in_(['function', 'class', 'method', 'variable'])
                )
                
                # 如果指定了排除位置，尝试查找其他位置的定义
                if exclude_file_path and exclude_line:
                    symbols = query.all()
                    # 优先选择不是排除位置的定义
                    for symbol in symbols:
                        if symbol.file_id:
                            sym_file = self.db.query(CodeFile).filter(
                                CodeFile.id == symbol.file_id
                            ).first()
                            if sym_file:
                                if not (sym_file.file_path == exclude_file_path and 
                                       (symbol.start_line or 0) == exclude_line):
                                    return symbol
                    # 如果所有匹配都是排除位置，返回第一个（可能是定义本身）
                    if symbols:
                        return symbols[0]
                else:
                    symbol = query.first()
                    if symbol:
                        return symbol
            
            # 使用 symbol_name 匹配
            symbols = self.db.query(CodeSymbol).filter(
                CodeSymbol.repository_id == repository_id,
                CodeSymbol.symbol_name == symbol_name,
                CodeSymbol.symbol_type.in_(['function', 'class', 'method', 'variable'])
            ).all()
            
            # 如果有多个匹配，优先选择函数和类，并排除当前位置
            if symbols:
                # 按类型优先级排序
                type_priority = {'function': 1, 'class': 2, 'method': 3, 'variable': 4}
                symbols.sort(key=lambda s: type_priority.get(s.symbol_type, 99))
                
                # 如果指定了排除位置，优先选择其他位置
                if exclude_file_path and exclude_line:
                    for symbol in symbols:
                        if symbol.file_id:
                            sym_file = self.db.query(CodeFile).filter(
                                CodeFile.id == symbol.file_id
                            ).first()
                            if sym_file:
                                if not (sym_file.file_path == exclude_file_path and 
                                       (symbol.start_line or 0) == exclude_line):
                                    return symbol
                
                # 返回第一个（可能是定义本身）
                return symbols[0]
            
            return None
            
        except Exception as e:
            logger.error(f"查找符号定义失败: {e}", exc_info=True)
            return None
    
    def _get_line_context(
        self,
        repository_id: int,
        file_path: str,
        line: int,
        context_lines: int = 2
    ) -> str:
        """
        获取行的上下文代码
        
        Args:
            repository_id: 仓库ID
            file_path: 文件路径
            line: 行号（1-based）
            context_lines: 上下文行数
            
        Returns:
            上下文代码（单行或几行）
        """
        try:
            # 获取仓库路径
            from app.models.code_repository import CodeRepository
            repo = self.db.query(CodeRepository).filter(
                CodeRepository.id == repository_id
            ).first()
            
            if not repo or not repo.local_path:
                return ""
            
            full_path = os.path.join(repo.local_path, file_path)
            if not os.path.exists(full_path):
                return ""
            
            # 读取文件内容
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            if line > len(lines):
                return ""
            
            # 提取上下文
            start = max(0, line - 1 - context_lines)
            end = min(len(lines), line + context_lines)
            context = ''.join(lines[start:end])
            
            return context.strip()
            
        except Exception as e:
            logger.debug(f"获取行上下文失败: {e}")
            return ""
