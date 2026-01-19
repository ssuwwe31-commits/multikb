"""
代码架构分析模块
负责提取架构详情、检测架构模式、生成架构建议等
"""

import os
import re
import ast
import json
import hashlib
from typing import Dict, List, Optional
from collections import defaultdict

from app.core.logging import logger
from app.services.code_diagram_generator import CodeDiagramGenerator


class CodeArchitectureAnalyzer:
    """代码架构分析器"""
    
    def __init__(self, diagram_generator: Optional[CodeDiagramGenerator] = None, db=None, repository_id: Optional[int] = None):
        """
        初始化架构分析器
        
        Args:
            diagram_generator: 图表生成器（可选，如果提供则使用，否则创建新实例）
            db: 数据库会话（用于 LLM 缓存）
            repository_id: 仓库ID（用于 LLM 缓存关联）
        """
        self.diagram_generator = diagram_generator or CodeDiagramGenerator()
        self.db = db
        self.repository_id = repository_id
        self._llm_service = None  # 延迟初始化
    
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
        
        # 提取 API 路由文件和详细信息（增强检测：支持更多路由定义方式）
        route_patterns = [
            '/api/', '/routes/', '/endpoints/', '/controllers/', '/handlers/',
            'router.', 'app.get', 'app.post', 'app.put', 'app.delete', 'app.patch',
            '@router', '@app.route', '@route', 'fastapi', 'express', 'koa', 'hapi',
            'flask', 'django.urls', 'spring.web', 'gin.', 'echo.', 'fiber.'
        ]
        
        for file_data in analyzed_files:
            path = file_data['file_path']
            path_lower = path.lower()
            content = file_data.get('content', '').lower()
            
            # 检查路径模式
            is_route_file = any(pattern in path_lower for pattern in route_patterns[:5])
            
            # 检查代码内容中的路由定义模式
            if not is_route_file and content:
                is_route_file = any(pattern in content[:2000] for pattern in route_patterns[5:])  # 只检查前2000字符
            
            # 检查文件名模式
            if not is_route_file:
                file_name = os.path.basename(path_lower)
                route_file_names = ['route', 'router', 'api', 'endpoint', 'controller', 'handler']
                is_route_file = any(name in file_name for name in route_file_names)
            
            if is_route_file:
                # 检查是否为代码文件（有 symbols 数据表示已解析）
                if file_data.get('symbols') or file_data.get('language'):
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
                    
                    # 使用 LLM 增强的 API 端点检测
                    endpoints = self.extract_api_endpoints_with_llm(file_data, repo_path)
                    architecture['api_endpoints_detail'].extend(endpoints)
        
        # 提取服务文件和详细信息
        for file_data in analyzed_files:
            path = file_data['file_path']
            if '/service' in path.lower() or '/services/' in path:
                # 检查是否为代码文件（有 symbols 数据表示已解析）
                if file_data.get('symbols') or file_data.get('language'):
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
                # 检查是否为代码文件（有 symbols 数据表示已解析）
                if file_data.get('symbols') or file_data.get('language'):
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
        detected_storage = self._detect_storage_from_code(analyzed_files, repo_path)
        logger.debug(f"[架构提取] 从代码中检测到 {len(detected_storage)} 个存储系统: {[s.get('name') for s in detected_storage]}")
        
        # 方法3: 使用 LLM 增强检测（如果检测结果较少）
        if len(detected_storage) < 2:
            logger.info(f"[架构提取] 存储系统检测结果较少 ({len(detected_storage)} 个)，使用 LLM 增强检测")
            llm_storage = self.detect_storage_systems_with_llm(analyzed_files, repo_path)
            for storage in llm_storage:
                # 避免重复添加
                if not any(s.get('name') == storage.get('name') for s in detected_storage):
                    detected_storage.append(storage)
                    logger.info(f"[架构提取] ✅ LLM 补充检测到存储系统: {storage.get('name')}")
        
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
    
    def _detect_storage_from_code(self, analyzed_files: List[Dict], repo_path: Optional[str] = None) -> List[Dict]:
        """
        从代码文件中直接检测存储系统（通过导入语句、配置文件等）
        
        Args:
            analyzed_files: 已分析的文件列表（file_path 可能是相对路径）
            repo_path: 仓库本地路径（用于构建完整文件路径）
            
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
        
        # 使用传入的 repo_path 来构建完整路径（如果 file_path 是相对路径）
        repo_path_for_storage = repo_path
        
        for file_data in analyzed_files:
            file_path = file_data.get('file_path', '')
            content = file_data.get('content', '')
            
            # 构建完整路径（如果 file_path 是相对路径）
            full_path = file_path
            if not os.path.isabs(file_path) and repo_path_for_storage:
                full_path = os.path.join(repo_path_for_storage, file_path)
            elif not os.path.isabs(file_path):
                # 如果无法确定 repo_path，尝试使用 file_path 本身
                full_path = file_path
            
            # 如果没有 content，尝试从文件读取
            if not content:
                files_without_content += 1
                # 尝试读取文件内容（只读取前1000行，避免内存问题）
                try:
                    # 先尝试完整路径，再尝试相对路径
                    read_path = full_path if os.path.exists(full_path) else file_path
                    if os.path.exists(read_path):
                        with open(read_path, 'r', encoding='utf-8', errors='ignore') as f:
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
            file_lower = file_path.lower()
            is_config_file = any(ext in file_lower for ext in ['.env', 'config', 'settings', 'database', 'package.json', 'requirements.txt', 'pom.xml', 'build.gradle', 'composer.json', 'gemfile', 'cargo.toml', 'go.mod'])
            
            if is_config_file:
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
                
                # 额外检查：从 package.json, requirements.txt 等依赖文件中检测
                if 'package.json' in file_lower or 'package-lock.json' in file_lower:
                    # Node.js 项目，检查数据库驱动
                    npm_db_patterns = {
                        'PostgreSQL': ['pg', 'postgres', 'postgresql', 'sequelize', 'typeorm'],
                        'MySQL': ['mysql', 'mysql2', 'sequelize', 'typeorm'],
                        'SQLite': ['sqlite3', 'better-sqlite3', 'sequelize', 'typeorm'],
                        'MongoDB': ['mongodb', 'mongoose'],
                        'Redis': ['redis', 'ioredis', 'node-redis'],
                        'Elasticsearch': ['elasticsearch', '@elastic/elasticsearch'],
                    }
                    for db_name, patterns in npm_db_patterns.items():
                        for pattern in patterns:
                            if f'"{pattern}"' in content or f"'{pattern}'" in content or f'`{pattern}`' in content:
                                if db_name not in detected_names:
                                    detected_names.add(db_name)
                                    storage_type = '数据库' if db_name not in ['Redis'] else '缓存'
                                    storage_systems.append({
                                        'name': db_name,
                                        'type': storage_type,
                                        'count': 1,
                                        'source': 'package.json',
                                        'file': file_path
                                    })
                                    logger.info(f"[架构提取] 🔍   从 package.json 检测到: {db_name} (模式: {pattern})")
                                    break
                
                elif 'requirements.txt' in file_lower or 'pyproject.toml' in file_lower or 'setup.py' in file_lower:
                    # Python 项目，检查数据库驱动
                    python_db_patterns = {
                        'PostgreSQL': ['psycopg2', 'psycopg', 'asyncpg', 'sqlalchemy'],
                        'MySQL': ['pymysql', 'mysql-connector', 'mysqlclient', 'sqlalchemy'],
                        'SQLite': ['sqlite3'],
                        'MongoDB': ['pymongo', 'motor', 'mongoengine'],
                        'Redis': ['redis', 'hiredis'],
                        'Elasticsearch': ['elasticsearch'],
                    }
                    for db_name, patterns in python_db_patterns.items():
                        for pattern in patterns:
                            if pattern.lower() in content.lower():
                                if db_name not in detected_names:
                                    detected_names.add(db_name)
                                    storage_type = '数据库' if db_name not in ['Redis'] else '缓存'
                                    storage_systems.append({
                                        'name': db_name,
                                        'type': storage_type,
                                        'count': 1,
                                        'source': 'requirements.txt',
                                        'file': file_path
                                    })
                                    logger.info(f"[架构提取] 🔍   从依赖文件检测到: {db_name} (模式: {pattern})")
                                    break
        
        logger.debug(f"[架构提取] 代码检测完成: 有内容={files_with_content}, 无内容={files_without_content}, 存储系统={len(storage_systems)}")
        return storage_systems
    
    def _parse_dependency_files(self, repo_path: str) -> Dict:
        """解析依赖文件"""
        dependencies = {}
        
        # Python
        req_file = os.path.join(repo_path, 'requirements.txt')
        if os.path.exists(req_file):
            try:
                with open(req_file, 'r', encoding='utf-8', errors='ignore') as f:
                    dependencies['requirements.txt'] = f.read()[:2000]  # 限制大小
            except:
                pass
        
        # Node.js
        package_file = os.path.join(repo_path, 'package.json')
        if os.path.exists(package_file):
            try:
                with open(package_file, 'r', encoding='utf-8', errors='ignore') as f:
                    dependencies['package.json'] = f.read()[:2000]
            except:
                pass
        
        # Java
        pom_file = os.path.join(repo_path, 'pom.xml')
        if os.path.exists(pom_file):
            try:
                with open(pom_file, 'r', encoding='utf-8', errors='ignore') as f:
                    dependencies['pom.xml'] = f.read()[:3000]
            except:
                pass
        
        return dependencies
    
    def _extract_config_files(self, repo_path: str, max_size: int = 5000) -> Dict:
        """提取配置文件内容"""
        config_files = {}
        config_patterns = ['.env', 'config', 'settings', 'application.properties', 'application.yml']
        
        for root, dirs, files in os.walk(repo_path):
            # 跳过忽略的目录
            dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', 'venv', '.venv']]
            
            for file in files:
                if any(pattern in file.lower() for pattern in config_patterns):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()[:max_size]
                            rel_path = os.path.relpath(file_path, repo_path)
                            config_files[rel_path] = content
                    except:
                        pass
        
        return config_files
    
    def detect_storage_systems_with_llm(self, analyzed_files: List[Dict], repo_path: str) -> List[Dict]:
        """
        使用 LLM 增强存储系统检测
        
        策略:
        1. 先使用规则检测（快速）
        2. 如果检测结果较少，使用 LLM 分析依赖和配置
        3. 利用 qwen3-coder 的长上下文能力分析多个文件
        """
        # 1. 规则检测（现有逻辑）
        storage_systems = self._detect_storage_from_code(analyzed_files, repo_path)
        
        # 2. 如果检测结果较少，使用 LLM 补充
        if len(storage_systems) >= 2:
            return storage_systems
        
        try:
            dependencies = self._parse_dependency_files(repo_path)
            
            # 提取配置文件内容（限制大小）
            config_files = self._extract_config_files(repo_path, max_size=5000)
            
            # 提取关键代码文件中的导入语句（前 100 个文件）
            import_statements = []
            for file_data in analyzed_files[:100]:
                for imp in file_data.get('imports', []):
                    module = imp.get('module', '')
                    if any(kw in module.lower() for kw in ['db', 'database', 'cache', 'redis', 'mq', 'queue', 'storage']):
                        import_statements.append({
                            'file': file_data.get('file_path', ''),
                            'import': module
                        })
            
            # 3. 使用 LLM 分析
            prompt = f"""基于以下项目依赖、配置和导入语句，识别所有使用的存储系统（数据库、缓存、消息队列等）。

