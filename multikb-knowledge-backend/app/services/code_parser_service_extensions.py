"""
代码解析服务扩展
为新增语言提供符号和导入提取方法
"""

from typing import List, Dict, Optional
from tree_sitter import Node

from app.core.logging import logger


def extract_java_symbols(node: Node, code: bytes) -> List[Dict]:
    """提取 Java 符号"""
    symbols = []
    code_str = code.decode('utf-8', errors='ignore')
    
    def traverse(node: Node):
        # 类定义
        if node.type == 'class_declaration':
            name_node = node.child_by_field_name('name')
            if name_node:
                name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                symbols.append({
                    'type': 'class',
                    'name': name,
                    'line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1
                })
        
        # 方法定义
        elif node.type == 'method_declaration':
            name_node = node.child_by_field_name('name')
            if name_node:
                name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                symbols.append({
                    'type': 'method',
                    'name': name,
                    'line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1
                })
        
        # 接口定义
        elif node.type == 'interface_declaration':
            name_node = node.child_by_field_name('name')
            if name_node:
                name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                symbols.append({
                    'type': 'interface',
                    'name': name,
                    'line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1
                })
        
        for child in node.children:
            traverse(child)
    
    traverse(node)
    return symbols


def extract_java_imports(node: Node, code: bytes) -> List[Dict]:
    """提取 Java 导入语句"""
    imports = []
    
    def traverse(node: Node):
        if node.type == 'import_declaration':
            scoped_identifier = node.child_by_field_name('name')
            if scoped_identifier:
                module = code[scoped_identifier.start_byte:scoped_identifier.end_byte].decode('utf-8')
                imports.append({
                    'type': 'import',
                    'module': module,
                    'line': node.start_point[0] + 1
                })
        
        for child in node.children:
            traverse(child)
    
    traverse(node)
    return imports


def extract_php_symbols(node: Node, code: bytes) -> List[Dict]:
    """提取 PHP 符号"""
    symbols = []
    
    def traverse(node: Node):
        # 类定义
        if node.type == 'class_declaration':
            name_node = node.child_by_field_name('name')
            if name_node:
                name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                symbols.append({
                    'type': 'class',
                    'name': name,
                    'line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1
                })
        
        # 函数定义
        elif node.type == 'function_definition':
            name_node = node.child_by_field_name('name')
            if name_node:
                name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                symbols.append({
                    'type': 'function',
                    'name': name,
                    'line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1
                })
        
        for child in node.children:
            traverse(child)
    
    traverse(node)
    return symbols


def extract_php_imports(node: Node, code: bytes) -> List[Dict]:
    """提取 PHP 导入语句"""
    imports = []
    
    def traverse(node: Node):
        # use 语句
        if node.type == 'use_declaration':
            for child in node.children:
                if child.type == 'namespace_name':
                    module = code[child.start_byte:child.end_byte].decode('utf-8')
                    imports.append({
                        'type': 'use',
                        'module': module,
                        'line': node.start_point[0] + 1
                    })
        
        # require/include 语句
        elif node.type in ['require_expression', 'include_expression']:
            string_node = node.child_by_field_name('source')
            if string_node:
                module = code[string_node.start_byte:string_node.end_byte].decode('utf-8')
                module = module.strip('"').strip("'")
                imports.append({
                    'type': 'require',
                    'module': module,
                    'line': node.start_point[0] + 1
                })
        
        for child in node.children:
            traverse(child)
    
    traverse(node)
    return imports


