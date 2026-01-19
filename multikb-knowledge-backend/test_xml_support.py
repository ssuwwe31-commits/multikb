#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 tree-sitter-languages 是否支持 XML
"""

import sys
import os

# 设置输出编码为 UTF-8（Windows 兼容）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("=" * 60)
print("测试 tree-sitter-languages XML 支持")
print("=" * 60)

# 1. 检查包是否安装
print("\n1. 检查 tree-sitter-languages 包...")
try:
    import tree_sitter_languages
    print(f"   [OK] tree-sitter-languages 已安装")
    print(f"   [INFO] 包路径: {tree_sitter_languages.__file__}")
except ImportError as e:
    print(f"   [ERROR] tree-sitter-languages 未安装: {e}")
    print(f"   [INFO] 尝试检查其他可能的包名...")
    try:
        import tree_sitter
        print(f"   [INFO] tree-sitter 已安装: {tree_sitter.__file__}")
    except ImportError:
        print(f"   [ERROR] tree-sitter 也未安装")
    sys.exit(1)

# 2. 检查可用的函数
print("\n2. 检查可用函数...")
try:
    from tree_sitter_languages import get_language, get_parser
    print(f"   [OK] get_language 可用")
    print(f"   [OK] get_parser 可用")
except ImportError as e:
    print(f"   [ERROR] 无法导入函数: {e}")
    sys.exit(1)

# 3. 测试 XML 解析器
print("\n3. 测试 XML 解析器...")
xml_parser_available = False
try:
    xml_parser = get_parser('xml')
    print(f"   [OK] XML 解析器初始化成功")
    print(f"   [INFO] 解析器类型: {type(xml_parser)}")
    xml_parser_available = True
except Exception as e:
    print(f"   [ERROR] XML 解析器初始化失败: {e}")
    print(f"   [WARN] tree-sitter-languages 可能不支持 XML")

# 4. 测试 XML 语言对象
print("\n4. 测试 XML 语言对象...")
xml_language_available = False
try:
    xml_language = get_language('xml')
    print(f"   [OK] XML 语言对象获取成功")
    print(f"   [INFO] 语言类型: {type(xml_language)}")
    xml_language_available = True
except Exception as e:
    print(f"   [ERROR] XML 语言对象获取失败: {e}")

# 5. 测试实际解析 XML
print("\n5. 测试实际解析 XML...")
if xml_parser_available:
    try:
        xml_parser = get_parser('xml')
        test_xml = b'<?xml version="1.0"?><root><child>test</child></root>'
        tree = xml_parser.parse(test_xml)
        print(f"   [OK] XML 解析成功")
        print(f"   [INFO] 根节点类型: {tree.root_node.type}")
        root_text = tree.root_node.text.decode('utf-8')[:50] if tree.root_node.text else "N/A"
        print(f"   [INFO] 根节点文本: {root_text}")
    except Exception as e:
        print(f"   [ERROR] XML 解析失败: {e}")
else:
    print(f"   [SKIP] 跳过解析测试（解析器不可用）")

# 6. 列出所有可用的解析器
print("\n6. 检查所有可用的解析器...")
try:
    # 尝试获取一些常见语言的解析器，看看哪些可用
    test_languages = ['python', 'javascript', 'java', 'xml', 'json', 'yaml', 'html']
    available = []
    unavailable = []
    
    for lang in test_languages:
        try:
            parser = get_parser(lang)
            available.append(lang)
        except Exception as e:
            error_msg = str(e)[:80].replace('\n', ' ')
            unavailable.append((lang, error_msg))
    
    print(f"   [OK] 可用的解析器: {', '.join(available)}")
    if unavailable:
        print(f"   [ERROR] 不可用的解析器:")
        for lang, error in unavailable:
            print(f"      - {lang}: {error}")
    
    if 'xml' in available:
        print(f"\n   [结论] tree-sitter-languages 支持 XML")
    else:
        print(f"\n   [结论] tree-sitter-languages 不支持 XML")
        
except Exception as e:
    print(f"   [WARN] 检查解析器时出错: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