依赖包:
{json.dumps(dependencies, ensure_ascii=False, indent=2)}

配置文件内容:
{json.dumps(config_files, ensure_ascii=False, indent=2)}

关键导入语句:
{json.dumps(import_statements[:50], ensure_ascii=False, indent=2)}

请识别：
1. 数据库（MySQL、PostgreSQL、MongoDB、SQLite、Redis、InfluxDB、TimescaleDB 等）
2. 缓存系统（Redis、Memcached、Hazelcast 等）
3. 消息队列（RabbitMQ、Kafka、NATS、Pulsar、Celery 等）
4. 搜索引擎（Elasticsearch、OpenSearch、Solr、Meilisearch 等）
5. 对象存储（S3、MinIO、OSS、Azure Blob、GCS 等）
6. 时序数据库（InfluxDB、TimescaleDB、Prometheus 等）
7. 图数据库（Neo4j、NebulaGraph、ArangoDB 等）

返回 JSON 格式：
{{
  "storage_systems": [
    {{
      "name": "MySQL",
      "type": "数据库",
      "evidence": "检测到 pymysql 依赖和 DATABASE_URL 配置",
      "confidence": 0.9
    }}
  ]
}}

注意：
- 只返回有明确证据的存储系统
- confidence 表示置信度（0-1）
- evidence 说明检测依据
"""
            
            # 优先使用 Function Calling（更稳定）
            llm_service = self._get_llm_service()
            cache_key = f"storage_systems:{repo_path}:{hashlib.md5(str(dependencies).encode()).hexdigest()[:16]}"
            
            # 尝试使用 Function Calling
            try:
                from app.services.llm_tools_definitions import STORAGE_SYSTEMS_TOOL
                
                # 限制 JSON 数据的大小，确保 prompt < 8K（为 Function Calling 预留空间）
                # 注意：不能简单截断，会导致 JSON 不完整，Function Calling 失败
                MAX_STORAGE_PROMPT_LENGTH = 7500  # 预留 2K 给 prompt 模板和工具定义（更保守）
                PROMPT_TEMPLATE_LENGTH = 200  # prompt 模板的固定长度
                MAX_DATA_LENGTH = MAX_STORAGE_PROMPT_LENGTH - PROMPT_TEMPLATE_LENGTH  # 实际可用数据长度
                
                # 智能限制各部分大小，确保总和不超过限制
                # 分配比例：依赖包 40%，配置文件 30%，导入语句 30%
                max_deps_length = int(MAX_DATA_LENGTH * 0.4)
                max_config_length = int(MAX_DATA_LENGTH * 0.3)
                max_imports_length = int(MAX_DATA_LENGTH * 0.3)
                
                # 1. 限制依赖包
                dependencies_str = json.dumps(dependencies, ensure_ascii=False, indent=2)
                if len(dependencies_str) > max_deps_length:
                    # 逐步减少依赖包数量，直到符合长度限制
                    limited_deps = {}
                    for lang, deps in dependencies.items():
                        if isinstance(deps, list):
                            # 从 20 个开始，逐步减少
                            for count in [20, 15, 10, 5]:
                                limited_deps[lang] = deps[:count]
                                test_str = json.dumps(limited_deps, ensure_ascii=False, indent=2)
                                if len(test_str) <= max_deps_length:
                                    break
                        else:
                            limited_deps[lang] = deps
                    dependencies_str = json.dumps(limited_deps, ensure_ascii=False, indent=2)
                    if len(dependencies_str) > max_deps_length:
                        # 如果还是太长，截断字符串（保留开头）
                        dependencies_str = dependencies_str[:max_deps_length-10] + "\n  ..."
                
                # 2. 限制配置文件
                config_files_str = json.dumps(config_files, ensure_ascii=False, indent=2)
                if len(config_files_str) > max_config_length:
                    # 逐步减少配置文件数量
                    for count in [5, 3, 2, 1]:
                        limited_configs = config_files[:count] if isinstance(config_files, list) else config_files
                        test_str = json.dumps(limited_configs, ensure_ascii=False, indent=2)
                        if len(test_str) <= max_config_length:
                            config_files_str = test_str
                            break
                    if len(config_files_str) > max_config_length:
                        config_files_str = config_files_str[:max_config_length-10] + "\n  ..."
                
                # 3. 限制导入语句
                import_statements_str = json.dumps(import_statements[:30], ensure_ascii=False, indent=2)
                if len(import_statements_str) > max_imports_length:
                    # 逐步减少导入语句数量
                    for count in [20, 15, 10, 5]:
                        test_str = json.dumps(import_statements[:count], ensure_ascii=False, indent=2)
                        if len(test_str) <= max_imports_length:
                            import_statements_str = test_str
                            break
                    if len(import_statements_str) > max_imports_length:
                        import_statements_str = import_statements_str[:max_imports_length-10] + "\n  ..."
                
                fc_prompt = f"""基于以下项目依赖、配置和导入语句，识别所有使用的存储系统。