def extract_ruby_symbols(node: Node, code: bytes) -> List[Dict]:
    """提取 Ruby 符号"""
    symbols = []
    
    def traverse(node: Node):
        # 类定义
        if node.type == 'class':
            constant = node.child_by_field_name('name')
            if constant:
                name = code[constant.start_byte:constant.end_byte].decode('utf-8')
                symbols.append({
                    'type': 'class',
                    'name': name,
                    'line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1
                })
        
        # 方法定义
        elif node.type == 'method':
            name_node = node.child_by_field_name('name')
            if name_node:
                name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                symbols.append({
                    'type': 'method',
                    'name': name,
                    'line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1
                })
        
        # 模块定义
        elif node.type == 'module':
            constant = node.child_by_field_name('name')
            if constant:
                name = code[constant.start_byte:constant.end_byte].decode('utf-8')
                symbols.append({
                    'type': 'module',
                    'name': name,
                    'line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1
                })
        
        for child in node.children:
            traverse(child)
    
    traverse(node)
    return symbols


def extract_ruby_imports(node: Node, code: bytes) -> List[Dict]:
    """提取 Ruby 导入语句"""
    imports = []
    
    def traverse(node: Node):
        # require 语句
        if node.type == 'call' and node.child_count > 0:
            method_name_node = node.children[0]
            if method_name_node and method_name_node.type == 'identifier':
                method_name = code[method_name_node.start_byte:method_name_node.end_byte].decode('utf-8')
                if method_name in ['require', 'require_relative', 'load']:
                    if node.child_count > 1:
                        arg = node.children[1]
                        if arg.type == 'string':
                            module = code[arg.start_byte:arg.end_byte].decode('utf-8')
                            module = module.strip('"').strip("'")
                            imports.append({
                                'type': method_name,
                                'module': module,
                                'line': node.start_point[0] + 1
                            })
        
        for child in node.children:
            traverse(child)
    
    traverse(node)
    return imports


def extract_c_cpp_symbols(node: Node, code: bytes, language: str) -> List[Dict]:
    """提取 C/C++ 符号"""
    symbols = []
    
    def traverse(node: Node):
        # 函数定义
        if node.type == 'function_definition':
            declarator = node.child_by_field_name('declarator')
            if declarator:
                function_declarator = declarator.child_by_field_name('declarator')
                if function_declarator:
                    identifier = function_declarator.child_by_field_name('declarator')
                    if identifier:
                        name = code[identifier.start_byte:identifier.end_byte].decode('utf-8')
                        symbols.append({
                            'type': 'function',
                            'name': name,
                            'line': node.start_point[0] + 1,
                            'end_line': node.end_point[0] + 1
                        })
        
        # 结构体定义
        elif node.type == 'struct_specifier':
            name_node = node.child_by_field_name('name')
            if name_node:
                name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                symbols.append({
                    'type': 'struct',
                    'name': name,
                    'line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1
                })
        
        # 类定义 (C++)
        elif node.type == 'class_specifier' and language == 'cpp':
            name_node = node.child_by_field_name('name')
            if name_node:
                name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                symbols.append({
                    'type': 'class',
                    'name': name,
                    'line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1
                })
        
        for child in node.children:
            traverse(child)
    
    traverse(node)
    return symbols


def extract_c_cpp_imports(node: Node, code: bytes) -> List[Dict]:
    """提取 C/C++ 导入语句"""
    imports = []
    
    def traverse(node: Node):
        # #include 预处理指令
        if node.type == 'preproc_include':
            string_literal = node.child_by_field_name('path')
            if string_literal:
                module = code[string_literal.start_byte:string_literal.end_byte].decode('utf-8')
                module = module.strip('"').strip('<').strip('>').strip()
                imports.append({
                    'type': 'include',
                    'module': module,
                    'line': node.start_point[0] + 1
                })
        
        for child in node.children:
            traverse(child)
    
    traverse(node)
    return imports


def extract_csharp_symbols(node: Node, code: bytes) -> List[Dict]:
    """提取 C# 符号"""
    symbols = []
    
    def traverse(node: Node):
        # 类定义
        if node.type == 'class_declaration':
            name_node = node.child_by_field_name('name')
            if name_node:
                name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                symbols.append({
                    'type': 'class',
                    'name': name,
                    'line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1
                })
        
        # 方法定义
        elif node.type == 'method_declaration':
            name_node = node.child_by_field_name('name')
            if name_node:
                name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                symbols.append({
                    'type': 'method',
                    'name': name,
                    'line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1
                })
        
        for child in node.children:
            traverse(child)
    
    traverse(node)
    return symbols


