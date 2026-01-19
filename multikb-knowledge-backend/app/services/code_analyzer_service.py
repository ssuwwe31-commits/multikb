"""
代码分析服务
对整个仓库进行深度分析，生成文档和依赖图
"""

import os
import re
import ast
import json
from typing import Dict, List, Optional
from pathlib import Path
from collections import defaultdict
from datetime import datetime

from app.core.logging import logger
from app.services.code_parser_service import CodeParserService
from app.services.code_statistics_analyzer import CodeStatisticsAnalyzer
from app.services.code_diagram_generator import CodeDiagramGenerator
from app.services.code_quality_analyzer import CodeQualityAnalyzer
from app.services.code_architecture_analyzer import CodeArchitectureAnalyzer
from app.services.code_wiki_generator import CodeWikiGenerator


class CodeAnalyzerService:
    """代码分析服务（生成文档摘要和依赖图）"""
    
    # 忽略的目录
    IGNORE_PATTERNS = [
        'node_modules', 'dist', 'build', '__pycache__', '.git',
        'venv', 'env', '.venv', 'target', 'out', '.next',
        'coverage', '.pytest_cache', '.mypy_cache'
    ]
    
    # 压缩文件路径特征（用于识别和过滤）
    MINIFIED_FILE_PATTERNS = [
        '_next/static/chunks',  # Next.js 打包文件
        '/dist/',               # 构建产物
        '/build/',              # 构建产物
        '.min.js',              # 压缩的 JS 文件
        '.bundle.js',           # 打包文件
        '.chunk.js',            # 代码块文件
    ]
    
    def __init__(self):
        """初始化分析服务"""
        self.parser_service = CodeParserService()
        # 初始化拆分后的模块
        self.statistics_analyzer = CodeStatisticsAnalyzer()
        self.diagram_generator = CodeDiagramGenerator()
        self.quality_analyzer = CodeQualityAnalyzer(is_minified_file_func=self._is_minified_file)
        self.architecture_analyzer = CodeArchitectureAnalyzer(diagram_generator=self.diagram_generator, db=None, repository_id=None)
        self.wiki_generator = CodeWikiGenerator(architecture_analyzer=self.architecture_analyzer, db=None, repository_id=None)
        # 注意：OllamaService 需要 db 参数，这里先不初始化
        # 将在实际调用时动态创建
        logger.info("代码分析服务初始化完成（已使用拆分后的模块）")
    
    def analyze_repository(self, repo_path: str) -> Dict:
        """
        分析整个仓库
        
        Args:
            repo_path: 仓库本地路径
            
        Returns:
            分析结果字典，包含：
            - files: 文件分析列表
            - statistics: 统计信息
            - dependencies: 依赖关系图
            - summary: LLM 生成的项目摘要
        """
        logger.info(f"开始分析仓库: {repo_path}")
        
        # 1. 扫描所有代码文件
        files = self._scan_code_files(repo_path)
        logger.info(f"扫描到 {len(files)} 个代码文件")
        
        # 2. 解析每个文件
        analyzed_files = []
        for file_path in files:
            language = self.parser_service.detect_language(file_path)
            if language:
                analysis = self.parser_service.parse_file(file_path, language)
                if analysis:
                    # 转换为相对路径
                    analysis['file_path'] = os.path.relpath(file_path, repo_path)
                    analyzed_files.append(analysis)
        
        logger.info(f"成功解析 {len(analyzed_files)} 个文件")
        
        # 3. 统计信息（使用拆分后的模块，传递 repo_path 以支持 LLM 增强）
        statistics = self.statistics_analyzer.calculate_statistics(analyzed_files, repo_path=repo_path)
        
        # 3.5. 如果规则检测未发现 API 端点，使用架构提取的 LLM 增强结果更新统计
        if statistics.get('api_endpoints', {}).get('backend', 0) == 0:
            logger.info(f"[API统计] 规则检测未发现后端端点，尝试使用架构提取的 LLM 增强结果...")
            try:
                external_services = statistics.get('external_services', [])
                arch_details = self.architecture_analyzer.extract_architecture_details(analyzed_files, repo_path, external_services)
                llm_endpoints_count = len(arch_details.get('api_endpoints_detail', []))
                if llm_endpoints_count > 0:
                    statistics['api_endpoints']['backend'] = llm_endpoints_count
                    logger.info(f"[API统计] ✅ 使用架构提取的 LLM 增强结果更新统计: {llm_endpoints_count} 个后端端点")
            except Exception as e:
                logger.warning(f"[API统计] 使用架构提取结果更新统计失败: {e}")
        
        # 4. 构建依赖关系图
        dependencies = self._build_dependency_graph(analyzed_files, repo_path)
        
        # 5. 生成项目摘要（使用 LLM）
        try:
            summary = self._generate_summary(analyzed_files, statistics, repo_path)
        except Exception as e:
            logger.error(f"生成摘要失败: {e}")
            summary = "自动生成摘要失败，请手动添加项目描述。"
        
        return {
            'files': analyzed_files,
            'statistics': statistics,
            'dependencies': dependencies,
            'summary': summary
        }
    
    def _scan_code_files(self, repo_path: str) -> List[str]:
        """
        扫描所有代码文件
        
        Args:
            repo_path: 仓库路径
            
        Returns:
            代码文件路径列表
        """
        code_files = []
        skipped_minified_count = 0  # 统计跳过的压缩文件数量
        
        for root, dirs, files in os.walk(repo_path):
            # 排除忽略目录
            dirs[:] = [d for d in dirs if d not in self.IGNORE_PATTERNS]
            
            for file in files:
                file_path = os.path.join(root, file)
                if self.parser_service.is_code_file(file_path):
                    # 过滤压缩/混淆文件
                    if not self._is_minified_file(file_path):
                        code_files.append(file_path)
                    else:
                        skipped_minified_count += 1
                        # 移除每个文件的详细日志，改为批量统计
        
        # 只在有跳过的文件时记录统计信息
        if skipped_minified_count > 0:
            logger.info(f"扫描完成: 找到 {len(code_files)} 个代码文件，跳过 {skipped_minified_count} 个压缩文件")
        else:
            logger.debug(f"扫描完成: 找到 {len(code_files)} 个代码文件")
        
        return code_files
    
    def _is_minified_file(self, file_path: str) -> bool:
        """
        检测是否为压缩/混淆文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            True 如果是压缩文件，False 否则
        """
        # 统一路径分隔符为 /（兼容 Windows 和 Linux）
        file_path_normalized = file_path.replace('\\', '/')
        file_path_lower = file_path_normalized.lower()
        
        # 检查路径特征
        for pattern in self.MINIFIED_FILE_PATTERNS:
            if pattern in file_path_lower:
                return True
        
        return False
    
    def _calculate_statistics(self, analyzed_files: List[Dict]) -> Dict:
        """
        【已废弃】请使用 self.statistics_analyzer.calculate_statistics()
        保留此方法仅用于向后兼容
        """
        return self.statistics_analyzer.calculate_statistics(analyzed_files)
    
    def _count_api_endpoints(self, analyzed_files: List[Dict], repo_path: str = None) -> Dict:
        """
        统计 API 端点数量（使用深度静态分析 + LLM 增强）
        
        Args:
            analyzed_files: 已分析的文件列表
            repo_path: 仓库路径（可选，用于 LLM 增强检测）
            
        Returns:
            API 统计信息 {'frontend': int, 'backend': int}
        """
        frontend_count = 0
        backend_count = 0
        frontend_files = []  # 调试：记录被识别为前端的文件
        backend_files_checked = []  # 调试：记录检查过的后端文件
        
        # 第一轮：规则检测
        for file_data in analyzed_files:
            file_path = file_data.get('file_path', '')
            language = file_data.get('language', '')
            
            # 前端路由检测（基于文件路径）
            if self._is_frontend_route_file(file_path, language):
                count = self._count_frontend_routes(file_data)
                frontend_count += count
                frontend_files.append((file_path, language, count))  # 调试
            
            # 后端 API 端点检测（使用精确解析）
            if self._is_backend_api_file(file_path, language):
                count = self._count_backend_endpoints_precise(file_data)
                backend_count += count
                backend_files_checked.append((file_path, language, count))
        
        # 第二轮：如果规则检测结果较少，使用 LLM 增强检测（仅后端）
        if backend_count == 0 and repo_path:
            logger.info(f"[API统计] 规则检测未发现后端端点，尝试使用 LLM 增强检测...")
            llm_backend_count = 0
            
            # 检查看起来像路由文件但规则检测为0的文件
            for file_data in analyzed_files:
                file_path = file_data.get('file_path', '')
                language = file_data.get('language', '')
                
                # 如果文件看起来像路由文件（包含 handler, route 等），但规则检测为0
                path_lower = file_path.lower()
                looks_like_route = any(kw in path_lower for kw in ['handler', 'route', 'api', 'endpoint'])
                
                if looks_like_route and language == 'python':
                    # 使用 LLM 增强检测
                    try:
                        endpoints = self.architecture_analyzer.extract_api_endpoints_with_llm(file_data, repo_path)
                        if endpoints:
                            llm_backend_count += len(endpoints)
                            logger.info(f"[API统计] LLM 在文件 {file_path} 中检测到 {len(endpoints)} 个端点")
                    except Exception as e:
                        logger.debug(f"[API统计] LLM 检测文件 {file_path} 失败: {e}")
            
            if llm_backend_count > 0:
                backend_count = llm_backend_count
                logger.info(f"[API统计] LLM 增强检测补充了 {llm_backend_count} 个后端端点")
        
        # 调试日志
        if frontend_files:
            logger.info(f"检测到 {len(frontend_files)} 个前端路由文件，总计 {frontend_count} 个路由")
            for file_path, lang, count in frontend_files[:10]:  # 只显示前10个
                logger.debug(f"  前端文件: {file_path} ({lang}) -> {count} 个路由")
        else:
            logger.warning(f"未检测到任何前端路由文件！检查的文件类型: {set(f.get('language', '') for f in analyzed_files[:100])}")
            # 显示一些 TypeScript/JavaScript 文件路径作为参考
            ts_js_files = [f for f in analyzed_files if f.get('language') in ['typescript', 'javascript', 'tsx', 'jsx']][:10]
            logger.debug(f"示例 TS/JS 文件路径: {[f.get('file_path') for f in ts_js_files]}")
        
        if backend_files_checked:
            logger.debug(f"规则检测检查了 {len(backend_files_checked)} 个后端文件，发现 {backend_count} 个端点")
        
        logger.info(f"API 统计完成 - 前端: {frontend_count}, 后端: {backend_count}")
        return {
            'frontend': frontend_count,
            'backend': backend_count
        }
    
    def _is_frontend_route_file(self, file_path: str, language: str) -> bool:
        """
        判断是否为前端路由文件（通用版，适配绝大多数前端项目）
        
        检测策略（优先级从高到低）：
        1. 路由配置文件（router.ts, routes.js 等）
        2. 文件系统路由（Next.js, Remix, Nuxt 等）
        3. 前端页面文件（基于文件类型和目录结构）
        """
        if language not in ['javascript', 'typescript', 'jsx', 'tsx', 'vue']:
            return False
        
        # 统一路径分隔符为 /（兼容 Windows 和 Linux）
        file_path_normalized = file_path.replace('\\', '/')
        file_path_lower = file_path_normalized.lower()
        
        # 排除非前端文件
        if any(exclude in file_path_lower for exclude in [
            '/node_modules/', '/dist/', '/build/', '/.next/', '/.nuxt/',
            '/coverage/', '/.git/', '/.svn/', '/venv/', '/env/',
            # 构建和依赖目录
        ]):
            return False
        
        # 1. 检测路由配置文件（优先级最高，最准确）
        # router.ts, routes.js, router.config.js, routes/index.ts 等
        if any(keyword in file_path_lower for keyword in [
            'router', 'route', 'routes'
        ]):
            # 排除后端路由（通常在特定目录中）
            if any(backend_dir in file_path_lower for backend_dir in [
                '/api/', '/server/', '/backend/', '/app/api/',
                '/controllers/', '/handlers/', '/endpoints/'
            ]):
                return False
            return True
        
        # 2. 检测文件系统路由（Next.js, Remix, Nuxt, SvelteKit 等）
        # 检测规则：
        # - 目录名：app/, pages/, routes/, src/pages/, src/routes/
        # - 特殊文件名：page.tsx, layout.tsx, route.ts (Next.js)
        # - 特殊文件名：+page.svelte, +layout.svelte (SvelteKit)
        
        route_patterns = [
            # Next.js App Router
            'page.tsx', 'page.ts', 'page.jsx', 'page.js',
            'layout.tsx', 'layout.ts', 'layout.jsx', 'layout.js',
            'route.ts', 'route.tsx',
            # Remix
            'routes.ts', 'routes.js',
            # Nuxt
            '.vue',  # Nuxt 自动路由
            # SvelteKit
            '+page.svelte', '+layout.svelte', '+page.ts', '+layout.ts',
            # 目录模式
            '/app/', '/pages/', '/routes/',
        ]
        
        # 检查是否匹配文件系统路由模式
        for pattern in route_patterns:
            if pattern in file_path_lower:
                # 排除后端目录中的路由
                if any(backend_dir in file_path_lower for backend_dir in [
                    '/api/', '/server/', '/backend/',
                    '/app/api/', '/app/server/',  # Next.js API routes 不算前端路由
                ]) and not ('/pages/' in file_path_lower or '/routes/' in file_path_lower):
                    continue
                return True
        
        # 3. 只检测真正的页面文件，不包括普通组件
        # 只统计文件系统路由（Next.js, Nuxt 等）和入口文件
        # 不包括普通的组件文件（components/*.tsx 等）
        
        frontend_extensions = ['.tsx', '.jsx', '.vue']
        if not any(file_path.endswith(ext) for ext in frontend_extensions):
            return False
        
        # 排除后端和测试文件
        backend_indicators = [
            '/api/', '/server/', '/backend/', '/services/',
            '/controllers/', '/handlers/', '/endpoints/',
            '/middleware/', '/utils/api/', '/lib/api/',
            '/test/', '/tests/', '/__tests__/', '/spec/', '/__mocks__/',
        ]
        
        if any(indicator in file_path_lower for indicator in backend_indicators):
            return False
        
        # 只检测页面文件目录（不包括 components）
        # 这些目录中的文件通常对应实际的路由
        page_indicators = [
            # 页面目录（明确的路由）
            '/pages/', '/routes/', '/views/',  # Vue views 也算页面
            # 文档网站页面
            '/website/src/pages/', '/docs/src/pages/',
            # 入口文件目录
            '/src/app/', '/app/',  # Next.js App Router
        ]
        
        # 如果文件在页面目录中
        if any(indicator in file_path_lower for indicator in page_indicators):
            return True
        
        # 检测入口文件（App.tsx, main.tsx 等）
        # 这些通常是应用的主入口，不算路由，但可以作为特殊页面
        path_parts = file_path.replace('\\', '/').split('/')
        if len(path_parts) <= 3:  # 在根目录或一级子目录
            filename_lower = path_parts[-1].lower()
            if any(name in filename_lower for name in [
                'app.', 'main.', 'index.', 'root.', 'entry.'
            ]) and any(file_path.endswith(ext) for ext in frontend_extensions):
                return True
        
        # 注意：不再统计普通的组件文件（components/*.tsx）
        # 这些不是路由，只是可复用的组件
        
        return False
    
    def _is_backend_api_file(self, file_path: str, language: str) -> bool:
        """判断是否为后端 API 文件"""
        # 统一路径分隔符为 /（兼容 Windows 和 Linux）
        file_path_normalized = file_path.replace('\\', '/')
        file_path_lower = file_path_normalized.lower()
        
        # 后端 API 文件关键词（扩展：包含 handler, service 等）
        backend_keywords = [
            'api', 'views', 'routes', 'endpoints', 'controller', 
            'handler', 'handlers',  # 添加 handler 支持
            'service', 'services'  # 某些框架使用 service 作为 API 层
        ]
        
        if language == 'python':
            return any(keyword in file_path_lower for keyword in backend_keywords)
        elif language in ['javascript', 'typescript']:
            return any(keyword in file_path_lower for keyword in backend_keywords)
        elif language == 'java':
            return any(keyword in file_path_lower for keyword in ['controller', 'handler', 'api'])
        
        return False
    
    def _count_frontend_routes(self, file_data: Dict) -> int:
        """
        统计前端路由数量（更精确的统计）
        
        策略：
        1. 文件系统路由（page.tsx 等）：每个文件 = 1 个路由
        2. 路由配置文件（router.ts 等）：解析实际的路由定义数量
        3. 入口文件（App.tsx 等）：算 1 个路由
        4. 普通组件文件：不算路由（已在上层过滤）
        """
        file_path = file_data.get('file_path', '').lower()
        
        # 1. 文件系统路由（Next.js, Nuxt, SvelteKit 等）
        # 每个页面文件对应一个路由
        if any(pattern in file_path for pattern in [
            'page.tsx', 'page.ts', 'page.jsx', 'page.js',
            'page.vue', '+page.svelte', '+page.ts',
            'layout.tsx', 'layout.ts',  # Next.js layout 也算路由
        ]):
            return 1
        
        # 2. 路由配置文件（router.ts, routes.js 等）
        # 需要解析实际的路由定义数量
        if any(keyword in file_path for keyword in ['router', 'route', 'routes']):
            # 尝试从文件内容中解析路由数量
            # 对于常见的路由配置格式，统计路由数组的长度
            # 这里简化处理：统计路由相关的导出/定义
            symbols = file_data.get('symbols', [])
            
            # 查找路由数组或路由对象
            # 通常路由配置会导出 routes 数组或 route 对象
            route_definitions = [
                s for s in symbols 
                if s['type'] in ['variable', 'constant'] 
                and ('route' in s.get('name', '').lower() or 'path' in s.get('name', '').lower())
            ]
            
            # 如果找到明确的路由定义，使用其数量
            if route_definitions:
                # 简化：假设每个路由定义变量对应多个路由
                # 实际应该解析数组长度，但这里先保守估计
                return len(route_definitions)
            
            # 如果没有找到明确的路由定义，但文件是路由配置文件
            # 保守估计：至少 1 个路由（可能是单页应用）
            return 1
        
        # 3. 入口文件（App.tsx, main.tsx 等）
        # 通常单页应用的主入口算 1 个路由
        path_parts = file_path.replace('\\', '/').split('/')
        if len(path_parts) <= 3:
            filename_lower = path_parts[-1].lower()
            if any(name in filename_lower for name in [
                'app.', 'main.', 'index.', 'root.', 'entry.'
            ]):
                return 1
        
        # 4. 其他情况（不应该到达这里，因为上层已经过滤）
        # 如果到达这里，说明是页面目录中的文件，算 1 个路由
        return 1
    
    def _count_backend_endpoints_precise(self, file_data: Dict) -> int:
        """
        精确统计后端 API 端点数量（使用 AST 解析）
        
        支持的框架：
        - Python: FastAPI, Flask, Django
        - JavaScript/TypeScript: Express, NestJS
        - Java: Spring Boot
        """
        language = file_data.get('language', '')
        file_path = file_data.get('file_path', '')
        
        try:
            if language == 'python':
                return self._count_python_endpoints(file_data)
            elif language in ['javascript', 'typescript']:
                return self._count_js_endpoints(file_data)
            elif language == 'java':
                return self._count_java_endpoints(file_data)
        except Exception as e:
            logger.warning(f"精确统计失败，使用降级方案: {file_path}, 错误: {e}")
            # 降级：使用符号数量估算
            symbols = file_data.get('symbols', [])
            return len([s for s in symbols if s['type'] in ['function', 'method']])
        
        return 0
    
    def _count_python_endpoints(self, file_data: Dict) -> int:
        """
        统计 Python API 端点（FastAPI, Flask, Django）
        
        识别模式：
        - FastAPI: @app.get, @app.post, @router.get 等
        - Flask: @app.route, @bp.route
        - Django: 通过 path() / re_path() 定义
        """
        # 尝试读取文件内容进行 AST 解析
        file_path = file_data.get('file_path', '')
        
        # 如果没有原始文件路径，使用符号信息降级
        if not file_path or not os.path.exists(file_path):
            # 检查符号中的装饰器信息（如果解析器已提取）
            symbols = file_data.get('symbols', [])
            count = 0
            for symbol in symbols:
                if symbol['type'] == 'function':
                    # 简化判断：API 文件中的函数很可能是端点
                    count += 1
            return count
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 使用 AST 解析
            tree = ast.parse(content)
            endpoint_count = 0
            
            # FastAPI/Flask 装饰器模式
            decorator_patterns = [
                'get', 'post', 'put', 'delete', 'patch',  # HTTP 方法
                'route',  # Flask
            ]
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    for decorator in node.decorator_list:
                        # 处理 @app.get() 形式
                        if isinstance(decorator, ast.Call):
                            if hasattr(decorator.func, 'attr'):
                                method = decorator.func.attr
                                if method in decorator_patterns:
                                    endpoint_count += 1
                                    break
                        # 处理 @app.route 形式（不带括号）
                        elif isinstance(decorator, ast.Attribute):
                            if decorator.attr in decorator_patterns:
                                endpoint_count += 1
                                break
            
            # Django URL patterns（正则匹配）
            if 'path(' in content or 're_path(' in content or 'url(' in content:
                # 统计 path() 调用
                django_patterns = re.findall(r'\b(?:path|re_path|url)\s*\(', content)
                endpoint_count += len(django_patterns)
            
            return endpoint_count
            
        except Exception as e:
            logger.warning(f"Python AST 解析失败: {file_path}, 错误: {e}")
            # 降级方案
            symbols = file_data.get('symbols', [])
            return len([s for s in symbols if s['type'] == 'function'])
    
    def _count_js_endpoints(self, file_data: Dict) -> int:
        """
        统计 JavaScript/TypeScript API 端点（Express, NestJS）
        
        识别模式：
        - Express: app.get(), router.post(), app.route().get()
        - NestJS: @Get(), @Post() 装饰器
        """
        file_path = file_data.get('file_path', '')
        
        if not file_path or not os.path.exists(file_path):
            symbols = file_data.get('symbols', [])
            return len([s for s in symbols if s['type'] == 'function'])
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            endpoint_count = 0
            
            # Express 模式：app.get(), router.post() 等
            express_patterns = [
                r'(?:app|router)\s*\.\s*(?:get|post|put|delete|patch)\s*\(',
                r'(?:app|router)\s*\.\s*route\s*\(',
            ]
            
            for pattern in express_patterns:
                matches = re.findall(pattern, content)
                endpoint_count += len(matches)
            
            # NestJS 装饰器：@Get(), @Post() 等
            nestjs_patterns = [
                r'@(?:Get|Post|Put|Delete|Patch)\s*\(',
            ]
            
            for pattern in nestjs_patterns:
                matches = re.findall(pattern, content)
                endpoint_count += len(matches)
            
            return endpoint_count
            
        except Exception as e:
            logger.warning(f"JS/TS 解析失败: {file_path}, 错误: {e}")
            symbols = file_data.get('symbols', [])
            return len([s for s in symbols if s['type'] == 'function'])
    
    def _count_java_endpoints(self, file_data: Dict) -> int:
        """
        统计 Java API 端点（Spring Boot）
        
        识别模式：
        - @GetMapping, @PostMapping, @PutMapping, @DeleteMapping, @PatchMapping
        - @RequestMapping
        """
        file_path = file_data.get('file_path', '')
        
        if not file_path or not os.path.exists(file_path):
            symbols = file_data.get('symbols', [])
            return len([s for s in symbols if s['type'] == 'method'])
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Spring Boot 注解模式
            spring_patterns = [
                r'@(?:Get|Post|Put|Delete|Patch)Mapping\s*\(',
                r'@RequestMapping\s*\(',
            ]
            
            endpoint_count = 0
            for pattern in spring_patterns:
                matches = re.findall(pattern, content)
                endpoint_count += len(matches)
            
            return endpoint_count
            
        except Exception as e:
            logger.warning(f"Java 解析失败: {file_path}, 错误: {e}")
            symbols = file_data.get('symbols', [])
            return len([s for s in symbols if s['type'] == 'method'])
    
    def _count_database_tables(self, analyzed_files: List[Dict]) -> int:
        """
        统计数据库表数量（使用深度静态分析）
        
        支持：
        - SQL 文件: 精确解析 CREATE TABLE 语句
        - Python ORM: SQLAlchemy, Django Models
        - Java ORM: JPA Entity
        - JavaScript/TypeScript ORM: TypeORM, Sequelize
        
        Args:
            analyzed_files: 已分析的文件列表
            
        Returns:
            数据库表数量
        """
        table_names = set()
        
        for file_data in analyzed_files:
            file_path = file_data.get('file_path', '')
            language = file_data.get('language', '')
            
            try:
                # SQL 文件 - 精确解析 CREATE TABLE
                if file_path.lower().endswith('.sql'):
                    tables = self._parse_sql_tables(file_data)
                    table_names.update(tables)
                
                # Python ORM 模型（更严格的判断）
                elif language == 'python' and self._is_python_model_file(file_path):
                    # 额外检查：确保文件路径或内容中确实有 ORM 相关的导入
                    imports = file_data.get('imports', [])
                    has_orm_import = any(
                        'sqlalchemy' in imp.get('module', '').lower() or 
                        'django.db' in imp.get('module', '').lower() or
                        'models' in imp.get('module', '').lower()
                        for imp in imports
                    )
                    if has_orm_import:
                        tables = self._parse_python_orm_tables(file_data)
                        table_names.update(tables)
                
                # Java Entity
                elif language == 'java' and self._is_java_entity_file(file_path):
                    tables = self._parse_java_entity_tables(file_data)
                    table_names.update(tables)
                
                # JavaScript/TypeScript ORM（更严格的判断）
                elif language in ['javascript', 'typescript'] and self._is_js_model_file(file_path):
                    # 额外检查：确保文件路径或内容中确实有 ORM 相关的导入
                    imports = file_data.get('imports', [])
                    has_orm_import = any(
                        'typeorm' in imp.get('module', '').lower() or 
                        'sequelize' in imp.get('module', '').lower() or
                        'mongoose' in imp.get('module', '').lower() or
                        'prisma' in imp.get('module', '').lower()
                        for imp in imports
                    )
                    if has_orm_import:
                        tables = self._parse_js_orm_tables(file_data)
                        table_names.update(tables)
                    
            except Exception as e:
                logger.warning(f"解析数据库表失败: {file_path}, 错误: {e}")
                continue
        
        count = len(table_names)
        logger.info(f"数据库表统计完成 - 共 {count} 个表")
        return count
    
    def _parse_sql_tables(self, file_data: Dict) -> set:
        """精确解析 SQL 文件中的 CREATE TABLE 语句"""
        file_path = file_data.get('file_path', '')
        tables = set()
        
        if not os.path.exists(file_path):
            return tables
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 正则匹配 CREATE TABLE 语句（支持多种变体）
            patterns = [
                r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"\']?(\w+)[`"\']?',
                r'create\s+table\s+(?:if\s+not\s+exists\s+)?[`"\']?(\w+)[`"\']?',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    # 排除常见的非表名（如临时表）
                    if not match.lower().startswith('temp_') and not match.lower().startswith('tmp_'):
                        tables.add(match)
            
            logger.debug(f"SQL 文件 {file_path} 解析出 {len(tables)} 个表")
            
        except Exception as e:
            logger.warning(f"SQL 解析失败: {file_path}, 错误: {e}")
        
        return tables
    
    def _is_python_model_file(self, file_path: str) -> bool:
        """判断是否为 Python ORM 模型文件"""
        file_path_lower = file_path.lower()
        return any(keyword in file_path_lower for keyword in ['model', 'models', 'entity', 'entities'])
    
    def _parse_python_orm_tables(self, file_data: Dict) -> set:
        """
        解析 Python ORM 模型（SQLAlchemy, Django）
        
        识别模式：
        - SQLAlchemy: class User(Base), class User(db.Model)
        - Django: class User(models.Model)
        - 排除：Base, Mixin, Abstract 等基类
        """
        file_path = file_data.get('file_path', '')
        tables = set()
        
        if not os.path.exists(file_path):
            # 使用符号信息降级
            symbols = file_data.get('symbols', [])
            for symbol in symbols:
                if symbol['type'] == 'class' and not self._is_base_class(symbol['name']):
                    tables.add(symbol['name'])
            return tables
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 使用 AST 解析
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                    
                    # 排除基类和 Mixin
                    if self._is_base_class(class_name):
                        continue
                    
                    # 检查是否继承自 ORM 基类
                    is_model = False
                    for base in node.bases:
                        # 处理简单继承：User(Base)
                        if isinstance(base, ast.Name):
                            base_name = base.id
                            if base_name in ['Base', 'Model', 'Document']:
                                is_model = True
                                break
                        # 处理属性继承：User(db.Model), User(models.Model)
                        elif isinstance(base, ast.Attribute):
                            if base.attr in ['Model', 'Document']:
                                is_model = True
                                break
                    
                    if is_model:
                        tables.add(class_name)
            
            logger.debug(f"Python ORM 文件 {file_path} 解析出 {len(tables)} 个表模型")
            
        except Exception as e:
            logger.warning(f"Python ORM 解析失败: {file_path}, 错误: {e}")
            # 降级：使用符号信息
            symbols = file_data.get('symbols', [])
            for symbol in symbols:
                if symbol['type'] == 'class' and not self._is_base_class(symbol['name']):
                    tables.add(symbol['name'])
        
        return tables
    
    def _is_java_entity_file(self, file_path: str) -> bool:
        """判断是否为 Java Entity 文件"""
        file_path_lower = file_path.lower()
        return any(keyword in file_path_lower for keyword in ['entity', 'entities', 'model', 'domain'])
    
    def _parse_java_entity_tables(self, file_data: Dict) -> set:
        """
        解析 Java JPA Entity
        
        识别模式：
        - @Entity 注解的类
        - @Table(name="...") 指定的表名
        """
        file_path = file_data.get('file_path', '')
        tables = set()
        
        if not os.path.exists(file_path):
            symbols = file_data.get('symbols', [])
            for symbol in symbols:
                if symbol['type'] == 'class':
                    tables.add(symbol['name'])
            return tables
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 查找 @Entity 注解的类
            # 匹配模式：@Entity ... class User
            entity_pattern = r'@Entity[^}]*?class\s+(\w+)'
            matches = re.findall(entity_pattern, content, re.DOTALL)
            
            for class_name in matches:
                tables.add(class_name)
            
            # 查找 @Table 注解指定的表名
            table_pattern = r'@Table\s*\(\s*name\s*=\s*["\'](\w+)["\']'
            table_matches = re.findall(table_pattern, content)
            
            for table_name in table_matches:
                tables.add(table_name)
            
            logger.debug(f"Java Entity 文件 {file_path} 解析出 {len(tables)} 个表")
            
        except Exception as e:
            logger.warning(f"Java Entity 解析失败: {file_path}, 错误: {e}")
            symbols = file_data.get('symbols', [])
            for symbol in symbols:
                if symbol['type'] == 'class':
                    tables.add(symbol['name'])
        
        return tables
    
    def _is_js_model_file(self, file_path: str) -> bool:
        """判断是否为 JavaScript/TypeScript ORM 模型文件"""
        file_path_lower = file_path.lower()
        return any(keyword in file_path_lower for keyword in ['model', 'models', 'entity', 'entities', 'schema'])
    
    def _parse_js_orm_tables(self, file_data: Dict) -> set:
        """
        解析 JavaScript/TypeScript ORM 模型（TypeORM, Sequelize）
        
        识别模式：
        - TypeORM: @Entity() class User
        - Sequelize: sequelize.define('User', ...)
        """
        file_path = file_data.get('file_path', '')
        tables = set()
        
        if not os.path.exists(file_path):
            symbols = file_data.get('symbols', [])
            for symbol in symbols:
                if symbol['type'] == 'class':
                    tables.add(symbol['name'])
            return tables
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # TypeORM: @Entity() class User
            typeorm_pattern = r'@Entity\s*\([^)]*\)[^}]*?(?:export\s+)?class\s+(\w+)'
            matches = re.findall(typeorm_pattern, content, re.DOTALL)
            tables.update(matches)
            
            # Sequelize: sequelize.define('User', ...)
            sequelize_pattern = r'\.define\s*\(\s*["\'](\w+)["\']'
            matches = re.findall(sequelize_pattern, content)
            tables.update(matches)
            
            logger.debug(f"JS/TS ORM 文件 {file_path} 解析出 {len(tables)} 个表")
            
        except Exception as e:
            logger.warning(f"JS/TS ORM 解析失败: {file_path}, 错误: {e}")
            symbols = file_data.get('symbols', [])
            for symbol in symbols:
                if symbol['type'] == 'class':
                    tables.add(symbol['name'])
        
        return tables
    
    def _is_base_class(self, class_name: str) -> bool:
        """判断是否为基类（应该排除的类）"""
        base_class_keywords = [
            'Base', 'Mixin', 'Abstract', 'Meta', 'Config',
            'BaseModel', 'AbstractModel', 'ModelMixin'
        ]
        return any(keyword in class_name for keyword in base_class_keywords)
    
    def _detect_external_services(self, analyzed_files: List[Dict]) -> List[Dict]:
        """
        检测外部依赖服务（增强版）
        
        Args:
            analyzed_files: 已分析的文件列表
            
        Returns:
            外部服务列表，格式: [{'name': str, 'type': str, 'count': int}]
        """
        services = defaultdict(int)
        
        # 常见的外部服务关键词
        service_keywords = {
            'mysql': 'MySQL',
            'postgresql': 'PostgreSQL',
            'postgres': 'PostgreSQL',
            'mongodb': 'MongoDB',
            'redis': 'Redis',
            'elasticsearch': 'Elasticsearch',
            'opensearch': 'OpenSearch',
            'kafka': 'Kafka',
            'rabbitmq': 'RabbitMQ',
            'zookeeper': 'Zookeeper',
            'nacos': 'Nacos',
            'consul': 'Consul',
            'etcd': 'etcd',
            'minio': 'MinIO',
            's3': 'AWS S3',
            'dynamodb': 'DynamoDB',
            'cassandra': 'Cassandra',
            'memcached': 'Memcached',
            'nginx': 'Nginx',
            'apache': 'Apache',
            'docker': 'Docker',
            'kubernetes': 'Kubernetes',
            'k8s': 'Kubernetes',
            'celery': 'Celery',
            'ollama': 'Ollama',
        }
        
        for file_data in analyzed_files:
            file_path = file_data.get('file_path', '')
            file_path_lower = file_path.lower()
            
            # 检查配置文件（扩展检测范围）
            is_config = any(keyword in file_path_lower for keyword in [
                '.env', 'config', 'settings', 'application', 
                'docker-compose', 'dockerfile', '.yml', '.yaml', '.json',
                'package.json', 'requirements.txt', 'pom.xml', 'build.gradle'
            ])
            
            # 方法 1：检查 import 语句（更严格的匹配）
            imports = file_data.get('imports', [])
            for imp in imports:
                module = imp.get('module', '').lower()
                # 只检查实际使用的库，排除依赖包中的关键词
                # 例如：如果 import mysql.connector，才认为是使用 MySQL
                # 但如果 import some_mysql_helper（依赖包名），不应该算
                for keyword, service_name in service_keywords.items():
                    # 更严格的匹配：必须是直接导入该服务相关的库
                    # 例如：mysql, pymysql, mysql2, opensearch-py, @opensearch-project/opensearch 等
                    strict_patterns = {
                        'mysql': ['mysql', 'pymysql', 'mysql2', 'mysql-connector'],
                        'opensearch': ['opensearch', '@opensearch-project/opensearch'],
                        'elasticsearch': ['elasticsearch', '@elastic/elasticsearch'],
                        'redis': ['redis', 'ioredis', 'node_redis'],
                        'postgresql': ['psycopg2', 'pg', 'postgres', 'postgresql'],
                        'mongodb': ['pymongo', 'mongodb', 'mongoose'],
                    }
                    
                    # 检查是否匹配严格模式
                    if keyword in strict_patterns:
                        for pattern in strict_patterns[keyword]:
                            if module.startswith(pattern) or f'.{pattern}' in module or f'/{pattern}' in module:
                                services[service_name] += 1
                                break
                    else:
                        # 对于其他服务，使用更宽松的匹配
                        if keyword in module and len(module) < 50:  # 避免匹配过长的模块名
                            services[service_name] += 1
            
            # 方法 2：检查配置文件内容（需要实际读取文件）
            if is_config and os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read().lower()
                    
                    for keyword, service_name in service_keywords.items():
                        # 配置文件中更严格的匹配
                        config_patterns = [
                            f'{keyword}://',      # 连接字符串
                            f'{keyword}_',        # 环境变量
                            f'{keyword}=',        # 配置项
                            f'"{keyword}"',       # JSON 配置
                            f"'{keyword}'",       # JSON 配置
                            f':{keyword}',        # Docker compose
                        ]
                        for pattern in config_patterns:
                            if pattern in content:
                                services[service_name] += 1
                                break
                except Exception:
                    pass  # 忽略读取失败
            
            # 方法 3：检查文件路径（Docker, K8s 等）
            if 'dockerfile' in file_path_lower or 'docker-compose' in file_path_lower:
                services['Docker'] += 1
            if 'kubernetes' in file_path_lower or 'k8s' in file_path_lower:
                services['Kubernetes'] += 1
        
        # 转换为列表格式，按使用频率排序
        result = [
            {
                'name': name,
                'type': self._get_service_type(name),
                'count': count
            }
            for name, count in sorted(services.items(), key=lambda x: x[1], reverse=True)
        ]
        
        logger.info(f"检测到 {len(result)} 个外部服务: {[s['name'] for s in result]}")
        return result
    
    def _get_service_type(self, service_name: str) -> str:
        """获取服务类型"""
        db_services = {'MySQL', 'PostgreSQL', 'MongoDB', 'Cassandra', 'DynamoDB'}
        cache_services = {'Redis', 'Memcached'}
        mq_services = {'Kafka', 'RabbitMQ'}
        search_services = {'Elasticsearch', 'OpenSearch'}
        registry_services = {'Zookeeper', 'Nacos', 'Consul', 'etcd'}
        storage_services = {'MinIO', 'AWS S3'}
        ai_services = {'Ollama'}
        
        if service_name in db_services:
            return '数据库'
        elif service_name in cache_services:
            return '缓存'
        elif service_name in mq_services:
            return '消息队列'
        elif service_name in search_services:
            return '搜索引擎'
        elif service_name in registry_services:
            return '注册中心'
        elif service_name in storage_services:
            return '对象存储'
        elif service_name in ai_services:
            return 'AI服务'
        else:
            return '其他'
    
    def _build_dependency_graph(self, analyzed_files: List[Dict], repo_path: str) -> Dict:
        """
        构建依赖关系图
        
        Args:
            analyzed_files: 已分析的文件列表
            repo_path: 仓库路径
            
        Returns:
            依赖图，包含 nodes 和 edges
        """
        nodes = []
        edges = []
        
        # 构建文件到路径的映射
        file_map = {}
        for file_data in analyzed_files:
            file_path = file_data['file_path']
            file_map[file_path] = file_data
            
            # 添加节点
            nodes.append({
                'id': file_path,
                'name': Path(file_path).name,
                'type': 'file',
                'language': file_data.get('language'),
                'symbols_count': len(file_data.get('symbols', [])),
                'lines': file_data.get('lines', 0)
            })
        
        # 构建依赖边
        for file_data in analyzed_files:
            source_file = file_data['file_path']
            imports = file_data.get('imports', [])
            
            for imp in imports:
                module = imp.get('module', '')
                
                # 尝试解析为本地文件
                target_file = self._resolve_import(module, source_file, file_map.keys(), repo_path)
                
                if target_file:
                    edges.append({
                        'source': source_file,
                        'target': target_file,
                        'type': imp.get('type', 'import')
                    })
        
        return {
            'nodes': nodes,
            'edges': edges
        }
    
    def _resolve_import(
        self, 
        module: str, 
        source_file: str, 
        all_files: List[str],
        repo_path: str
    ) -> Optional[str]:
        """
        解析导入语句，查找对应的本地文件
        
        Args:
            module: 模块名
            source_file: 源文件路径
            all_files: 所有文件列表
            repo_path: 仓库路径
            
        Returns:
            目标文件路径，如果不是本地文件则返回 None
        """
        # 跳过外部包
        if not module.startswith('.') and not module.startswith('/'):
            # 简单启发式：如果不包含本地路径特征，可能是外部包
            if '/' not in module and '\\' not in module:
                return None
        
        # 处理相对导入（Python）
        if module.startswith('.'):
            source_dir = os.path.dirname(source_file)
            # 简化处理：./ 表示同目录，../ 表示上级目录
            if module.startswith('./'):
                module = module[2:]
            elif module.startswith('../'):
                source_dir = os.path.dirname(source_dir)
                module = module[3:]
            
            # 尝试不同扩展名
            for ext in ['.py', '.js', '.ts', '.jsx', '.tsx']:
                potential_path = os.path.join(source_dir, module + ext)
                potential_path = os.path.normpath(potential_path)
                if potential_path in all_files:
                    return potential_path
        
        # 处理绝对路径或相对路径（JavaScript）
        else:
            # 尝试不同扩展名
            for ext in ['', '.js', '.ts', '.jsx', '.tsx', '.py']:
                potential_path = module + ext
                if potential_path in all_files:
                    return potential_path
        
        return None
    
    def _generate_summary(
        self, 
        analyzed_files: List[Dict], 
        statistics: Dict,
        repo_path: str
    ) -> str:
        """
        使用 LLM 生成项目摘要
        
        Args:
            analyzed_files: 已分析的文件列表
            statistics: 统计信息
            repo_path: 仓库路径
            
        Returns:
            项目摘要文本
        """
        # 构建上下文信息
        context = self._build_summary_context(analyzed_files, statistics, repo_path)
        
        # 构建 Prompt
        prompt = f"""请基于以下代码仓库信息，生成一份简洁的项目说明文档（200-300字）：

{context}

请按照以下格式生成：
1. 项目简介（1-2句话）
2. 主要功能（3-5个要点）
3. 技术栈
4. 项目结构概述

要求：
- 语言简洁专业
- 重点突出核心功能
- 避免重复描述
"""
        
        # 调用 LLM（使用同步方式调用 Ollama）
        try:
            import requests
            from app.config.settings import settings
            
            logger.info(f"[LLM调用] 项目摘要生成使用模型 {settings.CODE_LLM_MODEL}, prompt 长度: {len(prompt)} 字符")
            
            # 直接调用 Ollama API
            response = requests.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.CODE_LLM_MODEL,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120  # 2分钟超时
            )
            response.raise_for_status()
            result = response.json()
            summary = result.get("response", "").strip()
            
            if summary:
                logger.info(f"[LLM调用] 项目摘要生成成功，响应长度: {len(summary)} 字符")
                return summary
            else:
                logger.warning("[LLM调用] 项目摘要生成返回空内容，使用默认摘要")
                return self._generate_default_summary(statistics)
                
        except Exception as e:
            logger.error(f"LLM 生成摘要失败: {e}")
            return self._generate_default_summary(statistics)
    
    def _build_summary_context(
        self, 
        analyzed_files: List[Dict], 
        statistics: Dict,
        repo_path: str
    ) -> str:
        """构建摘要生成的上下文"""
        context = f"""
## 基本信息
- 代码文件数：{statistics['total_files']}
- 总代码行数：{statistics['total_lines']}
- 函数数量：{statistics['total_functions']}
- 类数量：{statistics['total_classes']}
- 使用语言：{', '.join(statistics['languages'].keys())}

## 主要文件
"""
        
        # 列出重要文件
        key_files = []
        for file_data in analyzed_files:
            path = file_data['file_path']
            # 优先展示 README、主入口、配置文件
            if any(keyword in path.lower() for keyword in ['readme', 'main', 'index', 'app', 'server', 'config']):
                key_files.append(path)
        
        if key_files:
            for file in key_files[:10]:  # 最多10个
                context += f"- {file}\n"
        
        # 列出主要符号（前10个）
        context += "\n## 主要代码结构\n"
        symbol_count = 0
        for file_data in analyzed_files[:5]:  # 只看前5个文件
            symbols = file_data.get('symbols', [])
            for symbol in symbols[:3]:  # 每个文件最多3个符号
                if symbol_count >= 10:
                    break
                context += f"- {symbol['type'].capitalize()} `{symbol['name']}` in {file_data['file_path']}\n"
                symbol_count += 1
            if symbol_count >= 10:
                break
        
        return context
    
    def _generate_default_summary(self, statistics: Dict) -> str:
        """生成默认摘要（当 LLM 失败时）"""
        languages = ', '.join(statistics['languages'].keys())
        
        summary = f"""
## 项目概述

这是一个使用 {languages} 开发的项目。

## 基本统计

- 代码文件：{statistics['total_files']} 个
- 代码行数：{statistics['total_lines']} 行
- 函数数量：{statistics['total_functions']}
- 类数量：{statistics['total_classes']}

## 代码质量

- 平均复杂度：{statistics['complexity']['average']:.2f}
- 最大复杂度：{statistics['complexity']['max']}

请查看具体文件了解更多详情。
"""
        return summary.strip()
    
    def generate_wiki_content(self, repo_path: str, repo_name: str) -> Dict:
        """
        【已重构】生成 Wiki 页面的所有 AI 内容 - 现在委托给 CodeWikiGenerator
        保留此方法仅用于向后兼容
        """
        # 1. 分析仓库（获取基础数据）
        analysis = self.analyze_repository(repo_path)
        analyzed_files = analysis['files']
        statistics = analysis['statistics']
        dependencies = analysis.get('dependencies', {})
        
        # 2. 使用 Wiki 生成器生成内容
        wiki_content = self.wiki_generator.generate_wiki_content(
            repo_path, repo_name, analyzed_files, statistics, dependencies
        )
        
        # 3. 并行生成架构建议和代码质量建议
        import concurrent.futures
        
        def safe_generate_architecture_recommendations():
            try:
                external_services = statistics.get('external_services', [])
                arch_details = self.architecture_analyzer.extract_architecture_details(analyzed_files, repo_path, external_services)
                module_structure = self.wiki_generator.extract_module_structure(analyzed_files, repo_path)
                return self.architecture_analyzer.generate_architecture_recommendations(
                    analyzed_files, arch_details, module_structure, repo_path
                )
            except Exception as e:
                logger.error(f"生成架构建议失败: {e}")
                return {"patterns_detected": [], "potential_issues": [], "improvement_suggestions": []}
        
        def safe_generate_code_quality_recommendations():
            try:
                return self.quality_analyzer.generate_code_quality_recommendations(analyzed_files, statistics)
            except Exception as e:
                logger.error(f"生成代码质量建议失败: {e}")
                return {"code_smells": [], "refactoring_suggestions": [], "test_suggestions": []}
        
        logger.info("开始并行生成架构建议和代码质量建议")
        start_time = datetime.now()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                'architecture_recommendations': executor.submit(safe_generate_architecture_recommendations),
                'code_quality_recommendations': executor.submit(safe_generate_code_quality_recommendations),
            }
            
            for key, future in futures.items():
                try:
                    result = future.result(timeout=120)
                    wiki_content[key] = result
                    logger.info(f"✅ 并行任务完成: {key}")
                except concurrent.futures.TimeoutError:
                    logger.error(f"❌ 并行任务超时: {key}")
                    wiki_content[key] = {}
                except Exception as e:
                    logger.error(f"❌ 并行任务失败: {key}, 错误: {e}")
                    wiki_content[key] = {}
        
        parallel_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ 架构和质量建议并行生成完成，耗时: {parallel_time:.2f} 秒")
        
        return wiki_content
    
    def _build_wiki_context(
        self,
        analyzed_files: List[Dict],
        statistics: Dict,
        repo_path: str,
        repo_name: str
    ) -> str:
        """
        【已重构】构建 Wiki 内容生成的上下文 - 现在委托给 CodeWikiGenerator
        保留此方法仅用于向后兼容
        """
        return self.wiki_generator.build_wiki_context(analyzed_files, statistics, repo_path, repo_name)
    
    def _generate_wiki_content_with_llm(
        self,
        context: str,
        repo_name: str,
        statistics: Dict
    ) -> Dict:
        """
        【已重构】使用 LLM 生成所有 Wiki 内容 - 现在委托给 CodeWikiGenerator
        保留此方法仅用于向后兼容
        """
        return self.wiki_generator.generate_wiki_content_with_llm(context, repo_name, statistics)
    
    def _extract_module_structure(self, analyzed_files: List[Dict], repo_path: str) -> Dict:
        """
        【已重构】提取模块结构信息 - 现在委托给 CodeWikiGenerator
        保留此方法仅用于向后兼容
        """
        return self.wiki_generator.extract_module_structure(analyzed_files, repo_path)
    
    def _extract_dependency_info(self, repo_path: str) -> Dict:
        """
        【已重构】提取依赖信息 - 现在委托给 CodeWikiGenerator
        保留此方法仅用于向后兼容
        """
        return self.wiki_generator.extract_dependency_info(repo_path)
    
    def _extract_deployment_info(self, repo_path: str) -> Dict:
        """
        【已重构】提取部署信息 - 现在委托给 CodeWikiGenerator
        保留此方法仅用于向后兼容
        """
        return self.wiki_generator.extract_deployment_info(repo_path)
    
    def _extract_readme_content(self, repo_path: str) -> str:
        """
        【已重构】提取 README 内容 - 现在委托给 CodeWikiGenerator
        保留此方法仅用于向后兼容
        """
        return self.wiki_generator.extract_readme_content(repo_path)
    
    def _identify_key_files(self, repo_path: str) -> List[Dict]:
        """
        【已重构】识别关键文件 - 现在委托给 CodeWikiGenerator
        保留此方法仅用于向后兼容
        """
        return self.wiki_generator.identify_key_files(repo_path)
    
    def _score_file_importance(self, rel_path: str, file_name: str, entry_patterns: Dict, build_patterns: List[str], doc_patterns: List[str]) -> tuple:
        """
        【已重构】评分文件重要性 - 现在委托给 CodeWikiGenerator
        保留此方法仅用于向后兼容
        """
        return self.wiki_generator.score_file_importance(rel_path, file_name, entry_patterns, build_patterns, doc_patterns)
    
    def _extract_api_endpoints_detail(self, file_data: Dict, repo_path: str) -> List[Dict]:
        """
        【已重构】提取 API 端点详细信息 - 现在委托给 CodeArchitectureAnalyzer
        保留此方法仅用于向后兼容
        """
        return self.architecture_analyzer.extract_api_endpoints_detail(file_data, repo_path)
    
    def _extract_service_methods_detail(self, file_data: Dict, repo_path: str) -> List[Dict]:
        """
        【已重构】提取服务方法详细信息 - 现在委托给 CodeArchitectureAnalyzer
        保留此方法仅用于向后兼容
        """
        return self.architecture_analyzer.extract_service_methods_detail(file_data, repo_path)
    
    def _extract_architecture_details(self, analyzed_files: List[Dict], repo_path: str, external_services: Optional[List[Dict]] = None) -> Dict:
        """
        【已重构】提取详细的架构信息 - 现在委托给 CodeArchitectureAnalyzer
        保留此方法仅用于向后兼容
        """
        return self.architecture_analyzer.extract_architecture_details(analyzed_files, repo_path, external_services)
    
    def _generate_system_architecture_llm(
        self,
        analyzed_files: List[Dict],
        module_structure: Dict,
        repo_name: str,
        statistics: Dict,
        repo_path: str
    ) -> Dict:
        """
        【已重构】使用 LLM 生成详细的系统架构说明 - 现在委托给 CodeArchitectureAnalyzer
        保留此方法仅用于向后兼容
        """
        return self.architecture_analyzer.generate_system_architecture_llm(
            analyzed_files, module_structure, repo_name, statistics, repo_path
        )
    
    def _generate_tech_stack_llm(
        self,
        dependency_info: Dict,
        statistics: Dict,
        repo_path: str
    ) -> Dict:
        """
        【已重构】使用 LLM 生成技术栈说明 - 现在委托给 CodeArchitectureAnalyzer
        保留此方法仅用于向后兼容
        """
        return self.architecture_analyzer.generate_tech_stack_llm(dependency_info, statistics, repo_path)
    
    def _generate_component_relationships_llm(
        self,
        dependencies: Dict,
        module_structure: Dict,
        repo_name: str
    ) -> Dict:
        """
        【已重构】使用 LLM 生成组件关系说明 - 现在委托给 CodeArchitectureAnalyzer
        保留此方法仅用于向后兼容
        """
        return self.architecture_analyzer.generate_component_relationships_llm(dependencies, module_structure, repo_name)
    
    def _generate_deployment_models_llm(
        self,
        deployment_info: Dict,
        repo_path: str,
        repo_name: str
    ) -> Dict:
        """
        【已重构】使用 LLM 生成部署模型说明 - 现在委托给 CodeArchitectureAnalyzer
        保留此方法仅用于向后兼容
        """
        return self.architecture_analyzer.generate_deployment_models_llm(deployment_info, repo_path, repo_name)
    
    def _generate_getting_started_llm(
        self,
        readme_content: str,
        dependency_info: Dict,
        repo_path: str,
        repo_name: str
    ) -> Dict:
        """
        【已重构】使用 LLM 生成快速开始指南 - 现在委托给 CodeArchitectureAnalyzer
        保留此方法仅用于向后兼容
        """
        return self.architecture_analyzer.generate_getting_started_llm(readme_content, dependency_info, repo_path, repo_name)
    
    def _generate_mermaid_architecture_diagram(self, arch_details: Dict, statistics: Dict) -> str:
        """
        【已重构】生成 Mermaid 系统架构图 - 现在委托给 CodeDiagramGenerator
        保留此方法仅用于向后兼容
        """
        return self.diagram_generator.generate_architecture_diagram(arch_details, statistics)
    
    def _generate_mermaid_data_flow_diagram(self, arch_details: Dict) -> str:
        """
        【已重构】生成 Mermaid 数据流图 - 现在委托给 CodeDiagramGenerator
        保留此方法仅用于向后兼容
        """
        return self.diagram_generator.generate_data_flow_diagram(arch_details)
    
    def _generate_mermaid_api_diagram(self, arch_details: Dict) -> str:
        """
        【已重构】生成 Mermaid API 架构图 - 现在委托给 CodeDiagramGenerator
        保留此方法仅用于向后兼容
        """
        return self.diagram_generator.generate_api_diagram(arch_details)
    
    def _generate_architecture_recommendations(
        self,
        analyzed_files: List[Dict],
        arch_details: Dict,
        module_structure: Dict,
        repo_path: str
    ) -> Dict:
        """
        【已重构】生成架构建议 - 现在委托给 CodeArchitectureAnalyzer
        保留此方法仅用于向后兼容
        """
        return self.architecture_analyzer.generate_architecture_recommendations(
            analyzed_files, arch_details, module_structure, repo_path
        )
    
    def _detect_architecture_patterns(
        self,
        analyzed_files: List[Dict],
        arch_details: Dict,
        module_structure: Dict
    ) -> List[Dict]:
        """
        【已重构】检测架构模式 - 现在委托给 CodeArchitectureAnalyzer
        保留此方法仅用于向后兼容
        """
        return self.architecture_analyzer.detect_architecture_patterns(analyzed_files, arch_details, module_structure)
    
    def _detect_architecture_issues(
        self,
        module_structure: Dict,
        arch_details: Dict
    ) -> List[Dict]:
        """
        【已重构】检测潜在架构问题 - 现在委托给 CodeArchitectureAnalyzer
        保留此方法仅用于向后兼容
        """
        return self.architecture_analyzer.detect_architecture_issues(module_structure, arch_details)
    
    def _detect_circular_dependencies(self, module_structure: Dict) -> List[List[str]]:
        """
        【已重构】检测循环依赖 - 现在委托给 CodeArchitectureAnalyzer
        保留此方法仅用于向后兼容
        """
        return self.architecture_analyzer.detect_circular_dependencies(module_structure)
    
    def _detect_high_coupling(self, module_structure: Dict) -> List[Dict]:
        """
        【已重构】检测高耦合模块 - 现在委托给 CodeArchitectureAnalyzer
        保留此方法仅用于向后兼容
        """
        return self.architecture_analyzer.detect_high_coupling(module_structure)
    
    def _detect_critical_modules(self, module_structure: Dict, arch_details: Dict) -> List[Dict]:
        """
        【已重构】检测关键模块 - 现在委托给 CodeArchitectureAnalyzer
        保留此方法仅用于向后兼容
        """
        return self.architecture_analyzer.detect_critical_modules(module_structure, arch_details)
    
    def _generate_improvement_suggestions_llm(
        self,
        patterns: List[Dict],
        issues: List[Dict],
        arch_details: Dict,
        module_structure: Dict,
        repo_path: str
    ) -> List[Dict]:
        """
        【已重构】使用 LLM 生成改进建议 - 现在委托给 CodeArchitectureAnalyzer
        保留此方法仅用于向后兼容
        """
        return self.architecture_analyzer.generate_improvement_suggestions_llm(
            patterns, issues, arch_details, module_structure, repo_path
        )
    
    def _generate_code_quality_recommendations(
        self,
        analyzed_files: List[Dict],
        statistics: Dict
    ) -> Dict:
        """
        【已重构】生成代码质量建议 - 现在委托给 CodeQualityAnalyzer
        保留此方法仅用于向后兼容
        """
        return self.quality_analyzer.generate_code_quality_recommendations(analyzed_files, statistics)
    
    def _detect_code_smells(self, analyzed_files: List[Dict]) -> List[Dict]:
        """
        【已重构】检测代码异味 - 现在委托给 CodeQualityAnalyzer
        保留此方法仅用于向后兼容
        """
        return self.quality_analyzer.detect_code_smells(analyzed_files)
    
    def _generate_refactoring_suggestions_llm(
        self,
        code_smells: List[Dict],
        analyzed_files: List[Dict]
    ) -> List[Dict]:
        """
        【已重构】使用 LLM 生成重构建议 - 现在委托给 CodeQualityAnalyzer
        保留此方法仅用于向后兼容
        """
        return self.quality_analyzer.generate_refactoring_suggestions_llm(code_smells, analyzed_files)
    
    def _generate_test_suggestions(self, analyzed_files: List[Dict]) -> List[Dict]:
        """
        【已重构】生成测试建议 - 现在委托给 CodeQualityAnalyzer
        保留此方法仅用于向后兼容
        """
        return self.quality_analyzer.generate_test_suggestions(analyzed_files)