依赖包:
{dependencies_str}

配置文件内容:
{config_files_str}

关键导入语句:
{import_statements_str}

请识别：数据库、缓存、消息队列、搜索引擎、对象存储、时序数据库、图数据库等。
只返回有明确证据的存储系统。"""
                
                # 最终检查：如果仍然超过限制，直接使用 prompt-based（不尝试 Function Calling）
                if len(fc_prompt) > MAX_STORAGE_PROMPT_LENGTH:
                    logger.warning(f"[存储检测] Prompt 长度 {len(fc_prompt)} 超过 Function Calling 限制 {MAX_STORAGE_PROMPT_LENGTH}，直接使用 prompt-based")
                    # 跳过 Function Calling，直接使用 prompt-based
                    raise ValueError("Prompt 过长，跳过 Function Calling")
                
                try:
                    llm_result_dict = llm_service.call_llm_with_function_calling(
                        prompt=fc_prompt,
                        tools=[STORAGE_SYSTEMS_TOOL],
                        cache_key=cache_key,
                        task_type="storage_systems"  # 指定任务类型，用于优化代码总结
                    )
                    
                    # Function Calling 返回的是字典，直接使用
                    llm_storage = llm_result_dict.get('storage_systems', [])
                except ValueError as e:
                    # Prompt 过长或其他原因导致 Function Calling 不可用，直接使用 prompt-based
                    if "Prompt 过长" in str(e) or "跳过 Function Calling" in str(e):
                        logger.info(f"[存储检测] 跳过 Function Calling，直接使用 prompt-based: {e}")
                        raise  # 重新抛出，让外层 catch 处理
                    else:
                        raise  # 其他错误，继续抛出
                logger.debug(f"[存储检测] Function Calling 检测到 {len(llm_storage)} 个存储系统")
                
                # 合并结果（去重，保留置信度高的）
                existing_names = {s.get('name') for s in storage_systems}
                for storage in llm_storage:
                    if storage.get('name') not in existing_names and storage.get('confidence', 0) > 0.6:
                        storage_systems.append({
                            'name': storage.get('name'),
                            'type': storage.get('type', 'unknown'),
                            'count': 1
                        })
                
                return storage_systems
                
            except Exception as e:
                # 降级到 prompt-based 方式
                logger.warning(f"[存储检测] Function Calling 失败，降级到 prompt-based: {e}")
                
                # 构建 prompt-based 的 prompt（使用完整数据）
                prompt = f"""基于以下项目依赖、配置和导入语句，识别所有使用的存储系统。