def extract_csharp_imports(node: Node, code: bytes) -> List[Dict]:
    """提取 C# 导入语句"""
    imports = []
    
    def traverse(node: Node):
        # using 语句
        if node.type == 'using_directive':
            qualified_name = node.child_by_field_name('name')
            if qualified_name:
                module = code[qualified_name.start_byte:qualified_name.end_byte].decode('utf-8')
                imports.append({
                    'type': 'using',
                    'module': module,
                    'line': node.start_point[0] + 1
                })
        
        for child in node.children:
            traverse(child)
    
    traverse(node)
    return imports


def extract_go_symbols(node: Node, code: bytes) -> List[Dict]:
    """提取 Go 符号"""
    symbols = []
    
    def traverse(node: Node):
        # 函数定义
        if node.type == 'function_declaration':
            name_node = node.child_by_field_name('name')
            if name_node:
                name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                symbols.append({
                    'type': 'function',
                    'name': name,
                    'line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1
                })
        
        # 类型定义
        elif node.type == 'type_declaration':
            type_spec = node.child_by_field_name('name')
            if type_spec:
                name = code[type_spec.start_byte:type_spec.end_byte].decode('utf-8')
                symbols.append({
                    'type': 'type',
                    'name': name,
                    'line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1
                })
        
        for child in node.children:
            traverse(child)
    
    traverse(node)
    return symbols


def extract_go_imports(node: Node, code: bytes) -> List[Dict]:
    """提取 Go 导入语句"""
    imports = []
    
    def traverse(node: Node):
        # import 语句
        if node.type == 'import_declaration':
            import_spec_list = node.child_by_field_name('name')
            if import_spec_list:
                module = code[import_spec_list.start_byte:import_spec_list.end_byte].decode('utf-8')
                module = module.strip('"')
                imports.append({
                    'type': 'import',
                    'module': module,
                    'line': node.start_point[0] + 1
                })
        
        for child in node.children:
            traverse(child)
    
    traverse(node)
    return imports


def extract_rust_symbols(node: Node, code: bytes) -> List[Dict]:
    """提取 Rust 符号"""
    symbols = []
    
    def traverse(node: Node):
        # 函数定义
        if node.type == 'function_item':
            name_node = node.child_by_field_name('name')
            if name_node:
                name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                symbols.append({
                    'type': 'function',
                    'name': name,
                    'line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1
                })
        
        # 结构体定义
        elif node.type == 'struct_item':
            name_node = node.child_by_field_name('name')
            if name_node:
                name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                symbols.append({
                    'type': 'struct',
                    'name': name,
                    'line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1
                })
        
        # impl 块
        elif node.type == 'impl_item':
            trait = node.child_by_field_name('trait')
            type_identifier = node.child_by_field_name('type')
            if type_identifier:
                name = code[type_identifier.start_byte:type_identifier.end_byte].decode('utf-8')
                symbols.append({
                    'type': 'impl',
                    'name': name,
                    'line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1
                })
        
        for child in node.children:
            traverse(child)
    
    traverse(node)
    return symbols


def extract_rust_imports(node: Node, code: bytes) -> List[Dict]:
    """提取 Rust 导入语句"""
    imports = []
    
    def traverse(node: Node):
        # use 语句
        if node.type == 'use_declaration':
            scoped_use_list = node.child_by_field_name('path')
            if scoped_use_list:
                module = code[scoped_use_list.start_byte:scoped_use_list.end_byte].decode('utf-8')
                imports.append({
                    'type': 'use',
                    'module': module,
                    'line': node.start_point[0] + 1
                })
        
        for child in node.children:
            traverse(child)
    
    traverse(node)
    return imports


