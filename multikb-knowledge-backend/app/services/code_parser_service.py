"""
代码解析服务
使用 Tree-sitter 解析多种语言的代码结构
"""

import os
import threading
import warnings
from typing import Dict, List, Optional, Any
from pathlib import Path

from tree_sitter import Language, Parser, Node

from app.core.logging import logger

# 抑制 tree-sitter 的 FutureWarning
warnings.filterwarnings("ignore", category=FutureWarning, module="tree_sitter")

# 尝试导入语言库
try:
    from tree_sitter_languages import get_language, get_parser
    LANGUAGES_AVAILABLE = True
except ImportError:
    logger.warning("tree_sitter_languages 未安装，代码解析功能将不可用")
    LANGUAGES_AVAILABLE = False


class CodeParserService:
    """代码解析服务（使用 Tree-sitter，单例模式）"""
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    # 支持的语言
    SUPPORTED_LANGUAGES = {
        'python': ['.py'],
        'javascript': ['.js', '.jsx', '.mjs'],
        'typescript': ['.ts', '.tsx']
    }
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(CodeParserService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化解析器（仅执行一次）"""
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            
            self.parsers = {}
            self._init_parsers()
            logger.info(f"代码解析服务初始化完成，支持语言: {list(self.parsers.keys())}")
            self._initialized = True
    
    def _init_parsers(self):
        """初始化 Tree-sitter 解析器"""
        if not LANGUAGES_AVAILABLE:
            logger.error("tree-sitter-languages 未安装，请运行: pip install tree-sitter-languages")
            return
        
        # 只在第一次初始化时记录日志
        if not hasattr(CodeParserService, '_languages_loaded'):
            logger.info("tree-sitter-languages 已加载")
            CodeParserService._languages_loaded = True
        
        try:
            # Python 解析器
            try:
                self.parsers['python'] = get_parser('python')
                logger.info("✓ Python 解析器初始化成功")
            except Exception as e:
                logger.warning(f"Python 解析器初始化失败: {e}")
            
            # JavaScript 解析器
            try:
                self.parsers['javascript'] = get_parser('javascript')
                logger.info("✓ JavaScript 解析器初始化成功")
            except Exception as e:
                logger.warning(f"JavaScript 解析器初始化失败: {e}")
            
            # TypeScript 解析器
            try:
                self.parsers['typescript'] = get_parser('typescript')
                logger.info("✓ TypeScript 解析器初始化成功")
            except Exception as e:
                logger.warning(f"TypeScript 解析器初始化失败: {e}")
            
            if not self.parsers:
                logger.error("没有可用的解析器，请安装语言库: pip install tree-sitter-languages")
            
        except Exception as e:
            logger.error(f"初始化 Tree-sitter 解析器失败: {e}")
            raise
    
    def detect_language(self, file_path: str) -> Optional[str]:
        """
        根据文件扩展名检测语言
        
        Args:
            file_path: 文件路径
            
        Returns:
            语言名称，如果不支持则返回 None
        """
        ext = Path(file_path).suffix.lower()
        
        for lang, extensions in self.SUPPORTED_LANGUAGES.items():
            if ext in extensions:
                return lang
        
        return None
    
    def parse_file(self, file_path: str, language: Optional[str] = None) -> Optional[Dict]:
        """
        解析代码文件
        
        Args:
            file_path: 文件路径
            language: 语言类型，如果不提供则自动检测
            
        Returns:
            解析结果字典，包含：
            - file_path: 文件路径
            - language: 语言类型
            - symbols: 符号列表（函数、类等）
            - imports: 导入语句
            - complexity: 复杂度信息
            - lines: 代码行数
        """
        # 自动检测语言
        if language is None:
            language = self.detect_language(file_path)
        
        if language is None or language not in self.parsers:
            logger.warning(f"不支持的语言或文件: {file_path}")
            return None
        
        try:
            # 读取文件内容
            with open(file_path, 'rb') as f:
                code = f.read()
            
            # 解析代码
            parser = self.parsers[language]
            tree = parser.parse(code)
            
            # 提取信息
            symbols = self._extract_symbols(tree.root_node, code, language)
            imports = self._extract_imports(tree.root_node, code, language)
            complexity = self._calculate_complexity(tree.root_node)
            
            # 提取关系信息（调用关系、继承关系）
            call_relationships = self.extract_call_relationships(file_path, language)
            inheritance_relationships = self.extract_inheritance_relationships(file_path, language)
            
            # 统计代码行数
            lines = code.decode('utf-8', errors='ignore').count('\n') + 1
            
            return {
                'file_path': file_path,
                'language': language,
                'symbols': symbols,
                'imports': imports,
                'complexity': complexity,
                'lines': lines,
                'call_relationships': call_relationships,
                'inheritance_relationships': inheritance_relationships
            }
            
        except Exception as e:
            logger.error(f"解析文件失败 {file_path}: {e}")
            return None
    
    def parse_code(self, code_content: str, language: str) -> Optional[Dict]:
        """
        解析代码内容（不依赖文件路径）
        
        Args:
            code_content: 代码内容字符串
            language: 语言类型（python/javascript/typescript）
            
        Returns:
            解析结果字典，包含 symbols, imports, complexity, lines 等
        """
        if language not in self.parsers:
            logger.warning(f"不支持的语言: {language}")
            return None
        
        try:
            # 转换为字节
            code = code_content.encode('utf-8')
            
            # 解析代码
            parser = self.parsers[language]
            tree = parser.parse(code)
            
            # 提取信息
            symbols = self._extract_symbols(tree.root_node, code, language)
            imports = self._extract_imports(tree.root_node, code, language)
            complexity = self._calculate_complexity(tree.root_node)
            
            # 统计代码行数
            lines = code_content.count('\n') + 1
            
            # 组织返回结果（兼容 code_symbol_service 的期望格式）
            result = {
                'symbols': symbols,
                'imports': imports,
                'complexity': complexity,
                'lines': lines
            }
            
            # 将 symbols 按类型分组（兼容 code_symbol_service）
            functions = [s for s in symbols if s.get('type') == 'function']
            classes = [s for s in symbols if s.get('type') == 'class']
            
            result['functions'] = functions
            result['classes'] = classes
            
            return result
            
        except Exception as e:
            logger.error(f"解析代码失败: {e}")
            return None
    
    def _extract_symbols(self, node: Node, code: bytes, language: str) -> List[Dict]:
        """
        提取代码符号（函数、类、方法等）
        
        Args:
            node: AST 根节点
            code: 源代码
            language: 语言类型
            
        Returns:
            符号列表
        """
        symbols = []
        
        if language == 'python':
            symbols.extend(self._extract_python_symbols(node, code))
        elif language in ['javascript', 'typescript']:
            symbols.extend(self._extract_js_symbols(node, code))
        
        return symbols
    
    def _extract_python_symbols(self, node: Node, code: bytes) -> List[Dict]:
        """提取 Python 符号（增强版：包含类型信息、注释、方法列表）"""
        symbols = []
        code_str = code.decode('utf-8', errors='ignore')
        
        # 使用 Python AST 解析以获取更准确的类型信息
        try:
            import ast as py_ast
            ast_tree = py_ast.parse(code_str)
            ast_symbols = self._extract_python_symbols_from_ast(ast_tree, code_str)
            # 合并 Tree-sitter 的位置信息和 AST 的类型信息
            tree_sitter_symbols = self._extract_python_symbols_from_tree_sitter(node, code)
            symbols = self._merge_python_symbols(tree_sitter_symbols, ast_symbols)
        except Exception as e:
            logger.warning(f"使用 AST 解析失败，回退到 Tree-sitter: {e}")
            symbols = self._extract_python_symbols_from_tree_sitter(node, code)
        
        return symbols
    
    def _extract_python_symbols_from_tree_sitter(self, node: Node, code: bytes) -> List[Dict]:
        """使用 Tree-sitter 提取 Python 符号（基础信息）"""
        symbols = []
        
        def traverse(node: Node):
            # 函数定义
            if node.type == 'function_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                    
                    # 提取参数
                    params = self._extract_python_parameters(node, code)
                    
                    # 提取文档字符串
                    docstring = self._extract_python_docstring(node, code)
                    
                    symbols.append({
                        'type': 'function',
                        'name': name,
                        'line': node.start_point[0] + 1,
                        'end_line': node.end_point[0] + 1,
                        'parameters': params,
                        'docstring': docstring
                    })
            
            # 类定义
            elif node.type == 'class_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                    
                    # 提取基类
                    bases = self._extract_python_bases(node, code)
                    
                    # 提取文档字符串
                    docstring = self._extract_python_docstring(node, code)
                    
                    symbols.append({
                        'type': 'class',
                        'name': name,
                        'line': node.start_point[0] + 1,
                        'end_line': node.end_point[0] + 1,
                        'bases': bases,
                        'docstring': docstring
                    })
            
            # 递归遍历子节点
            for child in node.children:
                traverse(child)
        
        traverse(node)
        return symbols
    
    def _extract_python_symbols_from_ast(self, ast_tree: 'ast.AST', code_str: str) -> Dict[str, Dict]:
        """使用 Python AST 提取符号的详细类型信息"""
        import ast as py_ast
        ast_symbols = {}
        
        class SymbolVisitor(py_ast.NodeVisitor):
            def __init__(self, code_str):
                self.code_str = code_str
                self.symbols = {}
            
            def visit_FunctionDef(self, node):
                # 提取参数类型和返回值类型
                params = []
                for arg in node.args.args:
                    param_info = {
                        'name': arg.arg,
                        'type': self._extract_type_annotation(arg.annotation) if arg.annotation else None
                    }
                    params.append(param_info)
                
                return_type = self._extract_type_annotation(node.returns) if node.returns else None
                
                # 提取注释（行内注释）
                comments = self._extract_comments_for_node(node, self.code_str)
                
                self.symbols[f"function:{node.name}:{node.lineno}"] = {
                    'type': 'function',
                    'name': node.name,
                    'line': node.lineno,
                    'parameters': params,
                    'return_type': return_type,
                    'comments': comments
                }
                self.generic_visit(node)
            
            def visit_AsyncFunctionDef(self, node):
                # 异步函数处理同普通函数
                self.visit_FunctionDef(node)
            
            def visit_ClassDef(self, node):
                # 提取基类（包括完整继承链）
                bases = []
                for base in node.bases:
                    base_name = self._extract_type_annotation(base)
                    if base_name:
                        bases.append(base_name)
                
                # 提取类的方法列表
                methods = []
                for item in node.body:
                    if isinstance(item, (py_ast.FunctionDef, py_ast.AsyncFunctionDef)):
                        methods.append({
                            'name': item.name,
                            'line': item.lineno,
                            'is_async': isinstance(item, py_ast.AsyncFunctionDef)
                        })
                
                # 提取注释
                comments = self._extract_comments_for_node(node, self.code_str)
                
                self.symbols[f"class:{node.name}:{node.lineno}"] = {
                    'type': 'class',
                    'name': node.name,
                    'line': node.lineno,
                    'bases': bases,
                    'methods': methods,
                    'comments': comments
                }
                self.generic_visit(node)
            
            def _extract_type_annotation(self, annotation_node):
                """提取类型注解字符串"""
                if annotation_node is None:
                    return None
                
                try:
                    if isinstance(annotation_node, py_ast.Name):
                        return annotation_node.id
                    elif isinstance(annotation_node, py_ast.Attribute):
                        # 处理 typing.List, typing.Dict 等
                        if isinstance(annotation_node.value, py_ast.Name):
                            return f"{annotation_node.value.id}.{annotation_node.attr}"
                    elif isinstance(annotation_node, py_ast.Subscript):
                        # 处理 List[str], Dict[str, int] 等
                        if isinstance(annotation_node.value, py_ast.Name):
                            base = annotation_node.value.id
                            # 简化处理，只返回基础类型
                            return base
                    elif isinstance(annotation_node, py_ast.Constant):
                        return str(annotation_node.value)
                    
                    # 通用处理：使用 ast.unparse（Python 3.9+）
                    try:
                        import ast
                        return ast.unparse(annotation_node)
                    except (AttributeError, ImportError):
                        # Python < 3.9，使用 astor 或简单字符串化
                        return str(annotation_node)
                except Exception:
                    return None
            
            def _extract_comments_for_node(self, node, code_str):
                """提取节点的注释（行内注释和块注释）"""
                comments = []
                lines = code_str.split('\n')
                
                # 提取节点之前的注释（块注释）
                node_start_line = node.lineno - 1  # 转换为 0-based
                if node_start_line > 0:
                    # 向上查找连续注释
                    for i in range(node_start_line - 1, max(-1, node_start_line - 10), -1):
                        line = lines[i].strip()
                        if line.startswith('#'):
                            comments.insert(0, line[1:].strip())
                        elif line == '':
                            continue
                        else:
                            break
                
                # 提取行内注释（在同一行）
                node_line = lines[node_start_line] if node_start_line < len(lines) else ''
                if '#' in node_line:
                    comment_part = node_line.split('#', 1)[1].strip()
                    if comment_part:
                        comments.append(comment_part)
                
                return comments
        
        visitor = SymbolVisitor(code_str)
        visitor.visit(ast_tree)
        return visitor.symbols
    
    def _merge_python_symbols(self, tree_sitter_symbols: List[Dict], ast_symbols: Dict[str, Dict]) -> List[Dict]:
        """合并 Tree-sitter 和 AST 的符号信息"""
        merged = []
        
        for ts_symbol in tree_sitter_symbols:
            symbol_key = f"{ts_symbol['type']}:{ts_symbol['name']}:{ts_symbol['line']}"
            
            # 查找匹配的 AST 符号
            matched_ast = None
            for key, ast_symbol in ast_symbols.items():
                if (ast_symbol['type'] == ts_symbol['type'] and 
                    ast_symbol['name'] == ts_symbol['name'] and
                    abs(ast_symbol['line'] - ts_symbol['line']) <= 2):  # 允许 2 行误差
                    matched_ast = ast_symbol
                    break
            
            # 合并信息
            merged_symbol = ts_symbol.copy()
            if matched_ast:
                # 合并参数类型信息
                if 'parameters' in matched_ast and isinstance(matched_ast['parameters'], list):
                    # 更新参数，添加类型信息
                    for i, param in enumerate(matched_ast['parameters']):
                        if isinstance(param, dict) and 'type' in param:
                            if i < len(merged_symbol.get('parameters', [])):
                                if isinstance(merged_symbol['parameters'][i], str):
                                    # 转换为字典格式
                                    merged_symbol['parameters'][i] = {
                                        'name': merged_symbol['parameters'][i],
                                        'type': param['type']
                                    }
                                elif isinstance(merged_symbol['parameters'][i], dict):
                                    merged_symbol['parameters'][i]['type'] = param['type']
                
                # 添加返回值类型
                if 'return_type' in matched_ast:
                    merged_symbol['return_type'] = matched_ast['return_type']
                
                # 添加注释
                if 'comments' in matched_ast:
                    merged_symbol['comments'] = matched_ast['comments']
                
                # 添加方法列表（类）
                if merged_symbol['type'] == 'class' and 'methods' in matched_ast:
                    merged_symbol['methods'] = matched_ast['methods']
                
                # 更新基类信息（如果 AST 中有更完整的信息）
                if merged_symbol['type'] == 'class' and 'bases' in matched_ast:
                    merged_symbol['bases'] = matched_ast['bases']
            
            merged.append(merged_symbol)
        
        return merged
    
    def _extract_js_symbols(self, node: Node, code: bytes) -> List[Dict]:
        """提取 JavaScript/TypeScript 符号（增强版：包含类型信息、注释）"""
        symbols = []
        code_str = code.decode('utf-8', errors='ignore')
        
        def traverse(node: Node, parent: Node = None):
            # 函数声明
            if node.type in ['function_declaration', 'function']:
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                    
                    # 提取参数（包含类型信息，如果是 TypeScript）
                    params = self._extract_js_parameters(node, code)
                    
                    # 提取返回值类型（TypeScript）
                    return_type = self._extract_js_return_type(node, code)
                    
                    # 提取 JSDoc 注释
                    docstring = self._extract_jsdoc(node, code, parent)
                    
                    # 从 JSDoc 中提取类型信息（如果 AST 中没有）
                    if docstring and not return_type:
                        return_type = self._extract_return_type_from_jsdoc(docstring)
                    
                    # 提取注释
                    comments = self._extract_js_comments(node, code_str)
                    
                    symbols.append({
                        'type': 'function',
                        'name': name,
                        'line': node.start_point[0] + 1,
                        'end_line': node.end_point[0] + 1,
                        'parameters': params,
                        'return_type': return_type,
                        'docstring': docstring,
                        'comments': comments
                    })
            
            # 箭头函数（变量声明）
            elif node.type == 'variable_declarator':
                name_node = node.child_by_field_name('name')
                value_node = node.child_by_field_name('value')
                
                if name_node and value_node and value_node.type == 'arrow_function':
                    name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                    
                    # 提取参数
                    params = self._extract_js_parameters(value_node, code)
                    
                    # 提取返回值类型
                    return_type = self._extract_js_return_type(value_node, code)
                    
                    # 提取 JSDoc 注释
                    docstring = self._extract_jsdoc(node, code, parent)
                    
                    # 提取注释
                    comments = self._extract_js_comments(node, code_str)
                    
                    symbols.append({
                        'type': 'function',
                        'name': name,
                        'line': node.start_point[0] + 1,
                        'end_line': node.end_point[0] + 1,
                        'parameters': params,
                        'return_type': return_type,
                        'docstring': docstring,
                        'comments': comments
                    })
            
            # 类声明
            elif node.type == 'class_declaration':
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                    
                    # 提取基类（继承关系）
                    bases = self._extract_js_bases(node, code)
                    
                    # 提取类的方法列表
                    methods = self._extract_js_class_methods(node, code)
                    
                    # 提取 JSDoc 注释
                    docstring = self._extract_jsdoc(node, code, parent)
                    
                    # 提取注释
                    comments = self._extract_js_comments(node, code_str)
                    
                    symbols.append({
                        'type': 'class',
                        'name': name,
                        'line': node.start_point[0] + 1,
                        'end_line': node.end_point[0] + 1,
                        'bases': bases,
                        'methods': methods,
                        'docstring': docstring,
                        'comments': comments
                    })
            
            # 递归遍历
            for child in node.children:
                traverse(child, node)
        
        traverse(node)
        return symbols
    
    def _extract_js_parameters(self, func_node: Node, code: bytes) -> List[Dict]:
        """提取 JavaScript/TypeScript 函数参数（包含类型信息）"""
        params = []
        params_node = func_node.child_by_field_name('parameters')
        
        if params_node:
            for child in params_node.children:
                if child.type == 'identifier':
                    param_name = code[child.start_byte:child.end_byte].decode('utf-8')
                    params.append({
                        'name': param_name,
                        'type': None
                    })
                elif child.type == 'required_parameter':
                    # TypeScript 参数
                    name_node = child.child_by_field_name('pattern')
                    type_node = child.child_by_field_name('type')
                    if name_node:
                        param_name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                        param_type = None
                        if type_node:
                            param_type = code[type_node.start_byte:type_node.end_byte].decode('utf-8')
                        params.append({
                            'name': param_name,
                            'type': param_type
                        })
        
        return params
    
    def _extract_js_return_type(self, func_node: Node, code: bytes) -> Optional[str]:
        """提取 TypeScript 函数返回值类型"""
        return_type_node = func_node.child_by_field_name('return_type')
        if return_type_node:
            return code[return_type_node.start_byte:return_type_node.end_byte].decode('utf-8')
        return None
    
    def _extract_js_bases(self, class_node: Node, code: bytes) -> List[str]:
        """提取 JavaScript/TypeScript 类的基类"""
        bases = []
        superclass_node = class_node.child_by_field_name('superclass')
        
        if superclass_node:
            if superclass_node.type == 'identifier':
                base = code[superclass_node.start_byte:superclass_node.end_byte].decode('utf-8')
                bases.append(base)
            elif superclass_node.type == 'member_expression':
                # 处理 extends SomeClass 的情况
                base = code[superclass_node.start_byte:superclass_node.end_byte].decode('utf-8')
                bases.append(base)
        
        return bases
    
    def _extract_js_class_methods(self, class_node: Node, code: bytes) -> List[Dict]:
        """提取类的方法列表"""
        methods = []
        body_node = class_node.child_by_field_name('body')
        
        if body_node:
            for child in body_node.children:
                if child.type in ['method_definition', 'public_field_definition']:
                    name_node = child.child_by_field_name('name')
                    if name_node:
                        method_name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                        methods.append({
                            'name': method_name,
                            'line': child.start_point[0] + 1,
                            'is_async': False  # 可以进一步检测
                        })
        
        return methods
    
    def _extract_js_comments(self, node: Node, code_str: str) -> List[str]:
        """提取 JavaScript/TypeScript 注释"""
        comments = []
        lines = code_str.split('\n')
        node_start_line = node.start_point[0]
        
        # 提取节点之前的注释
        if node_start_line > 0:
            for i in range(node_start_line - 1, max(-1, node_start_line - 10), -1):
                line = lines[i].strip()
                if line.startswith('//') or line.startswith('/*'):
                    if line.startswith('//'):
                        comments.insert(0, line[2:].strip())
                    elif line.startswith('/*'):
                        # 块注释
                        comment_text = line[2:].rstrip('*/').strip()
                        comments.insert(0, comment_text)
                elif line == '':
                    continue
                else:
                    break
        
        return comments
    
    def _extract_return_type_from_jsdoc(self, jsdoc: str) -> Optional[str]:
        """从 JSDoc 中提取返回值类型"""
        import re
        # 匹配 @returns {Type} 或 @return {Type}
        match = re.search(r'@(?:returns?|return)\s*\{([^}]+)\}', jsdoc)
        if match:
            return match.group(1)
        return None
    
    def _extract_python_parameters(self, func_node: Node, code: bytes) -> List[Dict]:
        """提取 Python 函数参数（包含类型信息）"""
        params = []
        params_node = func_node.child_by_field_name('parameters')
        
        if params_node:
            for child in params_node.children:
                if child.type == 'identifier':
                    param_name = code[child.start_byte:child.end_byte].decode('utf-8')
                    # 检查是否有类型注解
                    param_type = None
                    # 在 Tree-sitter 中，类型注解可能在参数节点中
                    # 这里先返回基础信息，类型信息会在 AST 解析中补充
                    params.append({
                        'name': param_name,
                        'type': param_type
                    })
                elif child.type == 'typed_parameter':
                    # 处理带类型注解的参数
                    name_node = child.child_by_field_name('name')
                    type_node = child.child_by_field_name('type')
                    if name_node:
                        param_name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                        param_type = None
                        if type_node:
                            param_type = code[type_node.start_byte:type_node.end_byte].decode('utf-8')
                        params.append({
                            'name': param_name,
                            'type': param_type
                        })
        
        return params
    
    def _extract_python_bases(self, class_node: Node, code: bytes) -> List[str]:
        """提取 Python 类的基类"""
        bases = []
        superclasses_node = class_node.child_by_field_name('superclasses')
        
        if superclasses_node:
            for child in superclasses_node.children:
                if child.type == 'identifier':
                    base = code[child.start_byte:child.end_byte].decode('utf-8')
                    bases.append(base)
        
        return bases
    
    def _extract_python_docstring(self, node: Node, code: bytes) -> Optional[str]:
        """提取 Python 文档字符串"""
        body = node.child_by_field_name('body')
        if body and len(body.children) > 0:
            first_stmt = body.children[0]
            if first_stmt.type == 'expression_statement':
                string_node = first_stmt.children[0]
                if string_node.type == 'string':
                    docstring = code[string_node.start_byte:string_node.end_byte].decode('utf-8')
                    # 去掉引号
                    return docstring.strip('"""').strip("'''").strip()
        
        return None
    
    def _extract_jsdoc(self, node: Node, code: bytes, parent: Node = None) -> Optional[str]:
        """
        提取 JSDoc 注释（JavaScript/TypeScript 文档字符串）
        
        JSDoc 格式：
        /**
         * 这是函数的说明
         * @param {string} name 参数说明
         * @returns {number} 返回值说明
         */
        """
        try:
            # 方法 1: 查找节点之前的注释
            # 在 Tree-sitter 中，注释通常在符号定义之前
            if parent:
                # 查找父节点中在当前节点之前的注释
                node_start_line = node.start_point[0]
                node_start_byte = node.start_byte
                
                # 遍历父节点的所有子节点，找到当前节点之前的注释
                for i, sibling in enumerate(parent.children):
                    if sibling == node and i > 0:
                        # 检查前一个兄弟节点是否是注释
                        prev_sibling = parent.children[i - 1]
                        if prev_sibling.type in ['comment', 'line_comment', 'block_comment']:
                            comment_text = code[prev_sibling.start_byte:prev_sibling.end_byte].decode('utf-8')
                            # 检查是否是 JSDoc 格式（/** ... */）
                            if comment_text.strip().startswith('/**'):
                                # 提取 JSDoc 内容
                                lines = comment_text.split('\n')
                                doc_lines = []
                                for line in lines:
                                    # 移除 JSDoc 标记和星号
                                    line = line.strip()
                                    if line.startswith('/**'):
                                        line = line[3:].strip()
                                    elif line.startswith('*/'):
                                        line = line[:-2].strip()
                                    elif line.startswith('*'):
                                        line = line[1:].strip()
                                    
                                    if line:
                                        doc_lines.append(line)
                                
                                if doc_lines:
                                    return '\n'.join(doc_lines)
            
            # 方法 2: 在当前节点的直接子节点中查找注释
            # 某些情况下，注释可能是节点的第一个子节点
            if node.children:
                first_child = node.children[0]
                if first_child.type in ['comment', 'line_comment', 'block_comment']:
                    comment_text = code[first_child.start_byte:first_child.end_byte].decode('utf-8')
                    if comment_text.strip().startswith('/**'):
                        lines = comment_text.split('\n')
                        doc_lines = []
                        for line in lines:
                            line = line.strip()
                            if line.startswith('/**'):
                                line = line[3:].strip()
                            elif line.startswith('*/'):
                                line = line[:-2].strip()
                            elif line.startswith('*'):
                                line = line[1:].strip()
                            
                            if line:
                                doc_lines.append(line)
                        
                        if doc_lines:
                            return '\n'.join(doc_lines)
            
            # 方法 3: 在代码中向前查找（作为后备方案）
            # 查找节点开始位置之前的最近的多行注释
            node_start_byte = node.start_byte
            node_start_line = node.start_point[0]
            
            # 从节点开始位置向前查找（最多查找前 10 行）
            search_start = max(0, node_start_byte - 2000)  # 最多向前查找 2000 字节
            search_text = code[search_start:node_start_byte].decode('utf-8', errors='ignore')
            
            # 使用正则表达式查找 JSDoc 注释
            import re
            # 匹配 /** ... */ 格式的注释
            jsdoc_pattern = r'/\*\*([^*]|(?:\*(?!/)))*\*/'
            matches = list(re.finditer(jsdoc_pattern, search_text, re.DOTALL))
            
            if matches:
                # 取最后一个匹配（最接近符号定义的）
                last_match = matches[-1]
                comment_text = last_match.group(0)
                
                # 提取内容
                lines = comment_text.split('\n')
                doc_lines = []
                for line in lines:
                    line = line.strip()
                    if line.startswith('/**'):
                        line = line[3:].strip()
                    elif line.startswith('*/'):
                        line = line[:-2].strip()
                    elif line.startswith('*'):
                        line = line[1:].strip()
                    
                    if line:
                        doc_lines.append(line)
                
                if doc_lines:
                    return '\n'.join(doc_lines)
        
        except Exception as e:
            # 如果提取失败，返回 None（不影响主流程）
            pass
        
        return None
    
    def _extract_imports(self, node: Node, code: bytes, language: str) -> List[Dict]:
        """
        提取导入语句
        
        Args:
            node: AST 根节点
            code: 源代码
            language: 语言类型
            
        Returns:
            导入列表
        """
        imports = []
        
        if language == 'python':
            imports.extend(self._extract_python_imports(node, code))
        elif language in ['javascript', 'typescript']:
            imports.extend(self._extract_js_imports(node, code))
        
        return imports
    
    def _extract_python_imports(self, node: Node, code: bytes) -> List[Dict]:
        """提取 Python 导入语句"""
        imports = []
        
        def traverse(node: Node):
            # import xxx
            if node.type == 'import_statement':
                for child in node.children:
                    if child.type == 'dotted_name':
                        module = code[child.start_byte:child.end_byte].decode('utf-8')
                        imports.append({
                            'type': 'import',
                            'module': module,
                            'line': node.start_point[0] + 1
                        })
            
            # from xxx import yyy
            elif node.type == 'import_from_statement':
                module_node = node.child_by_field_name('module_name')
                if module_node:
                    module = code[module_node.start_byte:module_node.end_byte].decode('utf-8')
                    imports.append({
                        'type': 'from_import',
                        'module': module,
                        'line': node.start_point[0] + 1
                    })
            
            # 递归
            for child in node.children:
                traverse(child)
        
        traverse(node)
        return imports
    
    def _extract_js_imports(self, node: Node, code: bytes) -> List[Dict]:
        """提取 JavaScript 导入语句"""
        imports = []
        
        def traverse(node: Node):
            # import xxx from 'xxx'
            if node.type == 'import_statement':
                source_node = node.child_by_field_name('source')
                if source_node:
                    module = code[source_node.start_byte:source_node.end_byte].decode('utf-8')
                    # 去掉引号
                    module = module.strip('"').strip("'")
                    imports.append({
                        'type': 'import',
                        'module': module,
                        'line': node.start_point[0] + 1
                    })
            
            # require('xxx')
            elif node.type == 'call_expression':
                func_node = node.child_by_field_name('function')
                if func_node and code[func_node.start_byte:func_node.end_byte].decode('utf-8') == 'require':
                    args = node.child_by_field_name('arguments')
                    if args and len(args.children) > 0:
                        for child in args.children:
                            if child.type == 'string':
                                module = code[child.start_byte:child.end_byte].decode('utf-8')
                                module = module.strip('"').strip("'")
                                imports.append({
                                    'type': 'require',
                                    'module': module,
                                    'line': node.start_point[0] + 1
                                })
            
            # 递归
            for child in node.children:
                traverse(child)
        
        traverse(node)
        return imports
    
    def _calculate_complexity(self, node: Node) -> Dict[str, int]:
        """
        计算代码复杂度（简化版循环复杂度）
        
        Args:
            node: AST 根节点
            
        Returns:
            复杂度信息
        """
        complexity_nodes = [
            'if_statement', 'while_statement', 'for_statement',
            'except_clause', 'with_statement', 'match_statement',
            'conditional_expression', 'boolean_operator'
        ]
        
        count = 0
        
        def traverse(node: Node):
            nonlocal count
            if node.type in complexity_nodes:
                count += 1
            
            for child in node.children:
                traverse(child)
        
        traverse(node)
        
        return {
            'cyclomatic': count + 1,  # 基础复杂度为 1
            'branches': count
        }
    
    def is_code_file(self, file_path: str) -> bool:
        """
        判断是否为代码文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否为代码文件
        """
        return self.detect_language(file_path) is not None
    
    def extract_call_relationships(self, file_path: str, language: Optional[str] = None) -> List[Dict]:
        """
        提取函数调用关系
        
        Args:
            file_path: 文件路径
            language: 语言类型，如果不提供则自动检测
            
        Returns:
            调用关系列表，格式: [{'caller': str, 'callee': str, 'line': int, 'file_path': str}]
        """
        if language is None:
            language = self.detect_language(file_path)
        
        if language is None or language not in self.parsers:
            return []
        
        try:
            with open(file_path, 'rb') as f:
                code = f.read()
            
            parser = self.parsers[language]
            tree = parser.parse(code)
            code_str = code.decode('utf-8', errors='ignore')
            
            if language == 'python':
                return self._extract_python_call_relationships(tree.root_node, code_str, file_path)
            elif language in ['javascript', 'typescript']:
                return self._extract_js_call_relationships(tree.root_node, code_str, file_path)
            
            return []
        except Exception as e:
            logger.error(f"提取调用关系失败 {file_path}: {e}")
            return []
    
    def _extract_python_call_relationships(self, node: Node, code_str: str, file_path: str) -> List[Dict]:
        """提取 Python 函数调用关系（使用 AST）"""
        try:
            import ast as py_ast
            ast_tree = py_ast.parse(code_str)
            relationships = []
            
            class CallVisitor(py_ast.NodeVisitor):
                def __init__(self, code_str, file_path):
                    self.code_str = code_str
                    self.file_path = file_path
                    self.current_function = None
                    self.relationships = []
                
                def visit_FunctionDef(self, node):
                    old_function = self.current_function
                    self.current_function = node.name
                    self.generic_visit(node)
                    self.current_function = old_function
                
                def visit_AsyncFunctionDef(self, node):
                    self.visit_FunctionDef(node)
                
                def visit_Call(self, node):
                    if self.current_function:
                        # 提取被调用的函数名
                        callee_name = None
                        if isinstance(node.func, py_ast.Name):
                            callee_name = node.func.id
                        elif isinstance(node.func, py_ast.Attribute):
                            # 处理 obj.method() 的情况
                            if isinstance(node.func.value, py_ast.Name):
                                callee_name = f"{node.func.value.id}.{node.func.attr}"
                            else:
                                callee_name = node.func.attr
                        
                        if callee_name:
                            self.relationships.append({
                                'caller': self.current_function,
                                'callee': callee_name,
                                'line': node.lineno,
                                'file_path': self.file_path,
                                'relationship_type': 'calls'
                            })
                    self.generic_visit(node)
            
            visitor = CallVisitor(code_str, file_path)
            visitor.visit(ast_tree)
            return visitor.relationships
        except Exception as e:
            logger.warning(f"使用 AST 提取调用关系失败: {e}")
            return []
    
    def _extract_js_call_relationships(self, node: Node, code_str: str, file_path: str) -> List[Dict]:
        """提取 JavaScript/TypeScript 函数调用关系"""
        relationships = []
        code_bytes = code_str.encode('utf-8')
        
        def traverse(node: Node, current_function: Optional[str] = None):
            # 函数定义
            if node.type in ['function_declaration', 'function', 'arrow_function']:
                name_node = node.child_by_field_name('name')
                func_name = None
                if name_node:
                    func_name = code_bytes[name_node.start_byte:name_node.end_byte].decode('utf-8')
                elif node.type == 'arrow_function':
                    # 箭头函数可能没有名称，使用行号
                    func_name = f"_anonymous_{node.start_point[0]}"
                
                # 在函数体内查找调用
                body = node.child_by_field_name('body')
                if body:
                    for child in body.children:
                        traverse(child, func_name)
            
            # 调用表达式
            elif node.type == 'call_expression':
                if current_function:
                    func_node = node.child_by_field_name('function')
                    if func_node:
                        callee_name = None
                        if func_node.type == 'identifier':
                            callee_name = code_bytes[func_node.start_byte:func_node.end_byte].decode('utf-8')
                        elif func_node.type == 'member_expression':
                            # 处理 obj.method() 的情况
                            property_node = func_node.child_by_field_name('property')
                            if property_node:
                                callee_name = code_bytes[property_node.start_byte:property_node.end_byte].decode('utf-8')
                        
                        if callee_name:
                            relationships.append({
                                'caller': current_function,
                                'callee': callee_name,
                                'line': node.start_point[0] + 1,
                                'file_path': file_path,
                                'relationship_type': 'calls'
                            })
            
            # 递归遍历
            for child in node.children:
                traverse(child, current_function)
        
        traverse(node)
        return relationships
    
    def extract_inheritance_relationships(self, file_path: str, language: Optional[str] = None) -> List[Dict]:
        """
        提取类继承关系
        
        Args:
            file_path: 文件路径
            language: 语言类型，如果不提供则自动检测
            
        Returns:
            继承关系列表，格式: [{'child': str, 'parent': str, 'line': int, 'file_path': str}]
        """
        if language is None:
            language = self.detect_language(file_path)
        
        if language is None or language not in self.parsers:
            return []
        
        try:
            with open(file_path, 'rb') as f:
                code = f.read()
            
            parser = self.parsers[language]
            tree = parser.parse(code)
            code_str = code.decode('utf-8', errors='ignore')
            
            if language == 'python':
                return self._extract_python_inheritance_relationships(tree.root_node, code_str, file_path)
            elif language in ['javascript', 'typescript']:
                return self._extract_js_inheritance_relationships(tree.root_node, code_str, file_path)
            
            return []
        except Exception as e:
            logger.error(f"提取继承关系失败 {file_path}: {e}")
            return []
    
    def _extract_python_inheritance_relationships(self, node: Node, code_str: str, file_path: str) -> List[Dict]:
        """提取 Python 类继承关系（使用 AST）"""
        try:
            import ast as py_ast
            ast_tree = py_ast.parse(code_str)
            relationships = []
            
            class InheritanceVisitor(py_ast.NodeVisitor):
                def visit_ClassDef(self, node):
                    child_name = node.name
                    for base in node.bases:
                        parent_name = None
                        if isinstance(base, py_ast.Name):
                            parent_name = base.id
                        elif isinstance(base, py_ast.Attribute):
                            # 处理 module.Class 的情况
                            if isinstance(base.value, py_ast.Name):
                                parent_name = f"{base.value.id}.{base.attr}"
                        
                        if parent_name:
                            relationships.append({
                                'child': child_name,
                                'parent': parent_name,
                                'line': node.lineno,
                                'file_path': file_path,
                                'relationship_type': 'inherits'
                            })
                    self.generic_visit(node)
            
            visitor = InheritanceVisitor()
            visitor.visit(ast_tree)
            return relationships
        except Exception as e:
            logger.warning(f"使用 AST 提取继承关系失败: {e}")
            return []
    
    def _extract_js_inheritance_relationships(self, node: Node, code_str: str, file_path: str) -> List[Dict]:
        """提取 JavaScript/TypeScript 类继承关系"""
        relationships = []
        code_bytes = code_str.encode('utf-8')
        
        def traverse(node: Node):
            if node.type == 'class_declaration':
                name_node = node.child_by_field_name('name')
                if name_node:
                    child_name = code_bytes[name_node.start_byte:name_node.end_byte].decode('utf-8')
                    
                    # 提取基类
                    superclass_node = node.child_by_field_name('superclass')
                    if superclass_node:
                        parent_name = None
                        if superclass_node.type == 'identifier':
                            parent_name = code_bytes[superclass_node.start_byte:superclass_node.end_byte].decode('utf-8')
                        elif superclass_node.type == 'member_expression':
                            parent_name = code_bytes[superclass_node.start_byte:superclass_node.end_byte].decode('utf-8')
                        
                        if parent_name:
                            relationships.append({
                                'child': child_name,
                                'parent': parent_name,
                                'line': node.start_point[0] + 1,
                                'file_path': file_path,
                                'relationship_type': 'inherits'
                            })
            
            for child in node.children:
                traverse(child)
        
        traverse(node)
        return relationships
