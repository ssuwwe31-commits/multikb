"""
代码架构分析模块
负责提取架构详情、检测架构模式、生成架构建议等
"""

import os
import re
import ast
import json
from typing import Dict, List, Optional
from collections import defaultdict

from app.core.logging import logger
from app.services.code_diagram_generator import CodeDiagramGenerator


class CodeArchitectureAnalyzer:
    """代码架构分析器"""
    
    def __init__(self, diagram_generator: Optional[CodeDiagramGenerator] = None):
        """
        初始化架构分析器
        
        Args:
            diagram_generator: 图表生成器（可选，如果提供则使用，否则创建新实例）
        """
        self.diagram_generator = diagram_generator or CodeDiagramGenerator()
    
    def extract_architecture_details(
        self, 
        analyzed_files: List[Dict], 
        repo_path: str, 
        external_services: Optional[List[Dict]] = None
    ) -> Dict:
        """提取详细的架构信息（API路由、服务文件、前端组件等）"""
        architecture = {
            'api_routes': [],
            'api_endpoints_detail': [],
            'service_files': [],
            'service_methods_detail': [],
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
                    
                    endpoints = self.extract_api_endpoints_detail(file_data, repo_path)
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
                    
                    methods = self.extract_service_methods_detail(file_data, repo_path)
                    architecture['service_methods_detail'].extend(methods)
        
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
        
        # 识别存储系统（从外部服务检测结果中提取 + 从代码中直接检测）
        logger.debug(f"[架构提取] 🔍 开始检测存储系统")
        logger.debug(f"[架构提取] external_services 参数: {external_services}")
        
        storage_service_types = ['数据库', '搜索引擎', '对象存储', '缓存']
        
        # 方法1: 从 external_services 中提取
        if external_services:
            logger.debug(f"[架构提取] 从 external_services 中提取，数量={len(external_services)}")
            for service in external_services:
                service_name = service.get('name', '')
                service_type = service.get('type', '')
                logger.debug(f"[架构提取] 检查服务: name={service_name}, type={service_type}")
                if service_type in storage_service_types and service_name:
                    logger.debug(f"[架构提取] ✅ 识别为存储系统: {service_name} ({service_type})")
                    architecture['storage_systems'].append({
                        'name': service_name,
                        'type': service_type,
                        'count': service.get('count', 0)
                    })
        
        # 方法2: 从代码文件中直接检测（通过导入语句、配置文件等）
        logger.debug(f"[架构提取] 从代码文件中直接检测存储系统")
        detected_storage = self._detect_storage_from_code(analyzed_files)
        logger.debug(f"[架构提取] 从代码中检测到 {len(detected_storage)} 个存储系统: {[s.get('name') for s in detected_storage]}")
        for storage in detected_storage:
            # 避免重复添加
            if not any(s.get('name') == storage.get('name') for s in architecture['storage_systems']):
                architecture['storage_systems'].append(storage)
                logger.debug(f"[架构提取] ✅ 添加存储系统: {storage.get('name')}")
        
        if len(architecture['storage_systems']) > 0:
            logger.info(f"[架构提取] ✅ 检测到 {len(architecture['storage_systems'])} 个存储系统: {[s.get('name') for s in architecture['storage_systems']]}")
        else:
            logger.warning(f"[架构提取] ⚠️ 未检测到存储系统")
        
        # 识别三层架构
        has_frontend = len(architecture['frontend_views']) > 0 or len(architecture['frontend_components']) > 0
        has_backend = len(architecture['api_routes']) > 0 or len(architecture['service_files']) > 0
        has_data = len(architecture['service_files']) > 0
        
        architecture['three_tier_structure'] = {
            'has_frontend': has_frontend,
            'has_backend': has_backend,
            'has_data_layer': has_data,
            'frontend_files': len(architecture['frontend_views']) + len(architecture['frontend_components']),
            'backend_files': len(architecture['api_routes']) + len(architecture['service_files']),
            'task_files': len(architecture['task_files'])
        }
        
        return architecture
    
    def _detect_storage_from_code(self, analyzed_files: List[Dict]) -> List[Dict]:
        """
        从代码文件中直接检测存储系统（通过导入语句、配置文件等）
        
        Args:
            analyzed_files: 已分析的文件列表
            
        Returns:
            检测到的存储系统列表
        """
        storage_systems = []
        
        # 数据库相关的导入模式
        db_patterns = {
            'PostgreSQL': ['psycopg2', 'psycopg', 'postgresql', 'pg8000', 'asyncpg', 'sqlalchemy'],
            'MySQL': ['mysql', 'pymysql', 'mysql-connector', 'mysqldb'],
            'SQLite': ['sqlite3', 'sqlite'],
            'MongoDB': ['pymongo', 'motor', 'mongoengine'],
            'Redis': ['redis', 'hiredis'],
            'Elasticsearch': ['elasticsearch', 'opensearch'],
            'OpenSearch': ['opensearch-py', 'opensearch'],
            '文件系统': ['os.path', 'pathlib', 'shutil'],
        }
        
        # 配置文件模式
        config_patterns = {
            'PostgreSQL': ['postgresql://', 'postgres://', 'POSTGRES_', 'DATABASE_URL'],
            'MySQL': ['mysql://', 'mysql+pymysql://', 'MYSQL_'],
            'SQLite': ['.db', '.sqlite', 'sqlite://'],
            'MongoDB': ['mongodb://', 'MONGO_'],
            'Redis': ['redis://', 'REDIS_'],
            'Elasticsearch': ['elasticsearch://', 'ELASTICSEARCH_'],
            'OpenSearch': ['opensearch://', 'OPENSEARCH_'],
        }
        
        detected_names = set()
        
        # 从导入语句检测
        logger.debug(f"[架构提取] 开始从代码检测存储系统，文件数: {len(analyzed_files)}")
        files_with_content = 0
        files_without_content = 0
        
        for file_data in analyzed_files:
            file_path = file_data.get('file_path', '')
            content = file_data.get('content', '')
            
            # 如果没有 content，尝试从文件读取
            if not content:
                files_without_content += 1
                # 尝试读取文件内容（只读取前1000行，避免内存问题）
                try:
                    if os.path.exists(file_path):
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()[:1000]  # 只读取前1000行
                            content = ''.join(lines)
                            files_with_content += 1
                except Exception as e:
                    logger.debug(f"[架构提取] 🔍   无法读取文件内容: {file_path}, 错误: {e}")
                    continue
            
            if not content:
                continue
            
            files_with_content += 1
            
            # 检查导入语句
            for db_name, patterns in db_patterns.items():
                for pattern in patterns:
                    if pattern.lower() in content.lower():
                        if db_name not in detected_names:
                            detected_names.add(db_name)
                            storage_type = '数据库' if db_name not in ['Redis', '文件系统'] else ('缓存' if db_name == 'Redis' else '对象存储')
                            storage_systems.append({
                                'name': db_name,
                                'type': storage_type,
                                'count': 1,
                                'source': 'import',
                                'file': file_path
                            })
                            logger.info(f"[架构提取] 🔍   从导入语句检测到: {db_name} (文件: {file_path}, 模式: {pattern})")
                            break
            
            # 检查配置文件内容
            if any(ext in file_path.lower() for ext in ['.env', 'config', 'settings', 'database']):
                for db_name, patterns in config_patterns.items():
                    for pattern in patterns:
                        if pattern.lower() in content.lower():
                            if db_name not in detected_names:
                                detected_names.add(db_name)
                                storage_type = '数据库' if db_name not in ['Redis', '文件系统'] else ('缓存' if db_name == 'Redis' else '对象存储')
                                storage_systems.append({
                                    'name': db_name,
                                    'type': storage_type,
                                    'count': 1,
                                    'source': 'config',
                                    'file': file_path
                                })
                                logger.info(f"[架构提取] 🔍   从配置文件检测到: {db_name} (文件: {file_path}, 模式: {pattern})")
                                break
        
        logger.debug(f"[架构提取] 代码检测完成: 有内容={files_with_content}, 无内容={files_without_content}, 存储系统={len(storage_systems)}")
        return storage_systems
    
    def extract_api_endpoints_detail(self, file_data: Dict, repo_path: str) -> List[Dict]:
        """提取 API 端点详细信息"""
        endpoints = []
        file_path = file_data.get('file_path', '')
        full_path = os.path.join(repo_path, file_path) if file_path else None
        
        if not full_path or not os.path.exists(full_path):
            return endpoints
        
        language = file_data.get('language', '')
        
        try:
            if language == 'python':
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        http_method = None
                        route_path = None
                        docstring = ast.get_docstring(node) or ''
                        
                        for decorator in node.decorator_list:
                            if isinstance(decorator, ast.Call):
                                if hasattr(decorator.func, 'attr'):
                                    method = decorator.func.attr.lower()
                                    if method in ['get', 'post', 'put', 'delete', 'patch']:
                                        http_method = method.upper()
                                        if decorator.args:
                                            if isinstance(decorator.args[0], ast.Constant):
                                                route_path = decorator.args[0].value
                                            elif isinstance(decorator.args[0], ast.Str):
                                                route_path = decorator.args[0].s
                                        
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
                                            'docstring': docstring[:200],
                                            'line': node.lineno,
                                            'file_path': file_path
                                        })
                                        break
                            
                            elif isinstance(decorator, ast.Call) and hasattr(decorator.func, 'attr') and decorator.func.attr == 'route':
                                if decorator.args:
                                    if isinstance(decorator.args[0], ast.Constant):
                                        route_path = decorator.args[0].value
                                    elif isinstance(decorator.args[0], ast.Str):
                                        route_path = decorator.args[0].s
                                    
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
    
    def extract_service_methods_detail(self, file_data: Dict, repo_path: str) -> List[Dict]:
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
                                if arg.arg != 'self':
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
    
    def generate_architecture_recommendations(
        self,
        analyzed_files: List[Dict],
        arch_details: Dict,
        module_structure: Dict,
        repo_path: str
    ) -> Dict:
        """生成架构建议"""
        logger.info("开始生成架构建议")
        
        patterns = self.detect_architecture_patterns(analyzed_files, arch_details, module_structure)
        issues = self.detect_architecture_issues(module_structure, arch_details)
        suggestions = self.generate_improvement_suggestions_llm(
            patterns, issues, arch_details, module_structure, repo_path
        )
        
        return {
            "patterns_detected": patterns,
            "potential_issues": issues,
            "improvement_suggestions": suggestions
        }
    
    def detect_architecture_patterns(
        self,
        analyzed_files: List[Dict],
        arch_details: Dict,
        module_structure: Dict
    ) -> List[Dict]:
        """检测架构模式"""
        patterns = []
        
        has_models = any('model' in f.get('file_path', '').lower() for f in analyzed_files)
        has_views = any('view' in f.get('file_path', '').lower() or 'component' in f.get('file_path', '').lower() for f in analyzed_files)
        has_controllers = any('controller' in f.get('file_path', '').lower() or 'route' in f.get('file_path', '').lower() for f in analyzed_files)
        
        if has_models and has_views and has_controllers:
            patterns.append({
                "pattern": "MVC (Model-View-Controller)",
                "confidence": "高",
                "description": "检测到模型、视图和控制器分离的架构模式"
            })
        
        has_api_layer = arch_details.get('api_endpoints_detail', [])
        has_service_layer = arch_details.get('service_methods_detail', [])
        has_data_layer = arch_details.get('storage_systems', [])
        
        if has_api_layer and has_service_layer and has_data_layer:
            patterns.append({
                "pattern": "分层架构 (Layered Architecture)",
                "confidence": "高",
                "description": "检测到 API 层、服务层和数据层的清晰分离"
            })
        
        modules = module_structure.get('modules', [])
        if len(modules) > 5:
            independent_modules = sum(1 for m in modules if len(m.get('dependencies', [])) < 2)
            if independent_modules > 3:
                patterns.append({
                    "pattern": "微服务架构 (Microservices)",
                    "confidence": "中",
                    "description": f"检测到 {independent_modules} 个相对独立的模块，可能采用微服务架构"
                })
        
        if has_service_layer:
            patterns.append({
                "pattern": "服务层模式 (Service Layer)",
                "confidence": "高",
                "description": "检测到专门的服务层，业务逻辑与 API 层分离"
            })
        
        return patterns
    
    def detect_architecture_issues(
        self,
        module_structure: Dict,
        arch_details: Dict
    ) -> List[Dict]:
        """检测潜在架构问题"""
        issues = []
        
        circular_deps = self.detect_circular_dependencies(module_structure)
        if circular_deps:
            issues.append({
                "type": "循环依赖",
                "severity": "高",
                "description": f"检测到 {len(circular_deps)} 组循环依赖",
                "details": circular_deps[:5]
            })
        
        high_coupling = self.detect_high_coupling(module_structure)
        if high_coupling:
            issues.append({
                "type": "高耦合",
                "severity": "中",
                "description": f"检测到 {len(high_coupling)} 个高耦合模块",
                "details": high_coupling[:5]
            })
        
        critical_modules = self.detect_critical_modules(module_structure, arch_details)
        if critical_modules:
            issues.append({
                "type": "单点故障风险",
                "severity": "高",
                "description": f"检测到 {len(critical_modules)} 个关键模块，存在单点故障风险",
                "details": critical_modules[:5]
            })
        
        return issues
    
    def detect_circular_dependencies(self, module_structure: Dict) -> List[List[str]]:
        """检测循环依赖"""
        circular_deps = []
        visited = set()
        modules = module_structure.get('modules', [])
        module_map = {m['name']: m for m in modules}
        
        def dfs(module: str, path: List[str]) -> bool:
            if module in path:
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
    
    def detect_high_coupling(self, module_structure: Dict) -> List[Dict]:
        """检测高耦合模块"""
        high_coupling = []
        threshold = 5
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
    
    def detect_critical_modules(self, module_structure: Dict, arch_details: Dict) -> List[Dict]:
        """检测关键模块（被多个模块依赖）"""
        critical_modules = []
        dependents_count = defaultdict(int)
        modules = module_structure.get('modules', [])
        
        for module_data in modules:
            deps = module_data.get('dependencies', [])
            for dep in deps:
                dep_name = dep.get('module') if isinstance(dep, dict) else dep
                if dep_name:
                    dependents_count[dep_name] += 1
        
        threshold = 3
        for module, count in dependents_count.items():
            if count >= threshold:
                critical_modules.append({
                    "module": module,
                    "dependents_count": count,
                    "description": f"被 {count} 个模块依赖，存在单点故障风险"
                })
        
        return sorted(critical_modules, key=lambda x: x['dependents_count'], reverse=True)
    
    def generate_improvement_suggestions_llm(
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
            
            try:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    suggestions_data = json.loads(json_match.group())
                    suggestions = suggestions_data.get('suggestions', [])
                    logger.info(f"LLM 生成架构改进建议成功，数量: {len(suggestions)}")
                    return suggestions
            except json.JSONDecodeError:
                logger.warning("LLM 返回的 JSON 格式不正确，使用默认建议")
            
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
    
    def generate_system_architecture_llm(
        self,
        analyzed_files: List[Dict],
        module_structure: Dict,
        repo_name: str,
        statistics: Dict,
        repo_path: str
    ) -> Dict:
        """使用 LLM 生成详细的系统架构说明"""
        import requests
        from app.config.settings import settings
        
        external_services = statistics.get('external_services', [])
        arch_details = self.extract_architecture_details(analyzed_files, repo_path, external_services)
        
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
        
        context += "\n## API 端点详细信息（前30个）\n"
        for endpoint in arch_details.get('api_endpoints_detail', [])[:30]:
            context += f"""
- {endpoint['method']} {endpoint['path']} ({endpoint['file_path']}:{endpoint['line']})
  - 函数: {endpoint['function_name']}
  - 参数: {', '.join([p['name'] for p in endpoint.get('parameters', [])])}
  - 说明: {endpoint.get('docstring', '')[:100]}
"""
        
        context += "\n## 服务方法详细信息（前30个）\n"
        for method in arch_details.get('service_methods_detail', [])[:30]:
            context += f"""
- {method.get('class_name', '')}.{method['method_name']} ({method['file_path']}:{method['line']})
  - 参数: {', '.join([p['name'] for p in method.get('parameters', [])])}
  - 说明: {method.get('docstring', '')[:100]}
"""
        
        # 添加存储系统检测结果到上下文
        context += "\n## 检测到的存储系统\n"
        if arch_details.get('storage_systems'):
            for storage in arch_details['storage_systems']:
                context += f"""
- {storage.get('name', 'N/A')} ({storage.get('type', 'N/A')})
  - 检测来源: {storage.get('source', 'external_services')}
  - 相关文件: {storage.get('file', 'N/A')}
"""
        else:
            context += "\n- 未通过自动检测识别到存储系统，请根据代码中的导入语句、配置文件和数据库操作推断\n"
        
        # 添加代码中的数据库相关导入和操作线索
        context += "\n## 代码中的存储系统线索（用于推断）\n"
        db_imports = []
        db_operations = []
        for file_data in analyzed_files[:50]:  # 只检查前50个文件
            content = file_data.get('content', '')
            file_path = file_data.get('file_path', '')
            if not content:
                continue
            
            # 检查数据库相关导入
            db_keywords = ['sqlite', 'postgres', 'mysql', 'mongo', 'redis', 'elasticsearch', 'opensearch', 'database', 'db']
            for keyword in db_keywords:
                if keyword in content.lower():
                    # 提取包含该关键字的行
                    lines = content.split('\n')
                    for i, line in enumerate(lines[:20], 1):  # 只检查前20行（通常是导入部分）
                        if keyword in line.lower() and ('import' in line or 'from' in line or 'require' in line):
                            db_imports.append(f"{file_path}:{i} - {line.strip()[:100]}")
                            break
            
            # 检查数据库操作
            db_ops = ['db.query', 'db.execute', 'collection.find', 'collection.insert', 'redis.get', 'redis.set', 'session.query']
            for op in db_ops:
                if op in content.lower():
                    db_operations.append(f"{file_path} - {op}")
                    break
        
        if db_imports:
            context += "\n### 数据库相关导入语句（前10个）\n"
            for imp in db_imports[:10]:
                context += f"- {imp}\n"
        
        if db_operations:
            context += "\n### 数据库操作（前10个）\n"
            for op in db_operations[:10]:
                context += f"- {op}\n"
        
        if not db_imports and not db_operations:
            context += "\n- 未在代码中发现明显的数据库导入或操作，但大多数项目至少会使用文件系统存储\n"
        
        base_architecture_diagram = self.diagram_generator.generate_architecture_diagram(arch_details, statistics)
        base_data_flow_diagram = self.diagram_generator.generate_data_flow_diagram(arch_details)
        base_api_diagram = self.diagram_generator.generate_api_diagram(arch_details)
        
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

1. three_tier_architecture: 三层架构详细说明（300-400字）
2. functional_subsystems_table: 功能子系统表格，**必须**是数组，每个元素包含：
   - subsystem_name: 子系统名称（如"用户认证子系统"）
   - frontend_path: 前端路径（如"src/views/auth"或"无"）
   - backend_route: 后端路由（如"/api/auth"或"无"）
   - service_files: 服务文件路径列表（如["src/services/auth_service.py"]）
   - key_responsibilities: 关键职责说明（详细描述，至少50字）
3. architectural_patterns: 架构模式说明（400-500字）
4. storage_systems_table: 存储系统表格，**必须**是数组，每个元素包含：
   - storage_system: 存储系统名称（如"PostgreSQL"、"MySQL"、"SQLite"、"MongoDB"、"Redis"、"Elasticsearch"、"文件系统"等）
   - data_types: 数据类型（如"关系型数据"、"文档数据"、"缓存数据"、"配置文件"、"日志文件"等）- **注意：字段名是 data_types（复数）**
   - access_pattern: 访问模式（如"ORM访问"、"直接文件读写"、"API调用"、"键值访问"等）- **注意：字段名是 access_pattern**
   - key_use_cases: 关键用例说明（详细描述，至少30字）
   - **重要：即使代码中没有明确检测到存储系统，也要根据以下线索推断：**
     * 导入语句（如 import sqlite3, import redis, from pymongo import MongoClient）
     * 配置文件（如 .env 文件中的数据库连接字符串）
     * 代码中的数据库操作（如 db.query(), collection.find()）
     * 项目依赖（如 requirements.txt, package.json 中的数据库相关包）
   - **如果确实没有任何存储系统（如纯前端项目），可以返回空数组 []，但大多数项目至少会有文件系统存储**
5. key_architectural_decisions: 关键架构决策列表，**必须**是数组，每个元素包含：
   - decision: 决策内容（如"采用 TypeScript 与 JavaScript 混合开发"）
   - rationale: **必须**填写决策理由（详细说明，至少50字，不能为空）- **注意：字段名是 rationale（不是 reason）**
   - impact: **必须**填写预期影响（详细说明，至少50字，不能为空）
6. api_architecture: API 架构说明（200-300字）
7. scalability_considerations: 系统可扩展性考虑（200-300字）
8. mermaid_architecture_diagram: Mermaid 格式的系统架构图代码
9. mermaid_data_flow_diagram: Mermaid 格式的数据流图代码
10. mermaid_api_diagram: Mermaid 格式的 API 架构图代码

要求：
- **所有内容必须基于实际代码分析，不要编造**
- **语言要非常专业和详细，类似 DeepWiki 的风格**
- **重点突出架构设计、技术选择和决策理由**
- **表格内容要详细，包含具体的文件路径和职责说明**
- **引用具体的文件路径作为依据**
- **Mermaid 图表要基于实际的 API 端点、服务方法、组件关系生成，可以优化和扩展基础图表**
- **所有字段都必须填写，不能为空字符串或空数组（除非确实没有数据）**
- **key_architectural_decisions 中的 reason 和 impact 字段必须详细填写，不能为空**

返回格式示例：
{{
  "three_tier_architecture": "...",
  "functional_subsystems_table": [
    {{
      "subsystem_name": "用户认证子系统",
      "frontend_path": "src/views/auth",
      "backend_route": "/api/auth",
      "service_files": ["src/services/auth_service.py"],
      "key_responsibilities": "负责用户登录、注册、权限验证等功能..."
    }}
  ],
  "architectural_patterns": "...",
  "storage_systems_table": [
    {{
      "storage_system": "PostgreSQL",
      "data_types": "关系型数据",
      "access_pattern": "ORM访问",
      "key_use_cases": "存储用户信息、配置数据等..."
    }}
  ],
  "key_architectural_decisions": [
    {{
      "decision": "采用 TypeScript 与 JavaScript 混合开发",
      "rationale": "TypeScript 提供类型安全，JavaScript 保持灵活性，混合使用可以平衡开发效率和代码质量...",
      "impact": "提高了代码可维护性，减少了运行时错误，但增加了构建复杂度..."
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
            
            # 记录 LLM 原始响应（详细内容用于调试）
            logger.debug(f"[系统架构生成] 收到 LLM 原始响应，长度: {len(content)} 字符")
            logger.debug(f"[系统架构生成] LLM 原始响应（前500字符）: {content[:500]}...")
            
            # 步骤2: 清理 JSON 标记
            logger.debug(f"[系统架构生成] 开始清理 JSON 标记")
            original_content = content
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            logger.debug(f"[系统架构生成] 清理后长度: {len(content)} 字符（减少了 {len(original_content) - len(content)} 字符）")
            
            # 步骤3: 解析 JSON
            logger.debug(f"[系统架构生成] 开始解析 JSON")
            try:
                architecture_data = json.loads(content)
                logger.debug(f"[系统架构生成] JSON 解析成功，数据结构键: {list(architecture_data.keys())}")
            except json.JSONDecodeError as e:
                logger.error(f"[系统架构生成] ❌ 步骤3失败: JSON 解析失败")
                logger.error(f"[系统架构生成] ❌ 错误位置: 行 {e.lineno}, 列 {e.colno}")
                logger.error(f"[系统架构生成] ❌ 错误消息: {e.msg}")
                logger.error(f"[系统架构生成] ❌ 解析失败的 JSON 内容（前1000字符）: {content[:1000]}...")
                logger.error(f"[系统架构生成] ❌ 解析失败的 JSON 内容（错误位置前后500字符）: {content[max(0, e.pos-500):e.pos+500]}")
                raise
            
            # 验证和修复数据格式
            # 1. 验证 functional_subsystems_table
            subsystems = architecture_data.get('functional_subsystems_table', [])
            logger.debug(f"[系统架构生成] functional_subsystems_table: 类型={type(subsystems).__name__}, 长度={len(subsystems) if isinstance(subsystems, list) else 'N/A'}")
            
            if not isinstance(subsystems, list):
                logger.warning("functional_subsystems_table 不是数组，转换为空数组")
                subsystems = []
            else:
                # 验证每个子系统的字段
                for i, subsystem in enumerate(subsystems):
                    if not isinstance(subsystem, dict):
                        logger.warning(f"functional_subsystems_table[{i}] 不是字典，跳过")
                        continue
                    # 记录每个子系统的字段
                    logger.debug(f"[系统架构生成] 子系统[{i}]: {subsystem.get('subsystem_name', 'N/A')} - 字段: {list(subsystem.keys())}")
                    # 确保必需字段存在
                    if 'subsystem_name' not in subsystem:
                        subsystem['subsystem_name'] = f"子系统{i+1}"
                        logger.warning(f"[系统架构生成] 子系统[{i}] 缺少 subsystem_name，已补充")
                    if 'key_responsibilities' not in subsystem or not subsystem.get('key_responsibilities'):
                        subsystem['key_responsibilities'] = "职责说明待补充"
                        logger.warning(f"[系统架构生成] 子系统[{i}] 缺少 key_responsibilities，已补充")
            architecture_data['functional_subsystems_table'] = subsystems
            logger.debug(f"[系统架构生成] functional_subsystems_table 验证完成: {len(subsystems)} 个条目")
            
            # 2. 验证 storage_systems_table
            storage_systems = architecture_data.get('storage_systems_table', [])
            logger.debug(f"[系统架构生成] storage_systems_table: 类型={type(storage_systems).__name__}, 长度={len(storage_systems) if isinstance(storage_systems, list) else 'N/A'}")
            
            if not isinstance(storage_systems, list):
                logger.warning("storage_systems_table 不是数组，转换为空数组")
                storage_systems = []
            else:
                # 验证每个存储系统的字段
                for i, storage in enumerate(storage_systems):
                    if not isinstance(storage, dict):
                        logger.warning(f"storage_systems_table[{i}] 不是字典，跳过")
                        continue
                    # 记录每个存储系统的字段（仅调试级别）
                    storage_system = storage.get('storage_system', 'N/A')
                    logger.debug(f"[系统架构生成] 存储系统[{i}]: {storage_system}, 字段: {list(storage.keys())}")
                    # 确保必需字段存在
                    if 'storage_system' not in storage:
                        storage['storage_system'] = f"存储系统{i+1}"
                        logger.warning(f"[系统架构生成] 存储系统[{i}] 缺少 storage_system，已补充")
                    
                    # 前端期望 data_types 和 access_pattern，需要兼容 data_type 和 access_mode
                    if 'data_types' not in storage:
                        if 'data_type' in storage:
                            storage['data_types'] = storage['data_type']
                            logger.debug(f"[系统架构生成] 存储系统[{i}] 字段名转换: data_type -> data_types")
                        else:
                            storage['data_types'] = "未指定"
                            logger.warning(f"[系统架构生成] 存储系统[{i}] 缺少 data_types，已补充默认值")
                    
                    if 'access_pattern' not in storage:
                        if 'access_mode' in storage:
                            storage['access_pattern'] = storage['access_mode']
                            logger.debug(f"[系统架构生成] 存储系统[{i}] 字段名转换: access_mode -> access_pattern")
                        else:
                            storage['access_pattern'] = "未指定"
                            logger.warning(f"[系统架构生成] 存储系统[{i}] 缺少 access_pattern，已补充默认值")
                    
                    if 'key_use_cases' not in storage or not storage.get('key_use_cases'):
                        storage['key_use_cases'] = "用例说明待补充"
                        logger.warning(f"[系统架构生成] 存储系统[{i}] 缺少 key_use_cases，已补充")
            architecture_data['storage_systems_table'] = storage_systems
            logger.debug(f"[系统架构生成] storage_systems_table 验证完成: {len(storage_systems)} 个条目")
            
            # 3. 验证 key_architectural_decisions
            decisions = architecture_data.get('key_architectural_decisions', [])
            logger.debug(f"[系统架构生成] key_architectural_decisions: 类型={type(decisions).__name__}, 长度={len(decisions) if isinstance(decisions, list) else 'N/A'}")
            
            if not isinstance(decisions, list):
                logger.warning("key_architectural_decisions 不是数组，转换为空数组")
                decisions = []
            else:
                # 验证每个决策的字段
                for i, decision in enumerate(decisions):
                    if not isinstance(decision, dict):
                        logger.warning(f"key_architectural_decisions[{i}] 不是字典，跳过")
                        continue
                    # 记录每个决策的字段（仅调试级别）
                    decision_text = decision.get('decision', 'N/A')[:50]
                    rationale_len = len(decision.get('rationale', '') or decision.get('reason', ''))
                    impact_len = len(decision.get('impact', ''))
                    logger.debug(f"[系统架构生成] 决策[{i}]: {decision_text}..., rationale长度={rationale_len}, impact长度={impact_len}")
                    
                    # 确保必需字段存在且不为空
                    if 'decision' not in decision:
                        decision['decision'] = f"架构决策{i+1}"
                        logger.warning(f"[系统架构生成] 决策[{i}] 缺少 decision，已补充")
                    
                    # 前端期望 rationale 而不是 reason，需要兼容两者
                    if 'rationale' not in decision:
                        if 'reason' in decision:
                            decision['rationale'] = decision['reason']
                            logger.debug(f"[系统架构生成] 决策[{i}] 字段名转换: reason -> rationale")
                        else:
                            decision['rationale'] = ""
                            logger.warning(f"[系统架构生成] 决策[{i}] 缺少 rationale 和 reason")
                    
                    # 如果 rationale 为空或过短，补充默认值
                    if not decision.get('rationale') or len(decision.get('rationale', '').strip()) < 10:
                        logger.warning(f"[系统架构生成] 决策[{i}] 的 rationale 字段为空或过短（长度={len(decision.get('rationale', ''))}），补充默认值")
                        decision['rationale'] = f"基于项目实际需求和技术选型考虑，采用此架构决策。具体原因需要进一步分析代码实现细节。"
                    
                    # 保留 reason 字段以兼容（如果存在）
                    if 'reason' not in decision:
                        decision['reason'] = decision['rationale']
                    
                    # 验证 impact 字段
                    if 'impact' not in decision or not decision.get('impact') or len(decision.get('impact', '').strip()) < 10:
                        logger.warning(f"[系统架构生成] 决策[{i}] 的 impact 字段为空或过短（长度={len(decision.get('impact', '')) if 'impact' in decision else 0}），补充默认值")
                        decision['impact'] = f"此决策对系统的可扩展性、可维护性和性能产生影响。具体影响需要结合实际使用场景评估。"
            architecture_data['key_architectural_decisions'] = decisions
            logger.debug(f"[系统架构生成] key_architectural_decisions 验证完成: {len(decisions)} 个条目")
            
            # 只记录关键摘要信息
            logger.info(f"[系统架构生成] ✅ 系统架构生成成功: 子系统={len(subsystems)}, 决策={len(decisions)}, 存储系统={len(storage_systems)}")
            
            if len(subsystems) == 0:
                logger.warning("[系统架构生成] ⚠️ functional_subsystems_table 为空数组")
            if len(decisions) == 0:
                logger.warning("[系统架构生成] ⚠️ key_architectural_decisions 为空数组")
            
            # 步骤4: 处理 Mermaid 图表
            logger.debug(f"[系统架构生成] 开始处理 Mermaid 图表")
            mermaid_api = architecture_data.get('mermaid_api_diagram', '')
            mermaid_arch = architecture_data.get('mermaid_architecture_diagram', '')
            mermaid_flow = architecture_data.get('mermaid_data_flow_diagram', '')
            logger.debug(f"[系统架构生成] Mermaid 图表长度: api={len(mermaid_api)}, arch={len(mermaid_arch)}, flow={len(mermaid_flow)}")
            
            if mermaid_api:
                # 清理代码标记
                api_code = mermaid_api.replace('```mermaid', '').replace('```', '').strip()
                logger.debug(f"[系统架构生成] 清理 mermaid_api_diagram: {len(mermaid_api)} -> {len(api_code)} 字符")
                
                # 验证和修复 Mermaid 语法
                api_code_before_fix = api_code
                api_code = self._validate_and_fix_mermaid_code(api_code, 'api_diagram')
                logger.debug(f"[系统架构生成] 修复 mermaid_api_diagram: {len(api_code_before_fix)} -> {len(api_code)} 字符")
                
                # 重新包装为完整格式
                architecture_data['mermaid_api_diagram'] = f"```mermaid\n{api_code}\n```"
                
                # 检查关键元素
                has_client = '客户端' in api_code or 'Client' in api_code or 'A[' in api_code
                has_api = '/api/' in api_code or 'API' in api_code
                if not (has_client and has_api):
                    logger.warning(f"[系统架构生成] ⚠️ API 架构图可能不完整，缺少关键元素")
            else:
                logger.warning(f"[系统架构生成] ⚠️ mermaid_api_diagram 为空")
            
            return architecture_data
            
        except Exception as e:
            logger.error(f"生成系统架构失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
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
    
    def _validate_and_fix_mermaid_code(self, code: str, diagram_type: str = 'unknown') -> str:
        """
        验证和修复 Mermaid 代码语法
        
        Args:
            code: Mermaid 代码
            diagram_type: 图表类型（用于日志）
            
        Returns:
            修复后的 Mermaid 代码
        """
        logger.debug(f"[系统架构生成] 开始验证和修复 Mermaid 代码: diagram_type={diagram_type}, 长度={len(code)} 字符")
        
        if not code:
            logger.debug(f"[系统架构生成] 输入代码为空，直接返回")
            return code
        
        lines = code.split('\n')
        logger.debug(f"[系统架构生成] 代码行数: {len(lines)}")
        fixed_lines = []
        
        for i, line in enumerate(lines):
            original_line = line
            line = line.strip()
            logger.debug(f"[系统架构生成] 处理第{i+1}行: {repr(line[:100])}")
            
            if not line:
                logger.debug(f"[系统架构生成] 第{i+1}行: 空行，跳过")
                continue
            
            # 检查是否是图表类型声明（第一行）
            if i == 0 and (line.startswith('graph ') or line.startswith('sequenceDiagram') or line.startswith('flowchart')):
                logger.debug(f"[系统架构生成] 第{i+1}行: 图表类型声明，保留")
                fixed_lines.append(line)
                continue
            
            # 修复常见的语法错误
            # 1. 修复不完整的箭头：`A ->` 应该是 `A --> B`
            if '->' in line:
                logger.debug(f"[系统架构生成] 第{i+1}行: 包含箭头，检查语法")
                # 检查是否是不完整的箭头
                if line.endswith('->') or line.endswith('-->'):
                    logger.warning(f"[系统架构生成] 第{i+1}行: ⚠️ 检测到不完整的箭头，跳过")
                    continue  # 跳过这一行
            
            # 2. 修复节点标签中的特殊字符（引号问题）
            # Mermaid 节点标签应该用引号包裹，如果包含特殊字符需要转义
            if '[' in line:
                logger.debug(f"[系统架构生成] 第{i+1}行: 包含节点定义，检查语法")
                if ']' not in line:
                    logger.warning(f"[系统架构生成] 第{i+1}行: ⚠️ 检测到未闭合的节点标签，跳过")
                    continue
                # 提取节点定义部分
                import re
                # 匹配节点定义：ID["label"] 或 ID[label]
                node_pattern = r'(\w+)\[([^\]]+)\]'
                original_line_for_fix = line
                def fix_node_label(match):
                    node_id = match.group(1)
                    label = match.group(2)
                    logger.debug(f"[系统架构生成] 修复节点: {node_id}[{label[:50]}]")
                    # 如果标签包含引号，需要转义或移除
                    label = label.replace('"', "'").replace("'", "'")
                    # 如果标签太长，截断
                    if len(label) > 50:
                        logger.debug(f"[系统架构生成] 标签过长({len(label)}字符)，截断到50字符")
                        label = label[:47] + '...'
                    fixed = f'{node_id}["{label}"]'
                    return fixed
                
                line = re.sub(node_pattern, fix_node_label, line)
                if line != original_line_for_fix:
                    logger.debug(f"[系统架构生成] 第{i+1}行: 节点标签已修复")
            
            # 3. 确保箭头语法正确
            # 修复 `A -> B[/api/c` 这种被截断的情况
            if '->' in line:
                parts = line.split('->')
                logger.debug(f"[系统架构生成] 第{i+1}行: 包含箭头，检查语法")
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()
                    # 如果右侧不完整（没有闭合的括号或引号），跳过
                    if right and not (right.endswith(']') or right.endswith('"') or right.endswith("'")):
                        # 检查是否是被截断的节点
                        if '[' in right and ']' not in right:
                            logger.warning(f"[系统架构生成] 第{i+1}行: ⚠️ 检测到被截断的节点，跳过")
                            continue
                    # 确保使用 `-->` 而不是 `->`
                    if ' -> ' in line or (line.count('->') == 1 and '-->' not in line):
                        line = line.replace(' -> ', ' --> ').replace('->', ' --> ')
                        logger.debug(f"[系统架构生成] 第{i+1}行: 箭头已修复")
            
            # 4. 移除注释行（Mermaid 不支持注释）
            if line.startswith('#') or line.startswith('//'):
                logger.debug(f"[系统架构生成] 第{i+1}行: 注释行，跳过")
                continue
            
            logger.debug(f"[系统架构生成] 第{i+1}行: ✅ 保留")
            fixed_lines.append(line)
        
        fixed_code = '\n'.join(fixed_lines)
        logger.debug(f"[系统架构生成] 修复后代码行数: {len(fixed_lines)}")
        
        # 验证基本语法
        has_graph_type = (fixed_code.startswith('graph ') or 
                         fixed_code.startswith('sequenceDiagram') or 
                         fixed_code.startswith('flowchart'))
        logger.debug(f"[系统架构生成] 是否有图表类型声明: {has_graph_type}")
        
        if not has_graph_type:
            # 如果没有图表类型声明，添加默认的
            default_type = 'graph LR' if diagram_type == 'api_diagram' else 'graph TB'
            logger.warning(f"[系统架构生成] ⚠️ 缺少图表类型声明，添加默认类型: {default_type}")
            fixed_code = f'{default_type}\n' + fixed_code
        
        logger.debug(f"[系统架构生成] Mermaid 代码验证完成: diagram_type={diagram_type}, 输入行数={len(lines)}, 输出行数={len(fixed_lines)}, 最终长度={len(fixed_code)} 字符")
        return fixed_code
    
    def generate_tech_stack_llm(
        self,
        dependency_info: Dict,
        statistics: Dict,
        repo_path: str
    ) -> Dict:
        """使用 LLM 生成技术栈说明"""
        import requests
        from app.config.settings import settings
        
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

1. core_technologies: 核心技术说明（200-300字）
2. key_dependencies_table: 关键依赖表格
3. technology_choices: 技术选择说明（150-200字）

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
            
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
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
    
    def generate_component_relationships_llm(
        self,
        dependencies: Dict,
        module_structure: Dict,
        repo_name: str
    ) -> Dict:
        """使用 LLM 生成组件关系说明"""
        import requests
        from app.config.settings import settings
        
        context = f"""
## 项目组件关系

项目名称: {repo_name}

## 模块列表

"""
        for module in module_structure.get('modules', [])[:15]:
            context += f"- {module['name']}: {module['files_count']} 个文件, {module['lines']} 行代码\n"
        
        if dependencies.get('nodes'):
            context += "\n## 依赖关系\n"
            context += f"节点数: {len(dependencies.get('nodes', []))}\n"
            context += f"边数: {len(dependencies.get('edges', []))}\n"
        
        prompt = f"""请基于以下代码仓库的模块和依赖信息，生成组件关系说明。请以 JSON 格式返回：

{context}

请生成以下内容（JSON 格式）：

1. service_dependencies: 服务依赖说明（150-200字）
2. component_relationships: 组件关系描述（200-300字）
3. data_flow: 数据流说明（100-150字）

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
            
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
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
    
    def generate_deployment_models_llm(
        self,
        deployment_info: Dict,
        repo_path: str,
        repo_name: str
    ) -> Dict:
        """使用 LLM 生成部署模型说明"""
        import requests
        from app.config.settings import settings
        
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

1. standalone_server: 独立服务器部署说明（100-150字）
2. docker_deployment: Docker 部署说明（100-150字）
3. build_features: 构建特性说明（如果有）
4. deployment_steps: 部署步骤列表（3-5个步骤）

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
            
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
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
    
    def generate_getting_started_llm(
        self,
        readme_content: str,
        dependency_info: Dict,
        repo_path: str,
        repo_name: str
    ) -> Dict:
        """使用 LLM 生成快速开始指南"""
        import requests
        from app.config.settings import settings
        
        context = f"""
## 项目信息

项目名称: {repo_name}
项目路径: {repo_path}

## README 内容（前5000字符）

{readme_content[:5000]}

## 依赖信息

"""
        if dependency_info.get('python'):
            deps = dependency_info['python'][:10]
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

1. prerequisites: 前置要求列表（至少2-4个）
2. installation_steps: 安装步骤列表（至少4-6个详细步骤），**必须**包含：
   - 依赖安装步骤（如 npm install, pip install 等）
   - 配置步骤（如环境变量设置、配置文件修改等）
   - **运行项目步骤（必须包含具体的启动命令，如 npm start, python app.py, yarn dev 等）**
   - 验证步骤（如访问 http://localhost:3000 等）
3. key_endpoints: 关键端点列表（如果有 API 或 Web 服务）
4. quick_start_summary: 快速开始总结（150-200字）
5. **run_project_command: 运行项目的具体命令（字符串，如 "npm start" 或 "python app.py"）** - **必须填写，不能为空**

**重要要求**：
- ✅ 必须基于实际的 README 内容和项目配置生成，不要编造
- ✅ 提供**具体的命令和操作步骤**，不能使用占位符或通用说明
- ✅ 如果 README 中有启动命令，必须包含在 installation_steps 和 run_project_command 中
- ✅ 如果项目支持 Docker，必须包含 Docker 启动步骤和命令
- ✅ **run_project_command 必须填写具体的可执行命令，不能为空字符串或占位符**
- ✅ **installation_steps 中的每个步骤必须包含具体的命令，不能只是描述性文字**

返回格式示例：
{{
  "prerequisites": [
    {{"item": "Node.js 18+", "description": "需要 Node.js 18 或更高版本"}}
  ],
  "installation_steps": [
    {{"step": "安装依赖", "description": "运行 npm install 安装项目依赖"}},
    {{"step": "配置环境变量", "description": "复制 .env.example 到 .env 并配置必要的环境变量"}},
    {{"step": "运行项目", "description": "执行 npm start 启动开发服务器，访问 http://localhost:3000"}}
  ],
  "key_endpoints": [
    {{"endpoint": "/api/health", "method": "GET", "description": "健康检查端点"}}
  ],
  "quick_start_summary": "...",
  "run_project_command": "npm start"
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
            
            # 记录 LLM 原始响应（前500字符，用于调试）
            logger.debug(f"[快速开始指南] LLM 原始响应（前500字符）: {content[:500]}...")
            logger.info(f"[快速开始指南] LLM 原始响应长度: {len(content)} 字符")
            
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
                logger.debug("[快速开始指南] 移除了 ```json 前缀")
            elif content.startswith("```"):
                content = content[3:]
                logger.debug("[快速开始指南] 移除了 ``` 前缀")
            if content.endswith("```"):
                content = content[:-3]
                logger.debug("[快速开始指南] 移除了 ``` 后缀")
            content = content.strip()
            
            # 记录清理后的内容（前300字符）
            logger.debug(f"[快速开始指南] 清理后的 JSON（前300字符）: {content[:300]}...")
            
            try:
                getting_started_data = json.loads(content)
                logger.info(f"[快速开始指南] ✅ JSON 解析成功")
            except json.JSONDecodeError as e:
                logger.error(f"[快速开始指南] ❌ JSON 解析失败: {e}")
                logger.error(f"[快速开始指南] 解析失败的 JSON 内容（前500字符）: {content[:500]}...")
                raise
            
            # 记录解析结果
            logger.info(f"[快速开始指南] 📊 解析结果 - "
                       f"prerequisites={len(getting_started_data.get('prerequisites', []))}, "
                       f"installation_steps={len(getting_started_data.get('installation_steps', []))}, "
                       f"run_project_command={getting_started_data.get('run_project_command', 'N/A')}")
            
            # 验证和修复数据格式
            # 1. 确保 run_project_command 存在且不为空
            original_command = getting_started_data.get('run_project_command', '')
            logger.debug(f"[快速开始指南] run_project_command 原始值: '{original_command}'")
            
            if 'run_project_command' not in getting_started_data or not getting_started_data.get('run_project_command') or len(getting_started_data.get('run_project_command', '').strip()) < 3:
                # 尝试从 installation_steps 中提取运行命令
                run_command = None
                for step in getting_started_data.get('installation_steps', []):
                    step_desc = step.get('description', '') or step.get('step', '')
                    # 查找常见的启动命令
                    import re
                    patterns = [
                        r'(npm\s+start)',
                        r'(yarn\s+start)',
                        r'(python\s+[\w/]+\.py)',
                        r'(python\s+-m\s+[\w.]+)',
                        r'(node\s+[\w/]+\.js)',
                        r'(go\s+run)',
                        r'(cargo\s+run)',
                        r'(docker\s+compose\s+up)',
                        r'(docker\s+run)'
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, step_desc, re.IGNORECASE)
                        if match:
                            run_command = match.group(1)
                            break
                    if run_command:
                        break
                
                if not run_command:
                    # 根据项目类型推断默认命令
                    if has_package_json:
                        run_command = "npm start"
                        logger.debug("[快速开始指南] 根据 package.json 推断命令: npm start")
                    elif has_requirements:
                        run_command = "python app.py"
                        logger.debug("[快速开始指南] 根据 requirements.txt 推断命令: python app.py")
                    elif has_cargo_toml:
                        run_command = "cargo run"
                        logger.debug("[快速开始指南] 根据 Cargo.toml 推断命令: cargo run")
                    else:
                        run_command = "根据项目类型运行相应的启动命令"
                        logger.warning("[快速开始指南] 无法推断项目类型，使用默认占位符")
                
                getting_started_data['run_project_command'] = run_command
                logger.warning(f"[快速开始指南] ⚠️ run_project_command 为空或无效（原始值: '{original_command}'），已补充: {run_command}")
            else:
                logger.info(f"[快速开始指南] ✅ run_project_command 有效: {getting_started_data.get('run_project_command')}")
            
            # 2. 验证 installation_steps 中是否包含运行命令
            installation_steps = getting_started_data.get('installation_steps', [])
            has_run_step = False
            for step in installation_steps:
                step_desc = (step.get('description', '') or step.get('step', '')).lower()
                if any(keyword in step_desc for keyword in ['运行', '启动', 'start', 'run', 'dev', 'serve']):
                    has_run_step = True
                    break
            
            if not has_run_step and installation_steps:
                # 添加运行步骤
                run_command = getting_started_data.get('run_project_command', 'npm start')
                installation_steps.append({
                    "step": "运行项目",
                    "description": f"执行 {run_command} 启动项目"
                })
                getting_started_data['installation_steps'] = installation_steps
                logger.info(f"已添加运行步骤: {run_command}")
            
            logger.info(f"[快速开始指南] ✅ 快速开始指南生成成功: "
                       f"prerequisites={len(getting_started_data.get('prerequisites', []))}, "
                       f"installation_steps={len(installation_steps)}, "
                       f"run_project_command={getting_started_data.get('run_project_command', 'N/A')}")
            
            # 记录最终数据结构
            logger.debug(f"[快速开始指南] 📦 最终数据结构: {list(getting_started_data.keys())}")
            
            return getting_started_data
        except Exception as e:
            logger.error(f"生成快速开始指南失败: {e}")
            return {
                "prerequisites": [],
                "installation_steps": [],
                "key_endpoints": [],
                "quick_start_summary": "快速开始指南生成失败"
            }