依赖包:
{json.dumps(dependencies, ensure_ascii=False, indent=2)}

配置文件内容:
{json.dumps(config_files, ensure_ascii=False, indent=2)}

关键导入语句:
{json.dumps(import_statements[:50], ensure_ascii=False, indent=2)}

请识别：数据库、缓存、消息队列、搜索引擎、对象存储、时序数据库、图数据库等。
只返回有明确证据的存储系统。

请以 JSON 格式返回，格式：
{{
  "storage_systems": [
    {{"name": "存储系统名称", "type": "类型", "confidence": 0.8}}
  ]
}}"""
                
                llm_result = llm_service.call_llm_with_cache(prompt, cache_key=cache_key)
                
                # 调试：记录 LLM 原始响应（如果响应异常短）
                # 区分空结果（正常）和错误响应（异常）
                if len(llm_result) < 100:
                    # 尝试解析响应，判断是否是有效的空结果
                    try:
                        # 清理 markdown 代码块标记
                        cleaned_result = llm_result.strip()
                        if cleaned_result.startswith('```json'):
                            cleaned_result = cleaned_result[7:]
                        if cleaned_result.startswith('```'):
                            cleaned_result = cleaned_result[3:]
                        if cleaned_result.endswith('```'):
                            cleaned_result = cleaned_result[:-3]
                        cleaned_result = cleaned_result.strip()
                        
                        parsed = json.loads(cleaned_result)
                        if isinstance(parsed, dict) and 'storage_systems' in parsed:
                            if parsed['storage_systems'] == []:
                                # 这是有效的空结果，说明确实没有检测到存储系统
                                logger.debug(f"[存储检测] LLM 检测到 0 个存储系统（可能规则检测已找到，或确实没有）")
                            else:
                                # 有存储系统但响应很短，可能是截断
                                logger.warning(f"[存储检测] ⚠️ LLM 响应异常短（仅{len(llm_result)}字符），但包含存储系统")
                        else:
                            logger.warning(f"[存储检测] ⚠️ LLM 响应格式异常，响应: {llm_result[:100]}")
                    except json.JSONDecodeError:
                        # 无法解析 JSON，可能是错误响应
                        logger.error(f"[存储检测] ❌ LLM 响应无法解析为 JSON，原始响应: {repr(llm_result)}")
                    except Exception as e:
                        logger.warning(f"[存储检测] ⚠️ 解析 LLM 响应时出错: {e}, 响应: {llm_result[:100]}")
                
                parsed_result = llm_service.parse_json_response(llm_result)
                llm_storage = parsed_result.get('storage_systems', [])
                
                # 合并结果（去重，保留置信度高的）- 降级到 prompt-based 时才执行
                existing_names = {s.get('name') for s in storage_systems}
                for storage in llm_storage:
                    if storage.get('name') not in existing_names and storage.get('confidence', 0) > 0.6:
                        storage_systems.append({
                            'name': storage.get('name'),
                            'type': storage.get('type', '未知'),
                            'count': 1,
                            'source': 'llm',
                            'confidence': storage.get('confidence', 0.8)
                        })
                        existing_names.add(storage.get('name'))
                
                logger.info(f"[存储检测] LLM 补充检测到 {len(llm_storage)} 个存储系统")
                return storage_systems
        except Exception as e:
            logger.warning(f"[存储检测] LLM 检测失败: {e}")
            # 降级：继续使用规则检测的结果
        
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
                                        
            elif language in ['javascript', 'typescript']:
                # 支持 Express, Fastify, Koa 等 Node.js 框架
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # 使用正则表达式匹配路由定义
                # Express: app.get('/path', handler), router.get('/path', handler)
                # Fastify: fastify.get('/path', handler)
                # Koa: router.get('/path', handler)
                route_patterns = [
                    (r'(?:app|router|fastify)\.(get|post|put|delete|patch|options|head)\s*\(\s*["\']([^"\']+)["\']', 'express'),
                    (r'@(Get|Post|Put|Delete|Patch|Options|Head)\s*\(\s*["\']([^"\']+)["\']', 'nestjs'),
                    (r'@(get|post|put|delete|patch)\s*\(["\']([^"\']+)["\']', 'decorator'),
                ]
                
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    for pattern, framework in route_patterns:
                        matches = re.finditer(pattern, line, re.IGNORECASE)
                        for match in matches:
                            http_method = match.group(1).upper()
                            route_path = match.group(2)
                            
                            # 查找对应的处理函数（下一行或几行内）
                            handler_name = None
                            for j in range(i, min(i + 5, len(lines))):
                                func_match = re.search(r'(?:function|const|async\s+function)\s+(\w+)|(\w+)\s*[:=]\s*(?:async\s*)?\(', lines[j])
                                if func_match:
                                    handler_name = func_match.group(1) or func_match.group(2)
                                    break
                            
                            endpoints.append({
                                'method': http_method,
                                'path': route_path,
                                'function_name': handler_name or 'anonymous',
                                'parameters': [],
                                'docstring': '',
                                'line': i,
                                'file_path': file_path,
                                'framework': framework
                            })
                            break  # 每行只匹配一个模式，避免重复
                        if endpoints and endpoints[-1].get('line') == i:
                            break  # 如果已经匹配到，跳出模式循环
                            
        except Exception as e:
            logger.warning(f"提取 API 端点详情失败: {file_path}, {e}")
        
        return endpoints
    
    def _get_llm_service(self):
        """获取 LLM 增强服务（延迟初始化）"""
        if self._llm_service is None:
            from app.services.llm_enhancement_service import LLMEnhancementService
            self._llm_service = LLMEnhancementService(db=self.db, repository_id=self.repository_id)
        return self._llm_service
    
    def _looks_like_route_file(self, file_path: str, file_data: Dict) -> bool:
        """判断文件是否看起来像路由文件"""
        path_lower = file_path.lower()
        route_keywords = ['route', 'api', 'endpoint', 'controller', 'handler', 'view']
        return any(kw in path_lower for kw in route_keywords)
    
    def extract_api_endpoints_with_llm(self, file_data: Dict, repo_path: str) -> List[Dict]:
        """
        使用 LLM 增强 API 端点检测
        
        策略:
        1. 先使用规则检测（快速）
        2. 如果检测结果为空或较少，使用 LLM 分析文件内容
        3. LLM 识别非标准路由定义方式
        4. 利用 qwen3-coder 的长上下文能力（256K tokens）
        """
        # 1. 规则检测（现有逻辑）
        endpoints = self.extract_api_endpoints_detail(file_data, repo_path)
        
        # 2. 如果检测为空或较少，使用 LLM 补充
        # 条件：检测结果为空，或者文件看起来像路由文件但检测结果很少
        file_path = file_data.get('file_path', '')
        should_use_llm = (
            not endpoints or 
            (len(endpoints) < 2 and self._looks_like_route_file(file_path, file_data))
        )
        
        if not should_use_llm:
            return endpoints
        
        full_path = os.path.join(repo_path, file_path)
        
        if not os.path.exists(full_path):
            return endpoints
        
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Function Calling 的字符数限制（预留 1K 给 prompt 模板）
            # 注意：10K 字符是临界点，降低到 8.5K 更安全
            MAX_CHARS_FOR_FUNCTION_CALLING = 8500  # 9.5K - 1K 预留（更保守）
            
            # ========== 旧的行数限制逻辑已注释（不再使用） ==========
            # qwen3-coder 支持 256K tokens 上下文，但 Function Calling 有 10K 字符限制
            # 对于大文件（> 8.5K 字符），现在使用 ReAct Agent 处理
            # 对于小文件（<= 8.5K 字符），直接使用完整内容
            # lines = content.split('\n')
            # max_lines = 6000  # 旧的行数限制，已不再使用
            
            # 优先使用 Function Calling（更稳定）
            llm_service = self._get_llm_service()
            
            # ========== 新策略：使用文件级 ReAct Agent 处理大文件 ==========
            # 策略：先检查字符数（针对 Function Calling），再检查行数（针对 prompt-based）
            if len(content) > MAX_CHARS_FOR_FUNCTION_CALLING:
                # 文件字符数超过 Function Calling 限制：使用文件级 ReAct Agent
                logger.info(f"[API检测] 文件字符数 {len(content)} 超过 Function Calling 限制 {MAX_CHARS_FOR_FUNCTION_CALLING}，使用文件级 ReAct Agent: {file_path}")
                
                try:
                    from app.services.file_level_react_agent import FileLevelReActAgent
                    
                    # 创建文件级 ReAct Agent
                    file_agent = FileLevelReActAgent(
                        repo_path=repo_path,
                        task_type="api_endpoints",
                        max_iterations=3,
                        llm_service=llm_service
                    )
                    
                    # 执行 ReAct 分析
                    react_result = file_agent.analyze(file_path)
                    
                    if react_result.get("success"):
                        llm_endpoints = react_result.get("extracted_results", [])
                        confidence = react_result.get("confidence", 0.0)
                        iterations = react_result.get("iterations", 1)
                        
                        logger.info(f"[API检测] ReAct Agent 完成: 迭代 {iterations} 次, 提取 {len(llm_endpoints)} 个端点, 置信度 {confidence:.2f}")
                        
                        # 合并结果（去重）
                        existing_paths = {(e.get('method'), e.get('path')) for e in endpoints}
                        for ep in llm_endpoints:
                            key = (ep.get('method'), ep.get('path'))
                            if key not in existing_paths:
                                endpoints.append({
                                    'method': ep.get('method', ''),
                                    'path': ep.get('path', ''),
                                    'function_name': ep.get('function_name', ''),
                                    'parameters': ep.get('parameters', []),
                                    'docstring': ep.get('description', ''),
                                    'line': ep.get('line', 0),
                                    'file_path': file_path
                                })
                                existing_paths.add(key)
                        
                        return endpoints
                    else:
                        error_msg = react_result.get('error', '未知错误')
                        logger.warning(f"[API检测] ❌ ReAct Agent 失败: {error_msg}，开始降级策略")
                        # 中期优化：改进降级策略（二次降级，分块处理）
                        sample_content = self._fallback_strategy(file_path, content, llm_service, repo_path)
                        
                except Exception as e:
                    logger.error(f"[API检测] ❌ ReAct Agent 初始化失败: {e}，开始降级策略", exc_info=True)
                    # 中期优化：改进降级策略（二次降级，分块处理）
                    sample_content = self._fallback_strategy(file_path, content, llm_service, repo_path)
                    
                    # ========== 旧代码已注释（不再使用智能采样） ==========
                    # # 降级到智能采样（旧方式，已废弃）
                    # sample_content = llm_service._extract_api_related_code(content, MAX_CHARS_FOR_FUNCTION_CALLING)
                    # logger.info(f"[API检测] 智能采样完成: {len(content)} -> {len(sample_content)} 字符")
            # ========== 旧的行数采样逻辑已注释（不再使用） ==========
            # 注意：如果文件字符数未超过 8.5K，但行数很多，现在直接使用完整内容
            # 因为 qwen3-coder 支持 256K tokens 上下文，可以处理大文件
            # elif len(lines) > max_lines:
            #     # 超大文件（行数多但字符数未超限）：保留开头、中间关键部分、结尾
            #     head_lines = 2000  # 前 2000 行
            #     tail_lines = 2000  # 后 2000 行
            #     middle_sample = 2000  # 中间采样 2000 行
            #     
            #     # 从中间均匀采样
            #     middle_indices = range(
            #         head_lines, 
            #         len(lines) - tail_lines, 
            #         max(1, (len(lines) - head_lines - tail_lines) // middle_sample)
            #     )
            #     middle_lines = [lines[i] for i in middle_indices[:middle_sample]]
            #     
            #     sample_content = '\n'.join(
            #         lines[:head_lines] + 
            #         [f'\n# ... (省略中间 {len(lines) - head_lines - tail_lines - len(middle_lines)} 行) ...\n'] + 
            #         middle_lines +
            #         [f'\n# ... (省略中间部分) ...\n'] + 
            #         lines[-tail_lines:]
            #     )
            #     logger.info(f"[API检测] 文件过大 ({len(lines)} 行)，采样分析 (前{head_lines}+中{len(middle_lines)}+后{tail_lines}行): {file_path}")
            else:
                # 文件大小合适（字符数 <= 8.5K）：直接使用完整文件
                sample_content = content
                # 计算行数用于日志（不再用于采样决策）
                lines = content.split('\n')
                logger.debug(f"[API检测] 分析完整文件 ({len(lines)} 行, {len(content)} 字符): {file_path}")
            
            # ========== 以下代码仅用于小文件（< 8.5K 字符）或 ReAct Agent 失败后的降级 ==========
            # 注意：大文件（> 8.5K 字符）应该使用 ReAct Agent（上面的逻辑），不应该执行到这里
            # 如果执行到这里，说明：
            #   1. 文件较小（<= 8.5K 字符）：直接使用 Function Calling
            #   2. ReAct Agent 失败：降级到 prompt-based（使用完整内容）
            
            cache_key = f"api_endpoints:{file_path}:{hashlib.md5(content.encode()).hexdigest()[:16]}"
            
            # ========== Function Calling 逻辑（保留用于小文件和降级场景） ==========
            # 注意：此逻辑仅用于小文件（<= 8.5K 字符）或 ReAct Agent 失败后的降级
            # 大文件（> 8.5K 字符）应该使用 ReAct Agent（上面的逻辑），不应该执行到这里
            # 尝试使用 Function Calling（仅适用于小文件或降级场景）
            try:
                from app.services.llm_tools_definitions import API_ENDPOINTS_TOOL
                
                prompt = f"""分析以下代码文件，识别所有 API 端点（HTTP 路由）。

