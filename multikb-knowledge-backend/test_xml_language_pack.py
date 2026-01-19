#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 tree-sitter-language-pack XML 支持
"""

import sys
import io

# 设置 UTF-8 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("=" * 60)
print("测试 tree-sitter-language-pack XML 支持")
print("=" * 60)

# 1. 检查包
print("\n1. 检查 tree-sitter-language-pack 包...")
try:
    from tree_sitter_language_pack import get_language, get_parser
    print("   [OK] tree-sitter-language-pack 已安装")
    PACK_SOURCE = 'tree-sitter-language-pack'
except ImportError:
    try:
        from tree_sitter_languages import get_language, get_parser
        print("   [WARN] 使用 tree-sitter-languages（降级）")
        PACK_SOURCE = 'tree-sitter-languages'
    except ImportError:
        print("   [ERROR] 未安装任何 tree-sitter 语言包")
        sys.exit(1)

# 2. 测试 XML 解析器
print("\n2. 测试 XML 解析器...")
xml_ok = False
xml_error = None
try:
    xml_parser = get_parser('xml')
    if xml_parser:
        print("   [OK] XML 解析器初始化成功")
        xml_ok = True
    else:
        print("   [ERROR] XML 解析器返回 None")
except Exception as e:
    xml_error = str(e)
    print(f"   [ERROR] XML 解析器失败: {e}")

# 3. 测试解析
if xml_ok:
    print("\n3. 测试 XML 解析...")
    try:
        test_xml = b'<?xml version="1.0"?><root><child attr="value">test</child></root>'
        tree = xml_parser.parse(test_xml)
        if tree:
            print("   [OK] XML 解析成功")
            print(f"   [INFO] 根节点类型: {tree.root_node.type}")
            print(f"   [INFO] 根节点文本: {tree.root_node.text.decode('utf-8')[:50]}...")
            
            # 遍历子节点
            def print_node(node, depth=0):
                indent = "  " * depth
                node_text = node.text.decode('utf-8')[:30] if node.text else ""
                print(f"{indent}- {node.type} (行 {node.start_point[0]+1}, 列 {node.start_point[1]+1}) {node_text}")
                for child in node.children:
                    print_node(child, depth + 1)
            
            print("\n   [INFO] AST 结构:")
            print_node(tree.root_node)
        else:
            print("   [ERROR] 解析返回 None")
    except Exception as e:
        print(f"   [ERROR] 解析失败: {e}")

# 4. 测试其他语言（验证包完整性）
print("\n4. 检查其他语言支持...")
test_langs = ['python', 'javascript', 'java', 'xml', 'json', 'yaml', 'html']
available = []
failed = []
for lang in test_langs:
    try:
        parser = get_parser(lang)
        if parser:
            available.append(lang)
        else:
            failed.append(f"{lang} (返回 None)")
    except Exception as e:
        failed.append(f"{lang} ({str(e)[:30]})")

print(f"   [OK] 可用解析器: {', '.join(available)}")
if failed:
    print(f"   [WARN] 失败的解析器: {', '.join(failed)}")

# 5. 测试实际 XML 文件（如果存在）
print("\n5. 测试实际 XML 文件...")
import os
test_files = [
    'pom.xml',
    'test.xml',
    '../pom.xml',
    '../../pom.xml'
]

found_xml = False
for test_file in test_files:
    if os.path.exists(test_file):
        try:
            with open(test_file, 'rb') as f:
                content = f.read()
            tree = xml_parser.parse(content)
            if tree:
                print(f"   [OK] 成功解析: {test_file}")
                print(f"   [INFO] 根节点: {tree.root_node.type}")
                found_xml = True
                break
        except Exception as e:
            print(f"   [WARN] 解析 {test_file} 失败: {e}")

if not found_xml:
    print("   [INFO] 未找到测试 XML 文件，跳过实际文件测试")

# 6. 总结
print("\n" + "=" * 60)
print("测试总结")
print("=" * 60)
print(f"包来源: {PACK_SOURCE}")
print(f"XML 支持: {'✅ 是' if xml_ok else '❌ 否'}")
if xml_error:
    print(f"错误信息: {xml_error}")
print(f"可用语言数: {len(available)}")
print(f"XML 在可用列表中: {'✅ 是' if 'xml' in available else '❌ 否'}")

if xml_ok:
    print("\n✅ 结论: tree-sitter-language-pack 支持 XML 解析")
else:
    print("\n❌ 结论: tree-sitter-language-pack 不支持 XML 解析")
    print("   将使用标准库降级处理")

print("=" * 60)
