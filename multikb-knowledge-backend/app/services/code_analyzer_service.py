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
        # 注意：OllamaService 需要 db 参数，这里先不初始化
        # 将在实际调用时动态创建
        logger.info("代码分析服务初始化完成")
    
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
        
        # 3. 统计信息
        statistics = self._calculate_statistics(analyzed_files)
        
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
        计算统计信息
        
        Args:
            analyzed_files: 已分析的文件列表
            
        Returns:
            统计信息字典
        """
        stats = {
            'total_files': len(analyzed_files),
            'total_lines': 0,
            'total_functions': 0,
            'total_classes': 0,
            'languages': defaultdict(int),
            'complexity': {
                'total': 0,
                'average': 0,
                'max': 0
            },
            # 新增统计项
            'api_endpoints': {
                'frontend': 0,  # 前端接口数量
                'backend': 0,   # 后端接口数量
            },
            'database_tables': 0,  # 数据库表数量
            'external_services': []  # 外部依赖服务
        }
        
        complexities = []
        
        for file_data in analyzed_files:
            # 统计代码行数
            stats['total_lines'] += file_data.get('lines', 0)
            
            # 统计符号
            symbols = file_data.get('symbols', [])
            for symbol in symbols:
                if symbol['type'] == 'function':
                    stats['total_functions'] += 1
                elif symbol['type'] == 'class':
                    stats['total_classes'] += 1
            
            # 统计语言
            language = file_data.get('language')
            if language:
                stats['languages'][language] += 1
            
            # 统计复杂度
            complexity = file_data.get('complexity', {})
            cyclomatic = complexity.get('cyclomatic', 0)
            complexities.append(cyclomatic)
            stats['complexity']['total'] += cyclomatic
            stats['complexity']['max'] = max(stats['complexity']['max'], cyclomatic)
        
        # 计算平均复杂度
        if complexities:
            stats['complexity']['average'] = stats['complexity']['total'] / len(complexities)
        
        # 转换语言统计为列表
        stats['languages'] = dict(stats['languages'])
        
        # 统计 API 端点
        api_stats = self._count_api_endpoints(analyzed_files)
        stats['api_endpoints'].update(api_stats)
        
        # 统计数据库表
        stats['database_tables'] = self._count_database_tables(analyzed_files)
        
        # 检测外部依赖
        stats['external_services'] = self._detect_external_services(analyzed_files)
        
        return stats
    
    def _count_api_endpoints(self, analyzed_files: List[Dict]) -> Dict:
        """
        统计 API 端点数量（使用深度静态分析）
        
        Args:
            analyzed_files: 已分析的文件列表
            
        Returns:
            API 统计信息 {'frontend': int, 'backend': int}
        """
        frontend_count = 0
        backend_count = 0
        frontend_files = []  # 调试：记录被识别为前端的文件
        
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
        
        if language == 'python':
            return any(keyword in file_path_lower for keyword in ['api', 'views', 'routes', 'endpoints', 'controller'])
        elif language in ['javascript', 'typescript']:
            return any(keyword in file_path_lower for keyword in ['controller', 'api', 'routes', 'endpoints'])
        elif language == 'java':
            return 'controller' in file_path_lower
        
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
                logger.info(f"LLM 生成摘要成功，长度: {len(summary)} 字符")
                return summary
            else:
                logger.warning("LLM 返回空摘要，使用默认摘要")
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
        生成 Wiki 页面的所有 AI 内容
        
        Args:
            repo_path: 仓库本地路径
            repo_name: 仓库名称
            
        Returns:
            {
                "project_overview": "项目概述",
                "what_is_project": "项目是什么",
                "core_components": [...],
                "value_propositions": [...],
                "key_features": [...],
                "system_architecture": {...},
                "technology_stack": {...},
                "component_relationships": {...},
                "deployment_models": {...},
                "getting_started": {...}
            }
        """
        logger.info(f"开始生成 Wiki 内容: {repo_path}")
        
        # 1. 分析仓库（获取基础数据）
        analysis = self.analyze_repository(repo_path)
        analyzed_files = analysis['files']
        statistics = analysis['statistics']
        dependencies = analysis.get('dependencies', {})
        
        # 2. 构建基础上下文信息
        context = self._build_wiki_context(analyzed_files, statistics, repo_path, repo_name)
        
        # 3. 提取依赖和模块信息（用于系统架构分析）
        module_structure = self._extract_module_structure(analyzed_files, repo_path)
        dependency_info = self._extract_dependency_info(repo_path)
        deployment_info = self._extract_deployment_info(repo_path)
        readme_content = self._extract_readme_content(repo_path)
        
        # 提取架构详细信息（用于架构建议生成）
        arch_details = self._extract_architecture_details(analyzed_files, repo_path)
        
        # 4. 使用 LLM 生成基础内容（必须先完成，因为后续可能依赖）
        wiki_content = self._generate_wiki_content_with_llm(context, repo_name, statistics)
        
        # 5. 使用 LLM 并行生成扩展内容（系统架构、技术栈等）
        # 注意：系统架构需要先完成，因为它可能被其他部分引用
        wiki_content['system_architecture'] = self._generate_system_architecture_llm(
            analyzed_files, module_structure, repo_name, statistics, repo_path
        )
        
        # 并行执行独立的 LLM 调用（技术栈、组件关系、部署模型、快速开始）
        import concurrent.futures
        import threading
        
        def safe_generate_tech_stack():
            try:
                return self._generate_tech_stack_llm(dependency_info, statistics, repo_path)
            except Exception as e:
                logger.error(f"生成技术栈失败: {e}")
                return {"core_technologies": "生成失败", "key_dependencies_table": [], "technology_choices": ""}
        
        def safe_generate_component_relationships():
            try:
                return self._generate_component_relationships_llm(dependencies, module_structure, repo_name)
            except Exception as e:
                logger.error(f"生成组件关系失败: {e}")
                return {"service_dependencies": "生成失败", "component_relationships": "", "data_flow": ""}
        
        def safe_generate_deployment_models():
            try:
                return self._generate_deployment_models_llm(deployment_info, repo_path, repo_name)
            except Exception as e:
                logger.error(f"生成部署模型失败: {e}")
                return {"deployment_steps": [], "deployment_requirements": ""}
        
        def safe_generate_getting_started():
            try:
                return self._generate_getting_started_llm(readme_content, dependency_info, repo_path, repo_name)
            except Exception as e:
                logger.error(f"生成快速开始指南失败: {e}")
                return {"prerequisites": [], "installation_steps": [], "key_endpoints": [], "quick_start_summary": ""}
        
        # 使用 ThreadPoolExecutor 并行执行（IO密集型任务）
        logger.info("开始并行生成 Wiki 扩展内容（技术栈、组件关系、部署模型、快速开始）")
        start_time = datetime.now()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                'technology_stack': executor.submit(safe_generate_tech_stack),
                'component_relationships': executor.submit(safe_generate_component_relationships),
                'deployment_models': executor.submit(safe_generate_deployment_models),
                'getting_started': executor.submit(safe_generate_getting_started),
            }
            
            # 等待所有并行任务完成并收集结果
            for key, future in futures.items():
                try:
                    result = future.result(timeout=120)  # 每个任务最多等待2分钟
                    wiki_content[key] = result
                    logger.info(f"✅ 并行任务完成: {key}")
                except concurrent.futures.TimeoutError:
                    logger.error(f"❌ 并行任务超时: {key}")
                    wiki_content[key] = {}
                except Exception as e:
                    logger.error(f"❌ 并行任务失败: {key}, 错误: {e}")
                    wiki_content[key] = {}
        
        parallel_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ 并行生成完成，耗时: {parallel_time:.2f} 秒")
        
        # 6. 并行生成架构建议和代码质量建议（这两个也是独立的）
        logger.info("开始并行生成架构建议和代码质量建议")
        start_time = datetime.now()
        
        def safe_generate_architecture_recommendations():
            try:
                return self._generate_architecture_recommendations(
                    analyzed_files, arch_details, module_structure, repo_path
                )
            except Exception as e:
                logger.error(f"生成架构建议失败: {e}")
                return {"patterns_detected": [], "potential_issues": [], "improvement_suggestions": []}
        
        def safe_generate_code_quality_recommendations():
            try:
                return self._generate_code_quality_recommendations(analyzed_files, statistics)
            except Exception as e:
                logger.error(f"生成代码质量建议失败: {e}")
                return {"code_smells": [], "refactoring_suggestions": [], "test_suggestions": []}
        
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
        
        # 7. 添加关键文件列表
        key_files = self._identify_key_files(repo_path)
        wiki_content['key_files'] = key_files[:30]  # 最多返回 30 个关键文件
        
        logger.info(f"Wiki 内容生成完成: repo_path={repo_path}, "
                   f"关键文件数={len(key_files)}, "
                   f"架构建议数={len(wiki_content.get('architecture_recommendations', {}).get('patterns_detected', []))}, "
                   f"代码异味数={len(wiki_content.get('code_quality_recommendations', {}).get('code_smells', []))}")
        return wiki_content
    
    def _build_wiki_context(
        self,
        analyzed_files: List[Dict],
        statistics: Dict,
        repo_path: str,
        repo_name: str
    ) -> str:
        """构建 Wiki 内容生成的上下文"""
        # 按目录分组组件
        dir_map = defaultdict(lambda: {
            'files': 0,
            'lines': 0,
            'symbols': 0,
            'languages': set(),
            'file_paths': []
        })
        
        for file_data in analyzed_files:
            path = file_data['file_path']
            parts = path.split('/')
            if len(parts) > 1:
                key = f"{parts[0]}/{parts[1]}" if len(parts) > 1 else parts[0]
            else:
                key = parts[0] if parts else 'root'
            
            dir_map[key]['files'] += 1
            dir_map[key]['lines'] += file_data.get('lines', 0)
            if file_data.get('symbols'):
                dir_map[key]['symbols'] += len(file_data['symbols'])
            if file_data.get('language'):
                dir_map[key]['languages'].add(file_data['language'])
            dir_map[key]['file_paths'].append(path)
        
        # 构建组件信息
        components_info = []
        for comp_name, comp_data in sorted(dir_map.items(), key=lambda x: x[1]['lines'], reverse=True)[:15]:
            components_info.append({
                'name': comp_name,
                'files': comp_data['files'],
                'lines': comp_data['lines'],
                'symbols': comp_data['symbols'],
                'languages': list(comp_data['languages']),
                'sample_files': comp_data['file_paths'][:5]
            })
        
        # 构建上下文
        context = f"""
## 项目基本信息
- 项目名称：{repo_name}
- 代码文件数：{statistics['total_files']}
- 总代码行数：{statistics['total_lines']}
- 函数数量：{statistics['total_functions']}
- 类数量：{statistics['total_classes']}
- 使用语言：{', '.join(statistics['languages'].keys())}

## 主要组件结构
"""
        for comp in components_info:
            context += f"""
### {comp['name']}
- 文件数：{comp['files']}
- 代码行数：{comp['lines']}
- 符号数：{comp['symbols']}
- 使用语言：{', '.join(comp['languages'])}
- 示例文件：{', '.join(comp['sample_files'][:3])}
"""
        
        # 添加主要文件信息（使用智能识别）
        context += "\n## 主要文件（按重要性排序）\n"
        key_files = self._identify_key_files(repo_path)
        
        # 按类型分组显示
        file_types = {}
        for key_file in key_files[:20]:  # 最多显示 20 个
            file_type = key_file['type']
            if file_type not in file_types:
                file_types[file_type] = []
            file_types[file_type].append(key_file)
        
        # 按重要性顺序显示
        type_order = ['readme', 'entry', 'config', 'core', 'build', 'doc', 'test']
        for file_type in type_order:
            if file_type in file_types:
                context += f"\n### {file_type.upper()} 文件\n"
                for key_file in file_types[file_type][:5]:  # 每种类型最多 5 个
                    context += f"- {key_file['path']} (重要性: {key_file['importance']})\n"
        
        # 添加主要符号
        context += "\n## 主要代码符号\n"
        symbol_count = 0
        for file_data in analyzed_files[:10]:
            symbols = file_data.get('symbols', [])
            for symbol in symbols[:2]:
                if symbol_count >= 15:
                    break
                context += f"- {symbol['type'].capitalize()} `{symbol['name']}` in {file_data['file_path']}\n"
                symbol_count += 1
            if symbol_count >= 15:
                break
        
        return context
    
    def _generate_wiki_content_with_llm(
        self,
        context: str,
        repo_name: str,
        statistics: Dict
    ) -> Dict:
        """使用 LLM 生成所有 Wiki 内容"""
        import requests
        from app.config.settings import settings
        
        # 构建综合 Prompt
        prompt = f"""请基于以下代码仓库信息，生成 Wiki 页面的所有内容。请以 JSON 格式返回，包含以下字段：

{context}

请生成以下内容（JSON 格式）：

1. project_overview: 项目概述（200-300字），包括项目简介、主要功能、技术栈、项目结构概述
2. what_is_project: 项目是什么（100-150字），简洁描述项目的定位和核心价值
3. core_components: 核心组件列表（前10个最重要的组件），每个组件包含：
   - name: 组件名称
   - purpose: AI 分析的组件职责说明（50-100字）
4. value_propositions: 核心价值主张列表（3-5个），每个包含：
   - feature: 特性名称
   - description: AI 分析的特性描述（50-100字）
5. key_features: 主要特性列表（5-8个），每个包含：
   - name: 特性名称
   - description: AI 分析的特性说明（50-100字）

要求：
- 所有内容必须基于实际代码分析，不要编造
- 语言简洁专业
- 重点突出核心功能和价值
- 返回纯 JSON 格式，不要包含 markdown 代码块标记

返回格式示例：
{{
  "project_overview": "...",
  "what_is_project": "...",
  "core_components": [
    {{"name": "...", "purpose": "..."}}
  ],
  "value_propositions": [
    {{"feature": "...", "description": "..."}}
  ],
  "key_features": [
    {{"name": "...", "description": "..."}}
  ]
}}
"""
        
        # 调用 LLM
        response = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": settings.CODE_LLM_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=300  # 5分钟超时
        )
        response.raise_for_status()
        result = response.json()
        content = result.get("response", "").strip()
        
        if not content:
            raise Exception("LLM 返回空内容")
        
        # 解析 JSON（移除可能的 markdown 代码块标记）
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        import json
        try:
            wiki_data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"LLM 返回的 JSON 解析失败: {e}, 内容前500字符: {content[:500]}")
            raise Exception(f"LLM 返回的 JSON 格式错误: {str(e)}")
        
        # 验证必需字段
        required_fields = ['project_overview', 'what_is_project', 'core_components', 'value_propositions', 'key_features']
        for field in required_fields:
            if field not in wiki_data:
                raise Exception(f"LLM 返回数据缺少必需字段: {field}")
        
        # 验证字段类型
        if not isinstance(wiki_data.get('core_components'), list):
            raise Exception("core_components 必须是数组")
        if not isinstance(wiki_data.get('value_propositions'), list):
            raise Exception("value_propositions 必须是数组")
        if not isinstance(wiki_data.get('key_features'), list):
            raise Exception("key_features 必须是数组")
        
        logger.info(f"Wiki 内容生成成功: project_overview={len(wiki_data.get('project_overview', ''))} 字符, "
                   f"components={len(wiki_data.get('core_components', []))}, "
                   f"value_props={len(wiki_data.get('value_propositions', []))}, "
                   f"features={len(wiki_data.get('key_features', []))}")
        return wiki_data
    
    def _extract_module_structure(self, analyzed_files: List[Dict], repo_path: str) -> Dict:
        """提取模块结构信息（增强版：包含模块职责、依赖关系）"""
        module_map = defaultdict(lambda: {
            'files': [],
            'lines': 0,
            'symbols': 0,
            'languages': set(),
            'dependencies': set(),
            'api_endpoints': [],
            'service_methods': [],
            'imports': set(),
            'exports': set()
        })
        
        # 第一遍：收集模块基本信息
        for file_data in analyzed_files:
            path = file_data['file_path']
            # 提取模块名（第一级或第二级目录）
            parts = path.split('/')
            if len(parts) > 1:
                module_name = parts[0] if len(parts) == 2 else f"{parts[0]}/{parts[1]}"
            else:
                module_name = 'root'
            
            module_map[module_name]['files'].append(path)
            module_map[module_name]['lines'] += file_data.get('lines', 0)
            if file_data.get('symbols'):
                module_map[module_name]['symbols'] += len(file_data['symbols'])
            if file_data.get('language'):
                module_map[module_name]['languages'].add(file_data['language'])
            
            # 收集导入关系
            for imp in file_data.get('imports', []):
                module_map[module_name]['imports'].add(imp.get('module', ''))
            
            # 收集 API 端点
            if '/api/' in path or '/routes/' in path:
                for symbol in file_data.get('symbols', []):
                    if symbol.get('type') in ['function', 'method']:
                        module_map[module_name]['api_endpoints'].append({
                            'name': symbol.get('name', ''),
                            'file': path,
                            'line': symbol.get('line', 0)
                        })
            
            # 收集服务方法
            if '/service' in path.lower() or '/services/' in path:
                for symbol in file_data.get('symbols', []):
                    if symbol.get('type') in ['function', 'method']:
                        module_map[module_name]['service_methods'].append({
                            'name': symbol.get('name', ''),
                            'file': path,
                            'line': symbol.get('line', 0)
                        })
        
        # 第二遍：分析模块职责和依赖关系
        modules = []
        for name, data in sorted(module_map.items(), key=lambda x: x[1]['lines'], reverse=True):
            # 推断模块职责
            responsibilities = self._infer_module_responsibilities(name, data, analyzed_files)
            
            # 分析模块依赖关系
            module_dependencies = self._analyze_module_dependencies(name, data, analyzed_files, module_map)
            
            modules.append({
                'name': name,
                'files_count': len(data['files']),
                'lines': data['lines'],
                'symbols': data['symbols'],
                'languages': list(data['languages']),
                'sample_files': data['files'][:5],
                'responsibilities': responsibilities,
                'dependencies': module_dependencies,
                'api_endpoints_count': len(data['api_endpoints']),
                'service_methods_count': len(data['service_methods'])
            })
        
        return {'modules': modules}
    
    def _infer_module_responsibilities(self, module_name: str, module_data: Dict, analyzed_files: List[Dict]) -> List[str]:
        """推断模块职责"""
        responsibilities = []
        
        # 基于模块名称推断
        module_lower = module_name.lower()
        if 'api' in module_lower or 'route' in module_lower:
            responsibilities.append('API 路由处理')
        if 'service' in module_lower:
            responsibilities.append('业务逻辑处理')
        if 'model' in module_lower or 'entity' in module_lower:
            responsibilities.append('数据模型定义')
        if 'view' in module_lower or 'component' in module_lower:
            responsibilities.append('前端视图/组件')
        if 'util' in module_lower or 'helper' in module_lower:
            responsibilities.append('工具函数')
        if 'config' in module_lower or 'setting' in module_lower:
            responsibilities.append('配置管理')
        if 'test' in module_lower or 'spec' in module_lower:
            responsibilities.append('测试代码')
        
        # 基于文件内容推断
        if module_data.get('api_endpoints'):
            responsibilities.append('API 端点定义')
        if module_data.get('service_methods'):
            responsibilities.append('服务方法实现')
        
        # 基于导入关系推断
        imports = module_data.get('imports', set())
        if any('db' in imp.lower() or 'database' in imp.lower() for imp in imports):
            responsibilities.append('数据访问')
        if any('http' in imp.lower() or 'request' in imp.lower() for imp in imports):
            responsibilities.append('HTTP 请求处理')
        
        return list(set(responsibilities)) if responsibilities else ['通用功能']
    
    def _analyze_module_dependencies(self, module_name: str, module_data: Dict, analyzed_files: List[Dict], module_map: Dict) -> List[Dict]:
        """分析模块依赖关系"""
        dependencies = []
        
        # 分析导入关系，找出依赖的其他模块
        for file_path in module_data['files']:
            file_data = next((f for f in analyzed_files if f['file_path'] == file_path), None)
            if not file_data:
                continue
            
            for imp in file_data.get('imports', []):
                import_module = imp.get('module', '')
                if not import_module:
                    continue
                
                # 尝试匹配到其他模块
                target_module = self._match_import_to_module(import_module, module_map)
                if target_module and target_module != module_name:
                    # 检查是否已存在
                    if not any(dep['module'] == target_module for dep in dependencies):
                        dependencies.append({
                            'module': target_module,
                            'type': 'import',
                            'count': 1
                        })
                    else:
                        # 增加计数
                        for dep in dependencies:
                            if dep['module'] == target_module:
                                dep['count'] += 1
        
        return dependencies
    
    def _match_import_to_module(self, import_module: str, module_map: Dict) -> Optional[str]:
        """将导入模块匹配到实际模块"""
        # 移除相对路径前缀
        import_module = import_module.lstrip('./')
        
        # 尝试精确匹配
        for module_name in module_map.keys():
            if import_module.startswith(module_name) or module_name in import_module:
                return module_name
        
        # 尝试部分匹配（第一级目录）
        import_parts = import_module.split('/')
        if import_parts:
            first_part = import_parts[0]
            for module_name in module_map.keys():
                if module_name.startswith(first_part) or first_part in module_name:
                    return module_name
        
        return None
    
    def _extract_dependency_info(self, repo_path: str) -> Dict:
        """提取依赖信息（从 package.json, requirements.txt, Cargo.toml 等）"""
        dependency_info = {
            'python': [],
            'javascript': [],
            'rust': [],
            'java': [],
            'other': []
        }
        
        # Python: requirements.txt, setup.py, pyproject.toml
        for dep_file in ['requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile']:
            file_path = os.path.join(repo_path, dep_file)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if dep_file == 'requirements.txt':
                            # 简单解析 requirements.txt
                            for line in content.split('\n'):
                                line = line.strip()
                                if line and not line.startswith('#'):
                                    dep = line.split('==')[0].split('>=')[0].split('<=')[0].strip()
                                    if dep:
                                        dependency_info['python'].append(dep)
                        elif dep_file in ['setup.py', 'pyproject.toml']:
                            # 提取依赖（简化版）
                            import re
                            deps = re.findall(r'["\']([^"\']+)["\']', content)
                            dependency_info['python'].extend(deps[:20])  # 限制数量
                except Exception as e:
                    logger.warning(f"解析依赖文件失败: {file_path}, {e}")
        
        # JavaScript: package.json
        package_json = os.path.join(repo_path, 'package.json')
        if os.path.exists(package_json):
            try:
                import json
                with open(package_json, 'r', encoding='utf-8', errors='ignore') as f:
                    data = json.load(f)
                    deps = data.get('dependencies', {})
                    dev_deps = data.get('devDependencies', {})
                    dependency_info['javascript'] = list(deps.keys())[:30] + list(dev_deps.keys())[:20]
            except Exception as e:
                logger.warning(f"解析 package.json 失败: {e}")
        
        # Rust: Cargo.toml
        cargo_toml = os.path.join(repo_path, 'Cargo.toml')
        if os.path.exists(cargo_toml):
            try:
                with open(cargo_toml, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    import re
                    # 简单提取依赖
                    deps = re.findall(r'\[dependencies\.([^\]]+)\]', content)
                    dependency_info['rust'].extend(deps[:30])
            except Exception as e:
                logger.warning(f"解析 Cargo.toml 失败: {e}")
        
        return dependency_info
    
    def _extract_deployment_info(self, repo_path: str) -> Dict:
        """提取部署信息（Dockerfile, docker-compose.yml, 配置文件等）"""
        deployment_info = {
            'dockerfile': None,
            'docker_compose': None,
            'config_files': [],
            'scripts': []
        }
        
        # 查找 Dockerfile
        for dockerfile in ['Dockerfile', 'Dockerfile.prod', 'Dockerfile.dev']:
            file_path = os.path.join(repo_path, dockerfile)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        deployment_info['dockerfile'] = f.read()[:2000]  # 限制长度
                        break
                except Exception as e:
                    logger.warning(f"读取 Dockerfile 失败: {e}")
        
        # 查找 docker-compose.yml
        for compose_file in ['docker-compose.yml', 'docker-compose.yaml', 'compose.yml']:
            file_path = os.path.join(repo_path, compose_file)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        deployment_info['docker_compose'] = f.read()[:2000]
                        break
                except Exception as e:
                    logger.warning(f"读取 docker-compose 失败: {e}")
        
        # 查找配置文件
        config_patterns = ['.env.example', 'config.toml', 'config.yaml', 'config.yml', 'settings.py']
        for pattern in config_patterns:
            file_path = os.path.join(repo_path, pattern)
            if os.path.exists(file_path):
                deployment_info['config_files'].append(pattern)
        
        # 查找启动脚本
        script_patterns = ['start.sh', 'run.sh', 'deploy.sh', 'build.sh']
        for pattern in script_patterns:
            file_path = os.path.join(repo_path, pattern)
            if os.path.exists(file_path):
                deployment_info['scripts'].append(pattern)
        
        return deployment_info
    
    def _extract_readme_content(self, repo_path: str) -> str:
        """提取 README 内容（优先提取快速开始相关部分）"""
        readme_files = ['README.md', 'README.txt', 'README.rst', 'README', 'README_zh.md', 'README_zh_CN.md']
        for readme_file in readme_files:
            file_path = os.path.join(repo_path, readme_file)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                        # 优先提取"快速开始"、"安装"、"运行"等相关章节
                        getting_started_sections = []
                        lines = content.split('\n')
                        in_getting_started = False
                        current_section = []
                        
                        # 查找相关章节标题
                        section_keywords = [
                            'quick start', '快速开始', 'getting started', 'installation', 
                            '安装', 'setup', '设置', 'run', '运行', 'usage', '使用',
                            'prerequisites', '前置要求', 'requirements', '依赖'
                        ]
                        
                        for i, line in enumerate(lines):
                            line_lower = line.lower().strip()
                            # 检查是否是章节标题
                            is_section_header = (
                                line_lower.startswith('#') or 
                                line_lower.startswith('##') or
                                line_lower.startswith('###')
                            ) and any(keyword in line_lower for keyword in section_keywords)
                            
                            if is_section_header:
                                if current_section:
                                    getting_started_sections.extend(current_section)
                                current_section = [line]
                                in_getting_started = True
                            elif in_getting_started:
                                # 如果遇到新的顶级章节，停止收集
                                if line_lower.startswith('# ') and not any(keyword in line_lower for keyword in section_keywords):
                                    break
                                current_section.append(line)
                        
                        if current_section:
                            getting_started_sections.extend(current_section)
                        
                        # 如果找到了相关章节，优先使用；否则使用前8000字符
                        if getting_started_sections:
                            result = '\n'.join(getting_started_sections)
                            logger.info(f"从 README 提取到快速开始相关章节，长度: {len(result)} 字符")
                            return result[:8000]  # 增加长度限制
                        else:
                            logger.info(f"未找到快速开始章节，使用 README 前8000字符")
                            return content[:8000]  # 增加长度限制
                            
                except Exception as e:
                    logger.warning(f"读取 README 失败: {e}")
        return ""
    
    def _identify_key_files(self, repo_path: str) -> List[Dict]:
        """
        识别关键文件（扩展版：支持多种文件类型）
        
        Args:
            repo_path: 仓库路径
            
        Returns:
            关键文件列表，格式: [{'path': str, 'type': str, 'importance': int}]
        """
        key_files = []
        
        # 入口文件模式（按语言类型）
        entry_file_patterns = {
            'python': ['main.py', 'app.py', '__init__.py', 'manage.py', 'run.py', 'server.py', 'wsgi.py', 'asgi.py'],
            'javascript': ['index.js', 'index.ts', 'server.js', 'app.js', 'main.js', 'index.mjs'],
            'typescript': ['index.ts', 'index.tsx', 'server.ts', 'app.ts', 'main.ts'],
            'rust': ['main.rs', 'lib.rs'],
            'java': ['Application.java', 'Main.java', 'App.java'],
            'go': ['main.go'],
            'csharp': ['Program.cs', 'Startup.cs'],
        }
        
        # 构建文件模式
        build_file_patterns = [
            'Makefile', 'CMakeLists.txt', 'build.gradle', 'pom.xml', 'build.xml',
            'package.json', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
            'requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile',
            'Cargo.toml', 'Cargo.lock',
            'go.mod', 'go.sum',
            'composer.json', 'composer.lock',
            '.dockerignore', 'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
            '.github/workflows', '.gitlab-ci.yml', 'Jenkinsfile',
            'tsconfig.json', 'webpack.config.js', 'vite.config.js', 'rollup.config.js',
            'CMakeLists.txt', 'Makefile.am', 'Makefile.in'
        ]
        
        # 文档文件模式
        doc_file_patterns = [
            'docs/', '*.md', '*.rst', '*.txt', '*.adoc',
            'CHANGELOG', 'LICENSE', 'AUTHORS', 'CONTRIBUTING'
        ]
        
        # 遍历所有文件
        for root, dirs, files in os.walk(repo_path):
            # 排除忽略目录
            dirs[:] = [d for d in dirs if d not in self.IGNORE_PATTERNS]
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, repo_path)
                
                # 检测文件类型
                file_type, importance = self._score_file_importance(rel_path, file, entry_file_patterns, build_file_patterns, doc_file_patterns)
                
                if file_type:
                    key_files.append({
                        'path': rel_path,
                        'type': file_type,
                        'importance': importance
                    })
        
        # 按重要性排序
        key_files.sort(key=lambda x: x['importance'], reverse=True)
        
        return key_files
    
    def _score_file_importance(self, rel_path: str, file_name: str, entry_patterns: Dict, build_patterns: List[str], doc_patterns: List[str]) -> tuple:
        """
        评分文件重要性
        
        Args:
            rel_path: 相对路径
            file_name: 文件名
            entry_patterns: 入口文件模式字典
            build_patterns: 构建文件模式列表
            doc_patterns: 文档文件模式列表
            
        Returns:
            (文件类型, 重要性分数)
        """
        rel_path_lower = rel_path.lower()
        file_name_lower = file_name.lower()
        
        # README 文件：10 分
        if file_name_lower.startswith('readme'):
            return ('readme', 10)
        
        # 入口文件：9 分
        # 检测语言类型
        language = self.parser_service.detect_language(rel_path)
        if language and language in entry_patterns:
            if file_name in entry_patterns[language]:
                return ('entry', 9)
        
        # 配置文件：8 分
        config_files = [
            'package.json', 'requirements.txt', 'Cargo.toml', '.env', 'config.yaml',
            'config.yml', 'settings.py', 'config.py', 'config.toml', 'pyproject.toml',
            'tsconfig.json', 'webpack.config.js', 'vite.config.js', 'go.mod',
            'composer.json', 'pom.xml', 'build.gradle'
        ]
        if file_name in config_files or any(pattern in rel_path_lower for pattern in ['.env', 'config.', 'settings.']):
            return ('config', 8)
        
        # 核心服务文件：8 分（包含 service, core, main 关键词）
        if any(keyword in rel_path_lower for keyword in ['service', 'core', 'main', 'app']):
            # 排除测试文件
            if 'test' not in rel_path_lower and 'spec' not in rel_path_lower:
                return ('core', 8)
        
        # 构建文件：7 分
        if any(pattern in rel_path_lower for pattern in build_patterns):
            return ('build', 7)
        
        # 文档文件：6 分
        if any(pattern in rel_path_lower for pattern in doc_patterns) or file_name_lower.endswith(('.md', '.rst', '.txt', '.adoc')):
            return ('doc', 6)
        
        # 测试文件：3 分
        if any(keyword in rel_path_lower for keyword in ['test', 'spec', '__test__', '__tests__']):
            return ('test', 3)
        
        # 其他文件：1 分（不返回，只返回重要文件）
        return (None, 1)
    
    def _extract_api_endpoints_detail(self, file_data: Dict, repo_path: str) -> List[Dict]:
        """提取 API 端点详细信息（路径、方法、参数、文档字符串）"""
        endpoints = []
        file_path = file_data.get('file_path', '')
        full_path = os.path.join(repo_path, file_path) if file_path else None
        
        if not full_path or not os.path.exists(full_path):
            return endpoints
        
        language = file_data.get('language', '')
        
        try:
            if language == 'python':
                # 使用 AST 解析 Python 文件
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # 检查是否有路由装饰器
                        http_method = None
                        route_path = None
                        docstring = ast.get_docstring(node) or ''
                        
                        for decorator in node.decorator_list:
                            # 处理 @router.get("/path") 或 @app.get("/path")
                            if isinstance(decorator, ast.Call):
                                if hasattr(decorator.func, 'attr'):
                                    method = decorator.func.attr.lower()
                                    if method in ['get', 'post', 'put', 'delete', 'patch']:
                                        http_method = method.upper()
                                        # 提取路径参数
                                        if decorator.args:
                                            if isinstance(decorator.args[0], ast.Constant):
                                                route_path = decorator.args[0].value
                                            elif isinstance(decorator.args[0], ast.Str):  # Python < 3.8
                                                route_path = decorator.args[0].s
                                        
                                        # 提取函数参数
                                        params = []
                                        for arg in node.args.args:
                                            param_name = arg.arg
                                            param_type = None
                                            if arg.annotation:
                                                if isinstance(arg.annotation, ast.Name):
                                                    param_type = arg.annotation.id
                                                elif isinstance(arg.annotation, ast.Constant):
                                                    param_type = str(arg.annotation.value)
                                            params.append({
                                                'name': param_name,
                                                'type': param_type
                                            })
                                        
                                        endpoints.append({
                                            'method': http_method,
                                            'path': route_path or '',
                                            'function_name': node.name,
                                            'parameters': params,
                                            'docstring': docstring[:200],  # 限制长度
                                            'line': node.lineno,
                                            'file_path': file_path
                                        })
                                        break
                            
                            # 处理 @router.route("/path", methods=["GET"])
                            elif isinstance(decorator, ast.Call) and hasattr(decorator.func, 'attr') and decorator.func.attr == 'route':
                                if decorator.args:
                                    if isinstance(decorator.args[0], ast.Constant):
                                        route_path = decorator.args[0].value
                                    elif isinstance(decorator.args[0], ast.Str):
                                        route_path = decorator.args[0].s
                                    
                                    # 提取 methods 参数
                                    for keyword in decorator.keywords:
                                        if keyword.arg == 'methods' and isinstance(keyword.value, ast.List):
                                            if keyword.value.elts:
                                                method_node = keyword.value.elts[0]
                                                if isinstance(method_node, ast.Constant):
                                                    http_method = method_node.value.upper()
                                                elif isinstance(method_node, ast.Str):
                                                    http_method = method_node.s.upper()
                                    
                                    if route_path and http_method:
                                        endpoints.append({
                                            'method': http_method,
                                            'path': route_path,
                                            'function_name': node.name,
                                            'parameters': [],
                                            'docstring': docstring[:200],
                                            'line': node.lineno,
                                            'file_path': file_path
                                        })
                                        break
                                        
        except Exception as e:
            logger.warning(f"提取 API 端点详情失败: {file_path}, {e}")
        
        return endpoints
    
    def _extract_service_methods_detail(self, file_data: Dict, repo_path: str) -> List[Dict]:
        """提取服务方法详细信息"""
        methods = []
        file_path = file_data.get('file_path', '')
        full_path = os.path.join(repo_path, file_path) if file_path else None
        
        if not full_path or not os.path.exists(full_path):
            return methods
        
        language = file_data.get('language', '')
        
        try:
            if language == 'python':
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # 检查是否在类中（服务方法通常在类中）
                        is_method = False
                        class_name = None
                        for parent in ast.walk(tree):
                            if isinstance(parent, ast.ClassDef):
                                for child in parent.body:
                                    if child == node:
                                        is_method = True
                                        class_name = parent.name
                                        break
                        
                        if is_method or 'service' in file_path.lower():
                            docstring = ast.get_docstring(node) or ''
                            params = []
                            for arg in node.args.args:
                                if arg.arg != 'self':  # 排除 self
                                    params.append({
                                        'name': arg.arg,
                                        'type': None
                                    })
                            
                            methods.append({
                                'class_name': class_name,
                                'method_name': node.name,
                                'parameters': params,
                                'docstring': docstring[:200],
                                'line': node.lineno,
                                'file_path': file_path
                            })
                            
        except Exception as e:
            logger.warning(f"提取服务方法详情失败: {file_path}, {e}")
        
        return methods
    
    def _extract_architecture_details(self, analyzed_files: List[Dict], repo_path: str) -> Dict:
        """提取详细的架构信息（API路由、服务文件、前端组件等）"""
        architecture = {
            'api_routes': [],
            'api_endpoints_detail': [],  # 新增：详细的 API 端点信息
            'service_files': [],
            'service_methods_detail': [],  # 新增：详细的服务方法信息
            'task_files': [],
            'frontend_views': [],
            'frontend_components': [],
            'storage_systems': [],
            'three_tier_structure': {}
        }
        
        # 提取 API 路由文件和详细信息
        for file_data in analyzed_files:
            path = file_data['file_path']
            if '/api/' in path or '/routes/' in path or '/endpoints/' in path:
                if file_data.get('language') in ['python', 'javascript', 'typescript']:
                    # 统计路由数量
                    route_count = 0
                    if file_data.get('symbols'):
                        for symbol in file_data['symbols']:
                            if symbol['type'] in ['function', 'method']:
                                route_count += 1
                    
                    architecture['api_routes'].append({
                        'path': path,
                        'lines': file_data.get('lines', 0),
                        'route_count': route_count,
                        'language': file_data.get('language', '')
                    })
                    
                    # 提取详细的 API 端点信息
                    endpoints = self._extract_api_endpoints_detail(file_data, repo_path)
                    architecture['api_endpoints_detail'].extend(endpoints)
        
        # 提取服务文件和详细信息
        for file_data in analyzed_files:
            path = file_data['file_path']
            if '/service' in path.lower() or '/services/' in path:
                if file_data.get('language') in ['python', 'javascript', 'typescript']:
                    architecture['service_files'].append({
                        'path': path,
                        'lines': file_data.get('lines', 0),
                        'symbols_count': len(file_data.get('symbols', [])),
                        'language': file_data.get('language', '')
                    })
                    
                    # 提取详细的服务方法信息
                    methods = self._extract_service_methods_detail(file_data, repo_path)
                    architecture['service_methods_detail'].extend(methods)
        
        # 提取服务文件
        for file_data in analyzed_files:
            path = file_data['file_path']
            if '/service' in path.lower() or '/services/' in path:
                if file_data.get('language') in ['python', 'javascript', 'typescript']:
                    architecture['service_files'].append({
                        'path': path,
                        'lines': file_data.get('lines', 0),
                        'symbols_count': len(file_data.get('symbols', [])),
                        'language': file_data.get('language', '')
                    })
        
        # 提取任务文件
        for file_data in analyzed_files:
            path = file_data['file_path']
            if '/task' in path.lower() or '/tasks/' in path:
                if file_data.get('language') in ['python', 'javascript', 'typescript']:
                    architecture['task_files'].append({
                        'path': path,
                        'lines': file_data.get('lines', 0),
                        'language': file_data.get('language', '')
                    })
        
        # 提取前端视图和组件
        for file_data in analyzed_files:
            path = file_data['file_path']
            if '/view' in path.lower() or '/views/' in path:
                if file_data.get('language') in ['vue', 'javascript', 'typescript', 'jsx', 'tsx']:
                    architecture['frontend_views'].append({
                        'path': path,
                        'lines': file_data.get('lines', 0),
                        'language': file_data.get('language', '')
                    })
            elif '/component' in path.lower() or '/components/' in path:
                if file_data.get('language') in ['vue', 'javascript', 'typescript', 'jsx', 'tsx']:
                    architecture['frontend_components'].append({
                        'path': path,
                        'lines': file_data.get('lines', 0),
                        'language': file_data.get('language', '')
                    })
        
        # 识别存储系统（从依赖和配置推断）
        storage_indicators = {
            'MySQL': ['mysql', 'sqlalchemy', 'pymysql', 'mysqldb'],
            'PostgreSQL': ['postgresql', 'psycopg2', 'pg'],
            'Redis': ['redis', 'celery'],
            'MongoDB': ['mongo', 'pymongo'],
            'OpenSearch': ['opensearch', 'elasticsearch'],
            'NebulaGraph': ['nebula', 'nebula3'],
            'MinIO': ['minio', 's3'],
            'SQLite': ['sqlite']
        }
        
        # 从依赖信息推断（会在调用时传入）
        
        # 识别三层架构
        has_frontend = len(architecture['frontend_views']) > 0 or len(architecture['frontend_components']) > 0
        has_backend = len(architecture['api_routes']) > 0 or len(architecture['service_files']) > 0
        has_data = len(architecture['service_files']) > 0  # 服务层通常包含数据访问
        
        architecture['three_tier_structure'] = {
            'has_frontend': has_frontend,
            'has_backend': has_backend,
            'has_data_layer': has_data,
            'frontend_files': len(architecture['frontend_views']) + len(architecture['frontend_components']),
            'backend_files': len(architecture['api_routes']) + len(architecture['service_files']),
            'task_files': len(architecture['task_files'])
        }
        
        return architecture
    
    def _generate_system_architecture_llm(
        self,
        analyzed_files: List[Dict],
        module_structure: Dict,
        repo_name: str,
        statistics: Dict,
        repo_path: str
    ) -> Dict:
        """使用 LLM 生成详细的系统架构说明（类似 DeepWiki）"""
        import requests
        from app.config.settings import settings
        
        # 提取详细的架构信息
        arch_details = self._extract_architecture_details(analyzed_files, repo_path)
        
        # 构建详细的上下文
        context = f"""
## 项目基本信息

项目名称: {repo_name}
总文件数: {statistics['total_files']}
总代码行数: {statistics['total_lines']}
使用语言: {', '.join(statistics['languages'].keys())}

## 三层架构结构

前端层: {arch_details['three_tier_structure']['has_frontend']} ({arch_details['three_tier_structure']['frontend_files']} 个文件)
后端层: {arch_details['three_tier_structure']['has_backend']} ({arch_details['three_tier_structure']['backend_files']} 个文件)
数据层: {arch_details['three_tier_structure']['has_data_layer']}
异步任务: {arch_details['three_tier_structure']['task_files']} 个任务文件

## API 路由文件（前20个）

"""
        for route in sorted(arch_details['api_routes'], key=lambda x: x['lines'], reverse=True)[:20]:
            context += f"- {route['path']}: {route['lines']} 行, {route['route_count']} 个路由, {route['language']}\n"
        
        context += "\n## 服务文件（前20个）\n"
        for service in sorted(arch_details['service_files'], key=lambda x: x['lines'], reverse=True)[:20]:
            context += f"- {service['path']}: {service['lines']} 行, {service['symbols_count']} 个符号, {service['language']}\n"
        
        context += "\n## 异步任务文件\n"
        for task in sorted(arch_details['task_files'], key=lambda x: x['lines'], reverse=True)[:10]:
            context += f"- {task['path']}: {task['lines']} 行, {task['language']}\n"
        
        context += "\n## 前端视图文件（前15个）\n"
        for view in sorted(arch_details['frontend_views'], key=lambda x: x['lines'], reverse=True)[:15]:
            context += f"- {view['path']}: {view['lines']} 行, {view['language']}\n"
        
        context += "\n## 前端组件文件（前15个）\n"
        for comp in sorted(arch_details['frontend_components'], key=lambda x: x['lines'], reverse=True)[:15]:
            context += f"- {comp['path']}: {comp['lines']} 行, {comp['language']}\n"
        
        context += "\n## 主要模块结构\n"
        for module in module_structure.get('modules', [])[:20]:
            context += f"""
### {module['name']}
- 文件数: {module['files_count']}
- 代码行数: {module['lines']}
- 符号数: {module['symbols']}
- 使用语言: {', '.join(module['languages'])}
- 示例文件: {', '.join(module['sample_files'][:3])}
"""
        
        # 添加详细的 API 端点信息
        context += "\n## API 端点详细信息（前30个）\n"
        for endpoint in arch_details.get('api_endpoints_detail', [])[:30]:
            context += f"""
- {endpoint['method']} {endpoint['path']} ({endpoint['file_path']}:{endpoint['line']})
  - 函数: {endpoint['function_name']}
  - 参数: {', '.join([p['name'] for p in endpoint.get('parameters', [])])}
  - 说明: {endpoint.get('docstring', '')[:100]}
"""
        
        # 添加详细的服务方法信息
        context += "\n## 服务方法详细信息（前30个）\n"
        for method in arch_details.get('service_methods_detail', [])[:30]:
            context += f"""
- {method.get('class_name', '')}.{method['method_name']} ({method['file_path']}:{method['line']})
  - 参数: {', '.join([p['name'] for p in method.get('parameters', [])])}
  - 说明: {method.get('docstring', '')[:100]}
"""
        
        # 生成基础 Mermaid 图表（作为参考）
        base_architecture_diagram = self._generate_mermaid_architecture_diagram(arch_details, statistics)
        base_data_flow_diagram = self._generate_mermaid_data_flow_diagram(arch_details)
        base_api_diagram = self._generate_mermaid_api_diagram(arch_details)
        
        prompt = f"""请基于以下代码仓库的**非常详细**的架构信息，生成**极其详细和深入**的系统架构说明，完全参考 DeepWiki 的风格和深度。请以 JSON 格式返回：

{context}

## 基础架构图表（作为参考，请优化和扩展）

### 系统架构图
{base_architecture_diagram}

### 数据流图
{base_data_flow_diagram}

### API 架构图
{base_api_diagram}

请生成以下内容（JSON 格式），要求**非常详细和专业**：

1. three_tier_architecture: 三层架构详细说明（300-400字），包括：
   - 客户端层的组织方式和技术栈
   - 应用层的服务组织和API设计
   - 数据服务层的存储系统选择

2. functional_subsystems_table: 功能子系统表格，每个子系统包含：
   - subsystem_name: 子系统名称（如 "Document Processing", "Question Answering"）
   - frontend_path: 前端路径（如 "src/views/document/"）
   - backend_route: 后端路由（如 "app/api/v1/document.py"）
   - service_files: 服务文件列表（如 ["document_service.py"]）
   - key_responsibilities: 关键职责说明（100-150字）

3. architectural_patterns: 架构模式说明（400-500字），包括：
   - polyglot_persistence: 多语言持久化策略说明
   - asynchronous_processing: 异步处理架构说明
   - service_layer: 服务层模式说明
   - real_time_communication: 实时通信模式说明（如果有 WebSocket）

4. storage_systems_table: 存储系统表格，每个存储系统包含：
   - storage_system: 存储系统名称（如 "MySQL", "OpenSearch"）
   - data_types: 数据类型说明
   - access_pattern: 访问模式说明
   - key_use_cases: 关键用例说明

5. key_architectural_decisions: 关键架构决策列表，每个决策包含：
   - decision: 决策名称
   - rationale: 决策理由（100-150字）
   - impact: 影响说明（50-100字）

6. api_architecture: API 架构说明（200-300字），包括：
   - endpoint_count: 端点数量统计
   - http_methods: HTTP 方法分布
   - websocket_endpoints: WebSocket 端点数量（如果有）

7. scalability_considerations: 系统可扩展性考虑（200-300字）

8. mermaid_architecture_diagram: Mermaid 格式的系统架构图代码（基于基础图表优化和扩展）
9. mermaid_data_flow_diagram: Mermaid 格式的数据流图代码（基于基础图表优化和扩展）
10. mermaid_api_diagram: Mermaid 格式的 API 架构图代码（基于基础图表优化和扩展）

要求：
- **所有内容必须基于实际代码分析，不要编造**
- **语言要非常专业和详细，类似 DeepWiki 的风格**
- **重点突出架构设计、技术选择和决策理由**
- **表格内容要详细，包含具体的文件路径和职责说明**
- **引用具体的文件路径作为依据**
- **Mermaid 图表要基于实际的 API 端点、服务方法、组件关系生成，可以优化和扩展基础图表**

返回格式示例：
{{
  "three_tier_architecture": "...",
  "functional_subsystems_table": [
    {{
      "subsystem_name": "...",
      "frontend_path": "...",
      "backend_route": "...",
      "service_files": ["..."],
      "key_responsibilities": "..."
    }}
  ],
  "architectural_patterns": "...",
  "storage_systems_table": [
    {{
      "storage_system": "...",
      "data_types": "...",
      "access_pattern": "...",
      "key_use_cases": "..."
    }}
  ],
  "key_architectural_decisions": [
    {{
      "decision": "...",
      "rationale": "...",
      "impact": "..."
    }}
  ],
  "api_architecture": "...",
  "scalability_considerations": "...",
  "mermaid_architecture_diagram": "```mermaid\\ngraph TB\\n...\\n```",
  "mermaid_data_flow_diagram": "```mermaid\\nsequenceDiagram\\n...\\n```",
  "mermaid_api_diagram": "```mermaid\\ngraph LR\\n...\\n```"
}}
"""
        
        try:
            response = requests.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.CODE_LLM_MODEL,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=300
            )
            response.raise_for_status()
            result = response.json()
            content = result.get("response", "").strip()
            
            # 解析 JSON
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            import json
            architecture_data = json.loads(content)
            
            logger.info(f"系统架构生成成功: subsystems={len(architecture_data.get('functional_subsystems_table', []))}, "
                       f"decisions={len(architecture_data.get('key_architectural_decisions', []))}")
            return architecture_data
        except Exception as e:
            logger.error(f"生成系统架构失败: {e}")
            return {
                "three_tier_architecture": "系统架构分析失败",
                "functional_subsystems_table": [],
                "architectural_patterns": "",
                "storage_systems_table": [],
                "key_architectural_decisions": [],
                "api_architecture": "",
                "scalability_considerations": "",
                "mermaid_architecture_diagram": "",
                "mermaid_data_flow_diagram": "",
                "mermaid_api_diagram": ""
            }
    
    def _generate_tech_stack_llm(
        self,
        dependency_info: Dict,
        statistics: Dict,
        repo_path: str
    ) -> Dict:
        """使用 LLM 生成技术栈说明"""
        import requests
        from app.config.settings import settings
        
        # 构建上下文
        context = f"""
## 项目技术栈信息

使用语言: {', '.join(statistics['languages'].keys())}

## 依赖信息

"""
        if dependency_info.get('python'):
            context += f"\n### Python 依赖（前20个）\n"
            for dep in dependency_info['python'][:20]:
                context += f"- {dep}\n"
        
        if dependency_info.get('javascript'):
            context += f"\n### JavaScript 依赖（前20个）\n"
            for dep in dependency_info['javascript'][:20]:
                context += f"- {dep}\n"
        
        if dependency_info.get('rust'):
            context += f"\n### Rust 依赖（前20个）\n"
            for dep in dependency_info['rust'][:20]:
                context += f"- {dep}\n"
        
        prompt = f"""请基于以下代码仓库的依赖信息，生成技术栈说明。请以 JSON 格式返回：

{context}

请生成以下内容（JSON 格式）：

1. core_technologies: 核心技术说明（200-300字），描述项目使用的主要技术和框架
2. key_dependencies_table: 关键依赖表格，每个依赖包含：
   - name: 依赖名称
   - purpose: AI 分析的依赖用途说明（30-50字）
   - category: 依赖类别（如 "Web框架", "数据库", "工具库" 等）
3. technology_choices: 技术选择说明（150-200字），解释为什么选择这些技术

要求：
- 所有内容必须基于实际依赖分析，不要编造
- 语言简洁专业
- 重点突出核心技术和技术选择理由

返回格式示例：
{{
  "core_technologies": "...",
  "key_dependencies_table": [
    {{"name": "...", "purpose": "...", "category": "..."}}
  ],
  "technology_choices": "..."
}}
"""
        
        try:
            response = requests.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.CODE_LLM_MODEL,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=300
            )
            response.raise_for_status()
            result = response.json()
            content = result.get("response", "").strip()
            
            # 解析 JSON
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            import json
            tech_stack_data = json.loads(content)
            
            logger.info(f"技术栈生成成功: dependencies={len(tech_stack_data.get('key_dependencies_table', []))}")
            return tech_stack_data
        except Exception as e:
            logger.error(f"生成技术栈失败: {e}")
            return {
                "core_technologies": "技术栈分析失败",
                "key_dependencies_table": [],
                "technology_choices": ""
            }
    
    def _generate_component_relationships_llm(
        self,
        dependencies: Dict,
        module_structure: Dict,
        repo_name: str
    ) -> Dict:
        """使用 LLM 生成组件关系说明"""
        import requests
        from app.config.settings import settings
        
        # 构建上下文
        context = f"""
## 项目组件关系

项目名称: {repo_name}

## 模块列表

"""
        for module in module_structure.get('modules', [])[:15]:
            context += f"- {module['name']}: {module['files_count']} 个文件, {module['lines']} 行代码\n"
        
        # 添加依赖关系信息
        if dependencies.get('nodes'):
            context += "\n## 依赖关系\n"
            context += f"节点数: {len(dependencies.get('nodes', []))}\n"
            context += f"边数: {len(dependencies.get('edges', []))}\n"
        
        prompt = f"""请基于以下代码仓库的模块和依赖信息，生成组件关系说明。请以 JSON 格式返回：

{context}

请生成以下内容（JSON 格式）：

1. service_dependencies: 服务依赖说明（150-200字），描述模块间的依赖关系
2. component_relationships: 组件关系描述（200-300字），解释组件如何协作
3. data_flow: 数据流说明（100-150字），描述数据如何在组件间流动

要求：
- 所有内容必须基于实际代码分析，不要编造
- 语言简洁专业
- 重点突出组件间的协作关系

返回格式示例：
{{
  "service_dependencies": "...",
  "component_relationships": "...",
  "data_flow": "..."
}}
"""
        
        try:
            response = requests.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.CODE_LLM_MODEL,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=300
            )
            response.raise_for_status()
            result = response.json()
            content = result.get("response", "").strip()
            
            # 解析 JSON
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            import json
            relationships_data = json.loads(content)
            
            logger.info(f"组件关系生成成功")
            return relationships_data
        except Exception as e:
            logger.error(f"生成组件关系失败: {e}")
            return {
                "service_dependencies": "组件关系分析失败",
                "component_relationships": "",
                "data_flow": ""
            }
    
    def _generate_deployment_models_llm(
        self,
        deployment_info: Dict,
        repo_path: str,
        repo_name: str
    ) -> Dict:
        """使用 LLM 生成部署模型说明"""
        import requests
        from app.config.settings import settings
        
        # 构建上下文
        context = f"""
## 项目部署信息

项目名称: {repo_name}

"""
        if deployment_info.get('dockerfile'):
            context += f"\n### Dockerfile 内容（前500字符）\n{deployment_info['dockerfile'][:500]}\n"
        
        if deployment_info.get('docker_compose'):
            context += f"\n### Docker Compose 内容（前500字符）\n{deployment_info['docker_compose'][:500]}\n"
        
        if deployment_info.get('config_files'):
            context += f"\n### 配置文件\n{', '.join(deployment_info['config_files'])}\n"
        
        if deployment_info.get('scripts'):
            context += f"\n### 启动脚本\n{', '.join(deployment_info['scripts'])}\n"
        
        prompt = f"""请基于以下代码仓库的部署信息，生成部署模型说明。请以 JSON 格式返回：

{context}

请生成以下内容（JSON 格式）：

1. standalone_server: 独立服务器部署说明（100-150字），描述如何作为独立服务运行
2. docker_deployment: Docker 部署说明（100-150字），描述如何使用 Docker 部署
3. build_features: 构建特性说明（如果有），描述不同的构建选项
4. deployment_steps: 部署步骤列表（3-5个步骤），每个步骤包含：
   - step: 步骤名称
   - description: 步骤说明

要求：
- 所有内容必须基于实际部署文件分析，不要编造
- 语言简洁专业
- 提供清晰的部署指导

返回格式示例：
{{
  "standalone_server": "...",
  "docker_deployment": "...",
  "build_features": "...",
  "deployment_steps": [
    {{"step": "...", "description": "..."}}
  ]
}}
"""
        
        try:
            response = requests.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.CODE_LLM_MODEL,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=300
            )
            response.raise_for_status()
            result = response.json()
            content = result.get("response", "").strip()
            
            # 解析 JSON
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            import json
            deployment_data = json.loads(content)
            
            logger.info(f"部署模型生成成功: steps={len(deployment_data.get('deployment_steps', []))}")
            return deployment_data
        except Exception as e:
            logger.error(f"生成部署模型失败: {e}")
            return {
                "standalone_server": "部署模型分析失败",
                "docker_deployment": "",
                "build_features": "",
                "deployment_steps": []
            }
    
    def _generate_getting_started_llm(
        self,
        readme_content: str,
        dependency_info: Dict,
        repo_path: str,
        repo_name: str
    ) -> Dict:
        """使用 LLM 生成快速开始指南"""
        import requests
        from app.config.settings import settings
        
        # 构建上下文（增加更多信息）
        context = f"""
## 项目信息

项目名称: {repo_name}
项目路径: {repo_path}

## README 内容（前5000字符，包含更多安装和运行信息）

{readme_content[:5000]}

## 依赖信息

"""
        if dependency_info.get('python'):
            deps = dependency_info['python'][:10]  # 只显示前10个依赖
            context += f"\nPython 依赖（{len(dependency_info['python'])} 个）:\n"
            for dep in deps:
                context += f"  - {dep}\n"
        if dependency_info.get('javascript'):
            deps = dependency_info['javascript'][:10]
            context += f"\nJavaScript 依赖（{len(dependency_info['javascript'])} 个）:\n"
            for dep in deps:
                context += f"  - {dep}\n"
        if dependency_info.get('rust'):
            deps = dependency_info['rust'][:10]
            context += f"\nRust 依赖（{len(dependency_info['rust'])} 个）:\n"
            for dep in deps:
                context += f"  - {dep}\n"
        
        # 检查是否有 package.json、requirements.txt、Cargo.toml 等文件
        import os
        has_package_json = os.path.exists(os.path.join(repo_path, 'package.json'))
        has_requirements = os.path.exists(os.path.join(repo_path, 'requirements.txt'))
        has_cargo_toml = os.path.exists(os.path.join(repo_path, 'Cargo.toml'))
        has_dockerfile = os.path.exists(os.path.join(repo_path, 'Dockerfile'))
        has_docker_compose = os.path.exists(os.path.join(repo_path, 'docker-compose.yml')) or os.path.exists(os.path.join(repo_path, 'docker-compose.yaml'))
        
        context += f"""
## 项目配置文件

"""
        if has_package_json:
            context += "- 存在 package.json（Node.js/JavaScript 项目）\n"
        if has_requirements:
            context += "- 存在 requirements.txt（Python 项目）\n"
        if has_cargo_toml:
            context += "- 存在 Cargo.toml（Rust 项目）\n"
        if has_dockerfile:
            context += "- 存在 Dockerfile（支持 Docker 部署）\n"
        if has_docker_compose:
            context += "- 存在 docker-compose.yml（支持 Docker Compose 部署）\n"
        
        prompt = f"""请基于以下代码仓库的 README、依赖信息和项目配置，生成**详细且实用**的快速开始指南。请以 JSON 格式返回：

{context}

请生成以下内容（JSON 格式）：

1. prerequisites: 前置要求列表（至少2-4个），每个包含：
   - item: 要求名称（如 "Node.js 18+"、"Python 3.9+"、"Docker 20.10+"）
   - description: 详细说明（为什么需要、如何安装、如何验证）

2. installation_steps: 安装步骤列表（至少4-6个详细步骤），每个步骤包含：
   - step: 步骤名称（如 "1. 克隆仓库"、"2. 安装依赖"、"3. 配置环境变量"）
   - description: 详细说明（包含具体的命令和操作，例如：git clone xxx、npm install、pip install -r requirements.txt）

3. key_endpoints: 关键端点列表（如果有 API 或 Web 服务），每个包含：
   - endpoint: 端点路径（如 "/api/users"、"/health"）
   - method: HTTP 方法（GET、POST、PUT、DELETE）
   - description: 端点说明（用途、参数、返回值）

4. quick_start_summary: 快速开始总结（150-200字，包含完整的启动流程）

**重要要求**：
- ✅ 必须基于实际的 README 内容和项目配置生成，不要编造
- ✅ 提供**具体的命令和操作步骤**，不要只说"安装依赖"而要说明"运行 npm install"
- ✅ 如果 README 中有启动命令，必须包含在 installation_steps 中
- ✅ 如果项目支持 Docker，必须包含 Docker 启动步骤
- ✅ 语言简洁专业，但内容要详细实用
- ✅ 确保每个步骤都有清晰的操作说明

**示例格式**：
{{
  "prerequisites": [
    {{"item": "Node.js 18+", "description": "需要 Node.js 18 或更高版本。可通过 node --version 检查版本，如未安装请访问 https://nodejs.org 下载安装。"}},
    {{"item": "npm 或 yarn", "description": "Node.js 包管理器，通常随 Node.js 一起安装。可通过 npm --version 检查。"}}
  ],
  "installation_steps": [
    {{"step": "1. 克隆仓库", "description": "使用 git clone 命令克隆仓库：git clone https://github.com/owner/repo.git && cd repo"}},
    {{"step": "2. 安装依赖", "description": "运行 npm install 安装项目依赖：npm install"}},
    {{"step": "3. 配置环境变量", "description": "复制 .env.example 为 .env 并配置必要的环境变量：cp .env.example .env"}},
    {{"step": "4. 启动开发服务器", "description": "运行 npm run dev 启动开发服务器：npm run dev"}}
  ],
  "key_endpoints": [
    {{"endpoint": "/api/health", "method": "GET", "description": "健康检查端点，返回服务状态"}}
  ],
  "quick_start_summary": "快速开始：1) 克隆仓库 git clone xxx，2) 安装依赖 npm install，3) 配置环境变量 cp .env.example .env，4) 启动服务 npm run dev。访问 http://localhost:3000 查看应用。"
}}

返回格式示例：
{{
  "prerequisites": [
    {{"item": "...", "description": "..."}}
  ],
  "installation_steps": [
    {{"step": "...", "description": "..."}}
  ],
  "key_endpoints": [
    {{"endpoint": "...", "method": "...", "description": "..."}}
  ],
  "quick_start_summary": "..."
}}
"""
        
        try:
            response = requests.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.CODE_LLM_MODEL,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=300
            )
            response.raise_for_status()
            result = response.json()
            content = result.get("response", "").strip()
            
            # 解析 JSON
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            import json
            getting_started_data = json.loads(content)
            
            # 验证生成的数据完整性
            prerequisites_count = len(getting_started_data.get('prerequisites', []))
            steps_count = len(getting_started_data.get('installation_steps', []))
            endpoints_count = len(getting_started_data.get('key_endpoints', []))
            has_summary = bool(getting_started_data.get('quick_start_summary', ''))
            
            logger.info(f"快速开始指南生成成功: prerequisites={prerequisites_count}, "
                       f"installation_steps={steps_count}, key_endpoints={endpoints_count}, "
                       f"has_summary={has_summary}")
            
            # 如果数据不完整，记录警告
            if prerequisites_count == 0:
                logger.warning("快速开始指南：前置要求为空，可能 LLM 未正确生成")
            if steps_count == 0:
                logger.warning("快速开始指南：安装步骤为空，可能 LLM 未正确生成")
            if not has_summary:
                logger.warning("快速开始指南：快速开始总结为空")
            
            # 记录详细内容（用于调试）
            if prerequisites_count > 0:
                logger.debug(f"前置要求示例: {getting_started_data['prerequisites'][0]}")
            if steps_count > 0:
                logger.debug(f"安装步骤示例: {getting_started_data['installation_steps'][0]}")
            
            return getting_started_data
        except Exception as e:
            logger.error(f"生成快速开始指南失败: {e}")
            return {
                "prerequisites": [],
                "installation_steps": [],
                "key_endpoints": [],
                "quick_start_summary": "快速开始指南生成失败"
            }
    
    def _generate_mermaid_architecture_diagram(self, arch_details: Dict, statistics: Dict) -> str:
        """
        生成 Mermaid 系统架构图
        
        Args:
            arch_details: 架构详细信息
            statistics: 统计信息
            
        Returns:
            Mermaid 图表代码
        """
        diagram = "```mermaid\ngraph TB\n"
        
        # 三层架构节点
        if arch_details['three_tier_structure']['has_frontend']:
            frontend_langs = ', '.join(list(statistics.get('languages', {}).keys())[:3])
            diagram += f'    Frontend["前端层<br/>{frontend_langs}"]\n'
        
        if arch_details['three_tier_structure']['has_backend']:
            backend_langs = ', '.join([lang for lang in list(statistics.get('languages', {}).keys())[:3] if lang not in ['vue', 'javascript', 'typescript']])
            if not backend_langs:
                backend_langs = 'Python/Java/Go'
            diagram += f'    Backend["应用层<br/>{backend_langs}"]\n'
        
        # 数据层（从架构信息推断）
        storage_systems = []
        if arch_details.get('storage_systems'):
            storage_systems = [s.get('name', '') for s in arch_details['storage_systems'][:3]]
        else:
            # 默认推断
            storage_systems = ['MySQL', 'OpenSearch']
        
        if storage_systems:
            storage_str = ' + '.join(storage_systems)
            diagram += f'    Data["数据层<br/>{storage_str}"]\n'
        
        # 连接关系
        if arch_details['three_tier_structure']['has_frontend'] and arch_details['three_tier_structure']['has_backend']:
            diagram += '    Frontend --> Backend\n'
        
        if arch_details['three_tier_structure']['has_backend'] and storage_systems:
            diagram += '    Backend --> Data\n'
        
        # 添加主要组件（如果有）
        if arch_details.get('service_files'):
            diagram += '    Backend --> Services["服务层"]\n'
            diagram += '    Services --> Data\n'
        
        if arch_details.get('task_files'):
            diagram += '    Backend --> Tasks["异步任务"]\n'
            diagram += '    Tasks --> Data\n'
        
        diagram += "```"
        return diagram
    
    def _generate_mermaid_data_flow_diagram(self, arch_details: Dict) -> str:
        """
        生成 Mermaid 数据流图
        
        Args:
            arch_details: 架构详细信息
            
        Returns:
            Mermaid 图表代码
        """
        diagram = "```mermaid\nsequenceDiagram\n"
        
        # 典型请求流程
        diagram += "    participant Client as 客户端\n"
        
        if arch_details.get('api_routes'):
            diagram += "    participant API as API 层\n"
        
        if arch_details.get('service_files'):
            diagram += "    participant Service as 服务层\n"
        
        diagram += "    participant DB as 数据层\n"
        
        # 请求流程
        if arch_details.get('api_routes'):
            diagram += "    Client->>API: HTTP Request\n"
            if arch_details.get('service_files'):
                diagram += "    API->>Service: 调用服务方法\n"
                diagram += "    Service->>DB: 查询数据\n"
                diagram += "    DB-->>Service: 返回结果\n"
                diagram += "    Service-->>API: 返回数据\n"
            else:
                diagram += "    API->>DB: 查询数据\n"
                diagram += "    DB-->>API: 返回结果\n"
            diagram += "    API-->>Client: HTTP Response\n"
        else:
            diagram += "    Client->>Service: 请求\n"
            diagram += "    Service->>DB: 查询\n"
            diagram += "    DB-->>Service: 结果\n"
            diagram += "    Service-->>Client: 响应\n"
        
        diagram += "```"
        return diagram
    
    def _generate_mermaid_api_diagram(self, arch_details: Dict) -> str:
        """
        生成 Mermaid API 架构图
        
        Args:
            arch_details: 架构详细信息
            
        Returns:
            Mermaid 图表代码
        """
        diagram = "```mermaid\ngraph LR\n"
        
        # 提取主要 API 端点（前 10 个）
        endpoints = arch_details.get('api_endpoints_detail', [])[:10]
        
        if not endpoints:
            # 如果没有详细端点，使用路由文件
            routes = arch_details.get('api_routes', [])[:10]
            for i, route in enumerate(routes):
                route_id = f"API{i+1}"
                diagram += f'    {route_id}["{route["path"]}"]\n'
        else:
            # 使用详细端点信息
            for i, endpoint in enumerate(endpoints):
                endpoint_id = f"API{i+1}"
                method = endpoint.get('method', 'GET')
                path = endpoint.get('path', '')
                # 简化路径显示
                path_short = path[:30] + '...' if len(path) > 30 else path
                diagram += f'    {endpoint_id}["{method} {path_short}"]\n'
        
        # 连接到服务层
        if arch_details.get('service_files'):
            diagram += '    Service["服务层"]\n'
            endpoint_count = len(endpoints) if endpoints else len(arch_details.get('api_routes', []))
            for i in range(min(endpoint_count, 10)):
                endpoint_id = f"API{i+1}"
                diagram += f'    {endpoint_id} --> Service\n'
        
        diagram += "```"
        return diagram
    
    def _generate_architecture_recommendations(
        self,
        analyzed_files: List[Dict],
        arch_details: Dict,
        module_structure: Dict,
        repo_path: str
    ) -> Dict:
        """
        生成架构建议
        
        Args:
            analyzed_files: 已分析的文件列表
            arch_details: 架构详细信息
            module_structure: 模块结构信息
            repo_path: 仓库路径
            
        Returns:
            {
                "patterns_detected": [...],
                "potential_issues": [...],
                "improvement_suggestions": [...]
            }
        """
        logger.info("开始生成架构建议")
        
        # 1. 检测架构模式
        patterns = self._detect_architecture_patterns(analyzed_files, arch_details, module_structure)
        
        # 2. 检测潜在问题
        issues = self._detect_architecture_issues(module_structure, arch_details)
        
        # 3. 使用 LLM 生成改进建议
        suggestions = self._generate_improvement_suggestions_llm(
            patterns, issues, arch_details, module_structure, repo_path
        )
        
        return {
            "patterns_detected": patterns,
            "potential_issues": issues,
            "improvement_suggestions": suggestions
        }
    
    def _detect_architecture_patterns(
        self,
        analyzed_files: List[Dict],
        arch_details: Dict,
        module_structure: Dict
    ) -> List[Dict]:
        """检测架构模式"""
        patterns = []
        
        # 检测 MVC 模式
        has_models = any('model' in f.get('file_path', '').lower() for f in analyzed_files)
        has_views = any('view' in f.get('file_path', '').lower() or 'component' in f.get('file_path', '').lower() for f in analyzed_files)
        has_controllers = any('controller' in f.get('file_path', '').lower() or 'route' in f.get('file_path', '').lower() for f in analyzed_files)
        
        if has_models and has_views and has_controllers:
            patterns.append({
                "pattern": "MVC (Model-View-Controller)",
                "confidence": "高",
                "description": "检测到模型、视图和控制器分离的架构模式"
            })
        
        # 检测分层架构
        has_api_layer = arch_details.get('api_endpoints_detail', [])
        has_service_layer = arch_details.get('service_methods_detail', [])
        has_data_layer = arch_details.get('database_tables', [])
        
        if has_api_layer and has_service_layer and has_data_layer:
            patterns.append({
                "pattern": "分层架构 (Layered Architecture)",
                "confidence": "高",
                "description": "检测到 API 层、服务层和数据层的清晰分离"
            })
        
        # 检测微服务模式
        modules = module_structure.get('modules', [])
        if len(modules) > 5:
            independent_modules = sum(1 for m in modules if len(m.get('dependencies', [])) < 2)
            if independent_modules > 3:
                patterns.append({
                    "pattern": "微服务架构 (Microservices)",
                    "confidence": "中",
                    "description": f"检测到 {independent_modules} 个相对独立的模块，可能采用微服务架构"
                })
        
        # 检测服务层模式
        if has_service_layer:
            patterns.append({
                "pattern": "服务层模式 (Service Layer)",
                "confidence": "高",
                "description": "检测到专门的服务层，业务逻辑与 API 层分离"
            })
        
        return patterns
    
    def _detect_architecture_issues(
        self,
        module_structure: Dict,
        arch_details: Dict
    ) -> List[Dict]:
        """检测潜在架构问题"""
        issues = []
        
        # 检测循环依赖
        circular_deps = self._detect_circular_dependencies(module_structure)
        if circular_deps:
            issues.append({
                "type": "循环依赖",
                "severity": "高",
                "description": f"检测到 {len(circular_deps)} 组循环依赖",
                "details": circular_deps[:5]  # 最多显示 5 个
            })
        
        # 检测高耦合
        high_coupling = self._detect_high_coupling(module_structure)
        if high_coupling:
            issues.append({
                "type": "高耦合",
                "severity": "中",
                "description": f"检测到 {len(high_coupling)} 个高耦合模块",
                "details": high_coupling[:5]
            })
        
        # 检测单点故障
        critical_modules = self._detect_critical_modules(module_structure, arch_details)
        if critical_modules:
            issues.append({
                "type": "单点故障风险",
                "severity": "高",
                "description": f"检测到 {len(critical_modules)} 个关键模块，存在单点故障风险",
                "details": critical_modules[:5]
            })
        
        return issues
    
    def _detect_circular_dependencies(self, module_structure: Dict) -> List[List[str]]:
        """检测循环依赖"""
        circular_deps = []
        visited = set()
        modules = module_structure.get('modules', [])
        
        # 构建模块名到模块数据的映射
        module_map = {m['name']: m for m in modules}
        
        def dfs(module: str, path: List[str]) -> bool:
            if module in path:
                # 找到循环
                cycle_start = path.index(module)
                cycle = path[cycle_start:] + [module]
                if cycle not in circular_deps:
                    circular_deps.append(cycle)
                return True
            
            if module in visited:
                return False
            
            visited.add(module)
            path.append(module)
            
            module_data = module_map.get(module, {})
            deps = module_data.get('dependencies', [])
            for dep in deps:
                dep_name = dep.get('module') if isinstance(dep, dict) else dep
                if dep_name and dep_name in module_map:
                    dfs(dep_name, path.copy())
            
            return False
        
        for module in module_map:
            if module not in visited:
                dfs(module, [])
        
        return circular_deps
    
    def _detect_high_coupling(self, module_structure: Dict) -> List[Dict]:
        """检测高耦合模块"""
        high_coupling = []
        threshold = 5  # 依赖超过 5 个视为高耦合
        modules = module_structure.get('modules', [])
        
        for module_data in modules:
            deps_count = len(module_data.get('dependencies', []))
            if deps_count > threshold:
                high_coupling.append({
                    "module": module_data.get('name', ''),
                    "dependencies_count": deps_count,
                    "dependencies": module_data.get('dependencies', [])[:10]
                })
        
        return sorted(high_coupling, key=lambda x: x['dependencies_count'], reverse=True)
    
    def _detect_critical_modules(self, module_structure: Dict, arch_details: Dict) -> List[Dict]:
        """检测关键模块（被多个模块依赖）"""
        critical_modules = []
        dependents_count = defaultdict(int)
        modules = module_structure.get('modules', [])
        
        # 统计每个模块被依赖的次数
        for module_data in modules:
            deps = module_data.get('dependencies', [])
            for dep in deps:
                dep_name = dep.get('module') if isinstance(dep, dict) else dep
                if dep_name:
                    dependents_count[dep_name] += 1
        
        # 找出被依赖次数最多的模块
        threshold = 3  # 被 3 个以上模块依赖视为关键模块
        for module, count in dependents_count.items():
            if count >= threshold:
                critical_modules.append({
                    "module": module,
                    "dependents_count": count,
                    "description": f"被 {count} 个模块依赖，存在单点故障风险"
                })
        
        return sorted(critical_modules, key=lambda x: x['dependents_count'], reverse=True)
    
    def _generate_improvement_suggestions_llm(
        self,
        patterns: List[Dict],
        issues: List[Dict],
        arch_details: Dict,
        module_structure: Dict,
        repo_path: str
    ) -> List[Dict]:
        """使用 LLM 生成改进建议"""
        try:
            import requests
            from app.config.settings import settings
            
            # 构建上下文
            context = f"""
## 检测到的架构模式
{json.dumps(patterns, ensure_ascii=False, indent=2)}

## 检测到的潜在问题
{json.dumps(issues, ensure_ascii=False, indent=2)}

## 模块结构
模块数量: {len(module_structure.get('modules', []))}
主要模块: {', '.join([m.get('name', '') for m in module_structure.get('modules', [])[:10]])}
"""
            
            prompt = f"""基于以下架构分析结果，生成具体的改进建议：

{context}

请生成 3-5 条改进建议，每条建议包含：
1. suggestion: 建议内容
2. priority: 优先级（高/中/低）
3. impact: 预期影响
4. implementation: 实施步骤（简要说明）

返回 JSON 格式：
{{
  "suggestions": [
    {{
      "suggestion": "建议内容",
      "priority": "高",
      "impact": "预期影响",
      "implementation": "实施步骤"
    }}
  ]
}}
"""
            
            response = requests.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.CODE_LLM_MODEL,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            content = result.get("response", "").strip()
            
            # 解析 JSON
            try:
                # 提取 JSON 部分
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    suggestions_data = json.loads(json_match.group())
                    suggestions = suggestions_data.get('suggestions', [])
                    logger.info(f"LLM 生成架构改进建议成功，数量: {len(suggestions)}")
                    return suggestions
            except json.JSONDecodeError:
                logger.warning("LLM 返回的 JSON 格式不正确，使用默认建议")
            
            # 默认建议
            return [
                {
                    "suggestion": "考虑引入依赖注入框架，降低模块间耦合",
                    "priority": "中",
                    "impact": "提高代码可维护性和可测试性",
                    "implementation": "评估并引入合适的 DI 框架（如 Python 的 dependency-injector）"
                }
            ]
            
        except Exception as e:
            logger.error(f"LLM 生成架构改进建议失败: {e}")
            return []
    
    def _generate_code_quality_recommendations(
        self,
        analyzed_files: List[Dict],
        statistics: Dict
    ) -> Dict:
        """
        生成代码质量建议
        
        Args:
            analyzed_files: 已分析的文件列表
            statistics: 统计信息
            
        Returns:
            {
                "code_smells": [...],
                "refactoring_suggestions": [...],
                "test_suggestions": [...]
            }
        """
        logger.info("开始生成代码质量建议")
        
        # 1. 检测代码异味
        code_smells = self._detect_code_smells(analyzed_files)
        
        # 2. 使用 LLM 生成重构建议
        refactoring_suggestions = self._generate_refactoring_suggestions_llm(
            code_smells, analyzed_files
        )
        
        # 3. 生成测试建议
        test_suggestions = self._generate_test_suggestions(analyzed_files)
        
        return {
            "code_smells": code_smells,
            "refactoring_suggestions": refactoring_suggestions,
            "test_suggestions": test_suggestions
        }
    
    def _detect_code_smells(self, analyzed_files: List[Dict]) -> List[Dict]:
        """检测代码异味"""
        smells = []
        
        for file_data in analyzed_files:
            file_path = file_data.get('file_path', '')
            symbols = file_data.get('symbols', [])
            complexity = file_data.get('complexity', {})
            
            # 检测长函数
            for symbol in symbols:
                if symbol.get('type') == 'function':
                    func_lines = symbol.get('end_line', 0) - symbol.get('line', 0)
                    if func_lines > 100:
                        smells.append({
                            "type": "长函数",
                            "severity": "中",
                            "file": file_path,
                            "symbol": symbol.get('name'),
                            "line": symbol.get('line'),
                            "description": f"函数 {symbol.get('name')} 超过 100 行，建议拆分"
                        })
            
            # 检测复杂类
            for symbol in symbols:
                if symbol.get('type') == 'class':
                    methods = symbol.get('methods', [])
                    if len(methods) > 20:
                        smells.append({
                            "type": "复杂类",
                            "severity": "中",
                            "file": file_path,
                            "symbol": symbol.get('name'),
                            "line": symbol.get('line'),
                            "description": f"类 {symbol.get('name')} 有 {len(methods)} 个方法，建议拆分"
                        })
            
            # 检测高复杂度
            cyclomatic = complexity.get('cyclomatic', 0)
            if cyclomatic > 20:
                # 对于文件级别的复杂度，尝试找到最复杂的符号
                most_complex_symbol = None
                most_complex_line = None
                max_symbol_complexity = 0
                max_symbol_lines = 0
                
                # 查找最复杂的函数或方法
                # 优先使用符号的复杂度分数（如果存在）
                for symbol in symbols:
                    if symbol.get('type') in ['function', 'method']:
                        symbol_complexity = symbol.get('complexity_score', 0)
                        # 如果符号有复杂度分数且 > 15，优先使用
                        if symbol_complexity > 15 and symbol_complexity > max_symbol_complexity:
                            most_complex_symbol = symbol.get('name')
                            most_complex_line = symbol.get('line')
                            max_symbol_complexity = symbol_complexity
                
                # 如果没有找到高复杂度的符号，尝试找最长的函数/方法（基于行数）
                if not most_complex_symbol:
                    for symbol in symbols:
                        if symbol.get('type') in ['function', 'method']:
                            start_line = symbol.get('line', 0)
                            end_line = symbol.get('end_line', start_line)
                            symbol_lines = max(1, end_line - start_line + 1)
                            # 如果函数超过 50 行，认为它可能是最复杂的
                            if symbol_lines > max_symbol_lines:
                                most_complex_symbol = symbol.get('name')
                                most_complex_line = symbol.get('line')
                                max_symbol_lines = symbol_lines
                
                # 如果还是没有找到，至少显示第一个函数/方法作为参考
                if not most_complex_symbol:
                    for symbol in symbols:
                        if symbol.get('type') in ['function', 'method']:
                            most_complex_symbol = symbol.get('name')
                            most_complex_line = symbol.get('line')
                            break
                
                # 检查是否为压缩文件，如果是，添加特殊提示
                is_minified = self._is_minified_file(file_path)
                symbol_display = most_complex_symbol
                description_suffix = ""
                
                if is_minified:
                    # 压缩文件：符号名称无意义，添加警告
                    description_suffix = "（注意：此文件为压缩代码，符号名称可能无意义，建议查看源代码文件）"
                    if most_complex_symbol and len(most_complex_symbol) == 1:
                        # 单个字母的符号名称，很可能是压缩后的变量名
                        symbol_display = None  # 不显示无意义的符号名
                elif most_complex_symbol:
                    description_suffix = f"（最复杂符号: {most_complex_symbol}）"
                
                smells.append({
                    "type": "高复杂度",
                    "severity": "高" if cyclomatic > 30 else "中",
                    "file": file_path,
                    "symbol": symbol_display,  # 压缩文件不显示无意义的符号名
                    "line": most_complex_line,  # 最复杂符号的行号，如果没有则为 None
                    "description": f"文件复杂度 {cyclomatic}，建议重构{description_suffix}"
                })
        
        return sorted(smells, key=lambda x: {'高': 3, '中': 2, '低': 1}.get(x.get('severity', '低'), 1), reverse=True)
    
    def _generate_refactoring_suggestions_llm(
        self,
        code_smells: List[Dict],
        analyzed_files: List[Dict]
    ) -> List[Dict]:
        """使用 LLM 生成重构建议"""
        try:
            import requests
            from app.config.settings import settings
            
            # 构建上下文
            context = f"""
## 检测到的代码异味
{json.dumps(code_smells[:10], ensure_ascii=False, indent=2)}

## 代码统计
总文件数: {len(analyzed_files)}
"""
            
            prompt = f"""基于以下代码质量分析结果，生成具体的重构建议：

{context}

请生成 3-5 条重构建议，每条建议包含：
1. suggestion: 重构建议内容
2. priority: 优先级（高/中/低）
3. affected_files: 受影响的文件列表（文件名）
4. steps: 重构步骤（简要说明）

返回 JSON 格式：
{{
  "suggestions": [
    {{
      "suggestion": "重构建议",
      "priority": "高",
      "affected_files": ["file1.py", "file2.py"],
      "steps": "步骤说明"
    }}
  ]
}}
"""
            
            response = requests.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.CODE_LLM_MODEL,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            content = result.get("response", "").strip()
            
            # 解析 JSON
            try:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    suggestions_data = json.loads(json_match.group())
                    suggestions = suggestions_data.get('suggestions', [])
                    logger.info(f"LLM 生成重构建议成功，数量: {len(suggestions)}")
                    return suggestions
            except json.JSONDecodeError:
                logger.warning("LLM 返回的 JSON 格式不正确，使用默认建议")
            
            # 默认建议
            return [
                {
                    "suggestion": "拆分长函数，提高代码可读性",
                    "priority": "中",
                    "affected_files": [],
                    "steps": "识别长函数，提取子函数，保持单一职责"
                }
            ]
            
        except Exception as e:
            logger.error(f"LLM 生成重构建议失败: {e}")
            return []
    
    def _generate_test_suggestions(self, analyzed_files: List[Dict]) -> List[Dict]:
        """生成测试建议"""
        suggestions = []
        
        # 检查测试文件覆盖率
        test_files = [f for f in analyzed_files if 'test' in f.get('file_path', '').lower()]
        test_ratio = len(test_files) / max(len(analyzed_files), 1)
        
        if test_ratio < 0.2:
            suggestions.append({
                "type": "测试覆盖率不足",
                "severity": "高",
                "description": f"测试文件占比 {test_ratio*100:.1f}%，建议提高测试覆盖率",
                "files": []
            })
        
        # 检查关键文件是否有测试
        key_files = [f for f in analyzed_files if any(kw in f.get('file_path', '').lower() for kw in ['service', 'api', 'controller'])]
        untested_key_files = []
        for key_file in key_files[:10]:
            file_name = Path(key_file.get('file_path', '')).stem
            has_test = any(file_name in tf.get('file_path', '') for tf in test_files)
            if not has_test:
                untested_key_files.append(key_file.get('file_path', ''))
        
        if untested_key_files:
            suggestions.append({
                "type": "关键文件缺少测试",
                "severity": "中",
                "description": f"{len(untested_key_files)} 个关键文件缺少测试",
                "files": untested_key_files[:5]
            })
        
        return suggestions