文件路径: {file_path}
代码内容:
```python
{sample_content}
```

请识别所有 HTTP 端点（GET、POST、PUT、DELETE、PATCH 等）。
支持 FastAPI、Flask、Django、Gradio、Streamlit、Tornado、Sanic 等框架。
如果文件不是路由文件，返回空数组。"""
                
                llm_result_dict = llm_service.call_llm_with_function_calling(
                    prompt=prompt,
                    tools=[API_ENDPOINTS_TOOL],
                    cache_key=cache_key,
                    task_type="api_endpoints"  # 指定任务类型，用于优化代码总结
                )
                
                # Function Calling 返回的是字典，直接使用
                llm_endpoints = llm_result_dict.get('endpoints', [])
                logger.debug(f"[API检测] Function Calling 检测到 {len(llm_endpoints)} 个端点: {file_path}")
                
                # 合并结果（去重）
                existing_paths = {(e.get('method'), e.get('path')) for e in endpoints}
                for ep in llm_endpoints:
                    key = (ep.get('method'), ep.get('path'))
                    if key not in existing_paths:
                        # 确保格式一致
                        endpoints.append({
                            'method': ep.get('method', ''),
                            'path': ep.get('path', ''),
                            'function_name': ep.get('function_name', ''),
                            'parameters': ep.get('parameters', []),
                            'docstring': ep.get('description', ''),
                            'line': ep.get('line', 0),
                            'file_path': file_path
                        })
                
                return endpoints
                
            except Exception as e:
                # 降级到 prompt-based 方式
                logger.warning(f"[API检测] Function Calling 失败，降级到 prompt-based: {e}")
                
                prompt = f"""分析以下代码文件，识别所有 API 端点（HTTP 路由）。