def extract_generic_symbols(node: Node, code: bytes, language: str) -> List[Dict]:
    """通用符号提取方法（用于未特殊处理的语言）"""
    symbols = []
    
    def traverse(node: Node):
        # 尝试识别常见的符号节点类型
        common_symbol_types = [
            'function_definition', 'function_declaration', 'function',
            'class_definition', 'class_declaration', 'class',
            'method_definition', 'method_declaration', 'method',
            'type_definition', 'type_declaration'
        ]
        
        if node.type in common_symbol_types:
            # 尝试提取名称
            name_node = node.child_by_field_name('name')
            if not name_node:
                # 尝试从第一个子节点获取名称
                if node.children:
                    name_node = node.children[0]
            
            if name_node and name_node.type in ['identifier', 'type_identifier']:
                try:
                    name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                    symbol_type = 'function' if 'function' in node.type else 'class' if 'class' in node.type else 'symbol'
                    symbols.append({
                        'type': symbol_type,
                        'name': name,
                        'line': node.start_point[0] + 1,
                        'end_line': node.end_point[0] + 1
                    })
                except Exception:
                    pass
        
        for child in node.children:
            traverse(child)
    
    traverse(node)
    return symbols


def extract_generic_imports(node: Node, code: bytes, language: str) -> List[Dict]:
    """通用导入提取方法（用于未特殊处理的语言）"""
    imports = []
    
    def traverse(node: Node):
        # 尝试识别常见的导入节点类型
        common_import_types = [
            'import_statement', 'import_declaration', 'import',
            'use_statement', 'use_declaration', 'use',
            'require_statement', 'include_statement'
        ]
        
        if node.type in common_import_types:
            # 尝试提取模块名
            source_node = node.child_by_field_name('source')
            if not source_node:
                source_node = node.child_by_field_name('path')
            if not source_node:
                source_node = node.child_by_field_name('name')
            
            if source_node:
                try:
                    module = code[source_node.start_byte:source_node.end_byte].decode('utf-8')
                    module = module.strip('"').strip("'").strip('<').strip('>')
                    imports.append({
                        'type': 'import',
                        'module': module,
                        'line': node.start_point[0] + 1
                    })
                except Exception:
                    pass
        
        for child in node.children:
            traverse(child)
    
    traverse(node)
    return imports


def extract_java_call_relationships(node: Node, code_str: str, file_path: str) -> List[Dict]:
    """提取 Java 函数调用关系（基础实现）"""
    # TODO: 实现 Java 调用关系提取
    return []


def extract_java_inheritance_relationships(node: Node, code_str: str, file_path: str) -> List[Dict]:
    """提取 Java 类继承关系"""
    relationships = []
    code_bytes = code_str.encode('utf-8')
    
    def traverse(node: Node):
        if node.type == 'class_declaration':
            name_node = node.child_by_field_name('name')
            if name_node:
                child_name = code_bytes[name_node.start_byte:name_node.end_byte].decode('utf-8')
                
                # 提取基类
                superclass = node.child_by_field_name('superclass')
                if superclass:
                    parent_name = code_bytes[superclass.start_byte:superclass.end_byte].decode('utf-8')
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


def extract_c_cpp_call_relationships(node: Node, code_str: str, file_path: str) -> List[Dict]:
    """提取 C/C++ 函数调用关系（基础实现）"""
    # TODO: 实现 C/C++ 调用关系提取
    return []


def extract_c_cpp_inheritance_relationships(node: Node, code_str: str, file_path: str) -> List[Dict]:
    """提取 C++ 类继承关系"""
    relationships = []
    code_bytes = code_str.encode('utf-8')
    
    def traverse(node: Node):
        if node.type == 'class_specifier':
            name_node = node.child_by_field_name('name')
            if name_node:
                child_name = code_bytes[name_node.start_byte:name_node.end_byte].decode('utf-8')
                
                # 提取基类
                base_class_clause = node.child_by_field_name('base_clause')
                if base_class_clause:
                    for child in base_class_clause.children:
                        if child.type == 'type_identifier':
                            parent_name = code_bytes[child.start_byte:child.end_byte].decode('utf-8')
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
