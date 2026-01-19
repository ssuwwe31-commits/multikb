#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直接测试 tree-sitter-languages XML 支持
使用 conda 环境的 Python
"""

import sys

print("=" * 60)
print("测试 tree-sitter-languages XML 支持")
print("=" * 60)

# 1. 检查包
print("\n1. 检查 tree-sitter-languages 包...")
try:
    from tree_sitter_languages import get_language, get_parser
    print("   [OK] tree-sitter-languages 已安装")
except ImportError as e:
    print(f"   [ERROR] 未安装: {e}")
    sys.exit(1)

# 2. 测试 XML
print("\n2. 测试 XML 解析器...")
xml_ok = False
try:
    xml_parser = get_parser('xml')
    print("   [OK] XML 解析器初始化成功")
    xml_ok = True
except Exception as e:
    print(f"   [ERROR] XML 解析器失败: {e}")

# 3. 测试解析
if xml_ok:
    print("\n3. 测试 XML 解析...")
    try:
        test_xml = b'<?xml version="1.0"?><root><child>test</child></root>'
        tree = xml_parser.parse(test_xml)
        print("   [OK] XML 解析成功")
        print(f"   [INFO] 根节点: {tree.root_node.type}")
    except Exception as e:
        print(f"   [ERROR] 解析失败: {e}")

# 4. 列出所有解析器
print("\n4. 检查所有解析器...")
test_langs = ['python', 'javascript', 'java', 'xml', 'json', 'yaml', 'html']
available = []
for lang in test_langs:
    try:
        get_parser(lang)
        available.append(lang)
    except:
        pass

print(f"   [OK] 可用解析器: {', '.join(available)}")
print(f"   [结论] XML 支持: {'是' if 'xml' in available else '否'}")

print("\n" + "=" * 60)