文件路径: {file_path}
代码内容:
```python
{sample_content}
```

请识别：
1. 所有 HTTP 端点（GET、POST、PUT、DELETE、PATCH 等）
2. 路由路径（完整路径，包括路径参数）
3. HTTP 方法
4. 处理函数名
5. 行号（如果可能）

返回 JSON 格式：
{{
  "endpoints": [
    {{
      "method": "GET",
      "path": "/api/users",
      "function_name": "get_users",
      "line": 10,
      "description": "获取用户列表"
    }}
  ]
}}

注意：
- 支持 FastAPI、Flask、Django、Gradio、Streamlit、Tornado、Sanic 等框架
- 支持装饰器路由、函数式路由、类视图路由
- 支持配置文件定义的路由
- 支持动态路由（路径参数）
- 如果文件不是路由文件，返回空数组
"""
                
                llm_result = llm_service.call_llm_with_cache(
                    prompt, 
                    cache_key=cache_key
                )
                
                # 调试：记录 LLM 原始响应（如果响应异常短）
                # 区分空结果（正常）和错误响应（异常）
                if len(llm_result) < 100:
                    # 尝试解析响应，判断是否是有效的空结果
                    try:
                        # 清理 markdown 代码块标记
                        cleaned_result = llm_result.strip()
                        if cleaned_result.startswith('```json'):
                            cleaned_result = cleaned_result[7:]
                        if cleaned_result.startswith('```'):
                            cleaned_result = cleaned_result[3:]
                        if cleaned_result.endswith('```'):
                            cleaned_result = cleaned_result[:-3]
                        cleaned_result = cleaned_result.strip()
                        
                        parsed = json.loads(cleaned_result)
                        if isinstance(parsed, dict) and 'endpoints' in parsed:
                            if parsed['endpoints'] == []:
                                # 这是有效的空结果，说明文件确实没有端点
                                logger.debug(f"[API检测] LLM 检测到 0 个端点（文件确实没有端点）: {file_path}")
                            else:
                                # 有端点但响应很短，可能是截断
                                logger.warning(f"[API检测] ⚠️ LLM 响应异常短（仅{len(llm_result)}字符），但包含端点: {file_path}")
                        else:
                            logger.warning(f"[API检测] ⚠️ LLM 响应格式异常: {file_path}, 响应: {llm_result[:100]}")
                    except json.JSONDecodeError:
                        # 无法解析 JSON，可能是错误响应
                        logger.error(f"[API检测] ❌ LLM 响应无法解析为 JSON: {file_path}, 原始响应: {repr(llm_result)}")
                    except Exception as e:
                        logger.warning(f"[API检测] ⚠️ 解析 LLM 响应时出错: {file_path}, 错误: {e}, 响应: {llm_result[:100]}")
                
                parsed_result = llm_service.parse_json_response(llm_result)
                llm_endpoints = parsed_result.get('endpoints', [])
                
                # 合并结果（去重）- 降级到 prompt-based 时才执行
                existing_paths = {(e.get('method'), e.get('path')) for e in endpoints}
                for ep in llm_endpoints:
                    key = (ep.get('method'), ep.get('path'))
                    if key not in existing_paths:
                        # 确保格式一致
                        endpoints.append({
                            'method': ep.get('method', ''),
                            'path': ep.get('path', ''),
                            'function_name': ep.get('function_name', ''),
                            'parameters': ep.get('parameters', []),
                            'docstring': ep.get('description', ''),
                            'line': ep.get('line', 0),
                            'file_path': file_path
                        })
                        existing_paths.add(key)
                
                return endpoints
        except Exception as e:
            logger.warning(f"[API检测] LLM 检测失败: {file_path}, 错误: {e}")
            # 降级：继续使用规则检测的结果
        
        return endpoints
    
    def _fallback_strategy(self, file_path: str, content: str, llm_service, repo_path: str) -> str:
        """
        中期优化：改进降级策略（二次降级，智能采样）
        
        策略：
        1. 如果内容 <= 20K 字符：直接使用完整内容（prompt-based）
        2. 如果内容 > 20K 字符：使用智能采样（提取 API 相关代码）
        3. 如果智能采样失败或效果不理想，使用固定策略作为最后手段
        """
        MAX_PROMPT_LENGTH = 20000  # prompt-based 的限制（比 Function Calling 宽松）
        
        content_size = len(content)
        logger.info(f"[API检测] 降级策略: 文件大小 {content_size} 字符")
        
        if content_size <= MAX_PROMPT_LENGTH:
            logger.info(f"[API检测] 降级策略: 使用完整内容 (<= {MAX_PROMPT_LENGTH} 字符)")
            return content
        else:
            logger.warning(f"[API检测] 降级策略: 文件过大 ({content_size} > {MAX_PROMPT_LENGTH})，使用智能采样")
            
            # 优化：使用智能采样（提取 API 相关代码）
            try:
                # 使用 LLM 服务的智能采样方法
                sampled_content = llm_service._extract_api_related_code(content, MAX_PROMPT_LENGTH)
                sampled_size = len(sampled_content)
                compression_ratio = sampled_size / content_size if content_size > 0 else 0
                
                # 检查采样效果
                if sampled_size <= MAX_PROMPT_LENGTH and compression_ratio > 0.3:  # 至少保留 30% 的内容
                    logger.info(f"[API检测] 降级策略: 智能采样成功: {content_size} -> {sampled_size} 字符 (压缩率: {compression_ratio:.2%})")
                    return sampled_content
                else:
                    logger.warning(f"[API检测] 降级策略: 智能采样效果不理想 (压缩率: {compression_ratio:.2%})，使用固定策略")
            except Exception as e:
                logger.warning(f"[API检测] 降级策略: 智能采样失败 ({e})，使用固定策略")
            
            # 固定策略（作为最后手段）
            return self._fallback_fixed_strategy(content, MAX_PROMPT_LENGTH)
    
    def _fallback_fixed_strategy(self, content: str, max_length: int) -> str:
        """
        固定策略分块处理（作为最后手段）
        
        保留开头和结尾，中间均匀采样
        """
        CHUNK_SIZE = max_length - 1000  # 预留 1K 给 prompt 模板
        
        lines = content.split('\n')
        total_lines = len(lines)
        
        # 计算每块的行数
        head_lines = 200  # 前 200 行
        tail_lines = 200  # 后 200 行
        middle_lines_per_chunk = CHUNK_SIZE // 100  # 假设每行平均 100 字符
        
        # 从中间均匀采样
        middle_start = head_lines
        middle_end = total_lines - tail_lines
        middle_range = middle_end - middle_start
        
        if middle_range > 0:
            step = max(1, middle_range // middle_lines_per_chunk)
            middle_indices = range(middle_start, middle_end, step)
            middle_lines = [lines[i] for i in middle_indices[:middle_lines_per_chunk]]
        else:
            middle_lines = []
        
        # 组合采样内容
        sampled_lines = (
            lines[:head_lines] +
            [f'\n# ... (省略中间 {middle_range - len(middle_lines)} 行) ...\n'] +
            middle_lines +
            [f'\n# ... (省略中间部分) ...\n'] +
            lines[-tail_lines:]
        )
        
        sample_content = '\n'.join(sampled_lines)
        logger.info(f"[API检测] 降级策略: 固定策略采样完成: {total_lines} 行 -> {len(sampled_lines)} 行 ({len(sample_content)} 字符)")
        
        return sample_content
    
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
            
            logger.info(f"[LLM调用] 架构改进建议生成使用模型 {settings.CODE_LLM_MODEL}, prompt 长度: {len(prompt)} 字符")
            
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
            
            logger.info(f"[LLM调用] 架构改进建议生成成功，响应长度: {len(content)} 字符")
            
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
            logger.info(f"[LLM调用] 系统架构生成使用模型 {settings.CODE_LLM_MODEL}, prompt 长度: {len(prompt)} 字符")
            
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
            
            logger.info(f"[LLM调用] 系统架构生成成功，响应长度: {len(content)} 字符")
            
            # 记录 LLM 原始响应（详细内容用于调试）
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
            logger.info(f"[LLM调用] 技术栈生成使用模型 {settings.CODE_LLM_MODEL}, prompt 长度: {len(prompt)} 字符")
            
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
            
            logger.info(f"[LLM调用] 技术栈生成成功，响应长度: {len(content)} 字符")
            
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
            logger.info(f"[LLM调用] 组件关系生成使用模型 {settings.CODE_LLM_MODEL}, prompt 长度: {len(prompt)} 字符")
            
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
            
            logger.info(f"[LLM调用] 组件关系生成成功，响应长度: {len(content)} 字符")
            
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
            logger.info(f"[LLM调用] 部署模型生成使用模型 {settings.CODE_LLM_MODEL}, prompt 长度: {len(prompt)} 字符")
            
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
            
            logger.info(f"[LLM调用] 部署模型生成成功，响应长度: {len(content)} 字符")
            
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
            logger.info(f"[LLM调用] 快速开始指南生成使用模型 {settings.CODE_LLM_MODEL}, prompt 长度: {len(prompt)} 字符")
            
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
            
            logger.info(f"[LLM调用] 快速开始指南生成成功，响应长度: {len(content)} 字符")
            
            # 记录 LLM 原始响应（前500字符，用于调试）
            logger.debug(f"[快速开始指南] LLM 原始响应（前500字符）: {content[:500]}...")
            
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
