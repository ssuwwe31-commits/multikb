#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单测试 tree-sitter-languages XML 支持
直接使用项目中已有的代码
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置输出编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("=" * 60)
print("测试 tree-sitter-languages XML 支持")
print("=" * 60)

# 1. 检查包是否可用
print("\n1. 检查 tree-sitter-languages 包...")
try:
    from tree_sitter_languages import get_language, get_parser
    print("   [OK] tree-sitter-languages 已安装")
except ImportError as e:
    print(f"   [ERROR] tree-sitter-languages 未安装: {e}")
    print("   请运行: pip install tree-sitter-languages")
    sys.exit(1)

# 2. 测试 XML 解析器
print("\n2. 测试 XML 解析器...")
xml_supported = False
try:
    xml_parser = get_parser('xml')
    print("   [OK] XML 解析器初始化成功")
    print(f"   [INFO] 解析器类型: {type(xml_parser)}")
    xml_supported = True
except Exception as e:
    print(f"   [ERROR] XML 解析器初始化失败: {e}")
    print("   [结论] tree-sitter-languages 不支持 XML")

# 3. 测试 XML 语言对象
print("\n3. 测试 XML 语言对象...")
try:
    xml_language = get_language('xml')
    print("   [OK] XML 语言对象获取成功")
    print(f"   [INFO] 语言类型: {type(xml_language)}")
except Exception as e:
    print(f"   [ERROR] XML 语言对象获取失败: {e}")

# 4. 测试实际解析
if xml_supported:
    print("\n4. 测试实际解析 XML...")
    try:
        xml_parser = get_parser('xml')
        test_xml = b'<?xml version="1.0"?><root><child>test</child></root>'
        tree = xml_parser.parse(test_xml)
        print("   [OK] XML 解析成功")
        print(f"   [INFO] 根节点类型: {tree.root_node.type}")
    except Exception as e:
        print(f"   [ERROR] XML 解析失败: {e}")

# 5. 列出所有可用的解析器
print("\n5. 检查所有可用的解析器...")
test_languages = ['python', 'javascript', 'java', 'xml', 'json', 'yaml', 'html', 'css']
available = []
unavailable = []

for lang in test_languages:
    try:
        parser = get_parser(lang)
        available.append(lang)
    except Exception as e:
        error_msg = str(e)[:60].replace('\n', ' ')
        unavailable.append((lang, error_msg))

print(f"   [OK] 可用的解析器 ({len(available)}): {', '.join(available)}")
if unavailable:
    print(f"   [ERROR] 不可用的解析器 ({len(unavailable)}):")
    for lang, error in unavailable:
        print(f"      - {lang}: {error}")

# 6. 最终结论
print("\n" + "=" * 60)
if 'xml' in available:
    print("[结论] tree-sitter-languages 支持 XML")
    print("       XML 文件可以被正确解析")
else:
    print("[结论] tree-sitter-languages 不支持 XML")
    print("       需要使用降级方案（返回基本信息）")
print("=" * 60)
