"""
代码统计信息分析模块
负责统计 API 端点、数据库表、外部服务等
"""

import os
import re
import ast
from typing import Dict, List
from collections import defaultdict

from app.core.logging import logger


class CodeStatisticsAnalyzer:
    """代码统计信息分析器"""
    
    def calculate_statistics(self, analyzed_files: List[Dict]) -> Dict:
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
            'api_endpoints': {
                'frontend': 0,
                'backend': 0,
            },
            'database_tables': 0,
            'external_services': []
        }
        
        complexities = []
        
        for file_data in analyzed_files:
            stats['total_lines'] += file_data.get('lines', 0)
            
            symbols = file_data.get('symbols', [])
            for symbol in symbols:
                if symbol['type'] == 'function':
                    stats['total_functions'] += 1
                elif symbol['type'] == 'class':
                    stats['total_classes'] += 1
            
            language = file_data.get('language')
            if language:
                stats['languages'][language] += 1
            
            complexity = file_data.get('complexity', {})
            cyclomatic = complexity.get('cyclomatic', 0)
            complexities.append(cyclomatic)
            stats['complexity']['total'] += cyclomatic
            stats['complexity']['max'] = max(stats['complexity']['max'], cyclomatic)
        
        if complexities:
            stats['complexity']['average'] = stats['complexity']['total'] / len(complexities)
        
        stats['languages'] = dict(stats['languages'])
        
        # 统计 API 端点
        api_stats = self.count_api_endpoints(analyzed_files)
        stats['api_endpoints'].update(api_stats)
        
        # 统计数据库表
        stats['database_tables'] = self.count_database_tables(analyzed_files)
        
        # 检测外部依赖
        stats['external_services'] = self.detect_external_services(analyzed_files)
        
        return stats
    
    def count_api_endpoints(self, analyzed_files: List[Dict]) -> Dict:
        """统计 API 端点数量"""
        frontend_count = 0
        backend_count = 0
        frontend_files = []
        
        for file_data in analyzed_files:
            file_path = file_data.get('file_path', '')
            language = file_data.get('language', '')
            
            if self._is_frontend_route_file(file_path, language):
                count = self._count_frontend_routes(file_data)
                frontend_count += count
                frontend_files.append((file_path, language, count))
            
            if self._is_backend_api_file(file_path, language):
                count = self._count_backend_endpoints_precise(file_data)
                backend_count += count
        
        if frontend_files:
            logger.info(f"检测到 {len(frontend_files)} 个前端路由文件，总计 {frontend_count} 个路由")
        
        logger.info(f"API 统计完成 - 前端: {frontend_count}, 后端: {backend_count}")
        return {
            'frontend': frontend_count,
            'backend': backend_count
        }
    
    def _is_frontend_route_file(self, file_path: str, language: str) -> bool:
        """判断是否为前端路由文件"""
        if language not in ['javascript', 'typescript', 'jsx', 'tsx', 'vue']:
            return False
        
        file_path_normalized = file_path.replace('\\', '/')
        file_path_lower = file_path_normalized.lower()
        
        if any(exclude in file_path_lower for exclude in [
            '/node_modules/', '/dist/', '/build/', '/.next/', '/.nuxt/',
            '/coverage/', '/.git/', '/.svn/', '/venv/', '/env/',
        ]):
            return False
        
        if any(keyword in file_path_lower for keyword in ['router', 'route', 'routes']):
            if any(backend_dir in file_path_lower for backend_dir in [
                '/api/', '/server/', '/backend/', '/app/api/',
                '/controllers/', '/handlers/', '/endpoints/'
            ]):
                return False
            return True
        
        route_patterns = [
            'page.tsx', 'page.ts', 'page.jsx', 'page.js',
            'layout.tsx', 'layout.ts', 'layout.jsx', 'layout.js',
            'route.ts', 'route.tsx',
            'routes.ts', 'routes.js',
            '.vue',
            '+page.svelte', '+layout.svelte', '+page.ts', '+layout.ts',
            '/app/', '/pages/', '/routes/',
        ]
        
        for pattern in route_patterns:
            if pattern in file_path_lower:
                if any(backend_dir in file_path_lower for backend_dir in [
                    '/api/', '/server/', '/backend/',
                    '/app/api/', '/app/server/',
                ]) and not ('/pages/' in file_path_lower or '/routes/' in file_path_lower):
                    continue
                return True
        
        frontend_extensions = ['.tsx', '.jsx', '.vue']
        if not any(file_path.endswith(ext) for ext in frontend_extensions):
            return False
        
        backend_indicators = [
            '/api/', '/server/', '/backend/', '/services/',
            '/controllers/', '/handlers/', '/endpoints/',
            '/middleware/', '/utils/api/', '/lib/api/',
            '/test/', '/tests/', '/__tests__/', '/spec/', '/__mocks__/',
        ]
        
        if any(indicator in file_path_lower for indicator in backend_indicators):
            return False
        
        page_indicators = [
            '/pages/', '/routes/', '/views/',
            '/website/src/pages/', '/docs/src/pages/',
            '/src/app/', '/app/',
        ]
        
        if any(indicator in file_path_lower for indicator in page_indicators):
            return True
        
        path_parts = file_path.replace('\\', '/').split('/')
        if len(path_parts) <= 3:
            filename_lower = path_parts[-1].lower()
            if any(name in filename_lower for name in [
                'app.', 'main.', 'index.', 'root.', 'entry.'
            ]) and any(file_path.endswith(ext) for ext in frontend_extensions):
                return True
        
        return False
    
    def _is_backend_api_file(self, file_path: str, language: str) -> bool:
        """判断是否为后端 API 文件"""
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
        """统计前端路由数量"""
        file_path = file_data.get('file_path', '').lower()
        
        if any(pattern in file_path for pattern in [
            'page.tsx', 'page.ts', 'page.jsx', 'page.js',
            'page.vue', '+page.svelte', '+page.ts',
            'layout.tsx', 'layout.ts',
        ]):
            return 1
        
        if any(keyword in file_path for keyword in ['router', 'route', 'routes']):
            symbols = file_data.get('symbols', [])
            route_definitions = [
                s for s in symbols 
                if s['type'] in ['variable', 'constant'] 
                and ('route' in s.get('name', '').lower() or 'path' in s.get('name', '').lower())
            ]
            if route_definitions:
                return len(route_definitions)
            return 1
        
        path_parts = file_path.replace('\\', '/').split('/')
        if len(path_parts) <= 3:
            filename_lower = path_parts[-1].lower()
            if any(name in filename_lower for name in [
                'app.', 'main.', 'index.', 'root.', 'entry.'
            ]):
                return 1
        
        return 1
    
    def _count_backend_endpoints_precise(self, file_data: Dict) -> int:
        """精确统计后端 API 端点数量"""
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
            symbols = file_data.get('symbols', [])
            return len([s for s in symbols if s['type'] in ['function', 'method']])
        
        return 0
    
    def _count_python_endpoints(self, file_data: Dict) -> int:
        """统计 Python API 端点"""
        file_path = file_data.get('file_path', '')
        
        if not file_path or not os.path.exists(file_path):
            symbols = file_data.get('symbols', [])
            return len([s for s in symbols if s['type'] == 'function'])
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            tree = ast.parse(content)
            endpoint_count = 0
            
            decorator_patterns = ['get', 'post', 'put', 'delete', 'patch', 'route']
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call):
                            if hasattr(decorator.func, 'attr'):
                                method = decorator.func.attr
                                if method in decorator_patterns:
                                    endpoint_count += 1
                                    break
                        elif isinstance(decorator, ast.Attribute):
                            if decorator.attr in decorator_patterns:
                                endpoint_count += 1
                                break
            
            if 'path(' in content or 're_path(' in content or 'url(' in content:
                django_patterns = re.findall(r'\b(?:path|re_path|url)\s*\(', content)
                endpoint_count += len(django_patterns)
            
            return endpoint_count
            
        except Exception as e:
            logger.warning(f"Python AST 解析失败: {file_path}, 错误: {e}")
            symbols = file_data.get('symbols', [])
            return len([s for s in symbols if s['type'] == 'function'])
    
    def _count_js_endpoints(self, file_data: Dict) -> int:
        """统计 JavaScript/TypeScript API 端点"""
        file_path = file_data.get('file_path', '')
        
        if not file_path or not os.path.exists(file_path):
            symbols = file_data.get('symbols', [])
            return len([s for s in symbols if s['type'] == 'function'])
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            endpoint_count = 0
            
            express_patterns = [
                r'(?:app|router)\s*\.\s*(?:get|post|put|delete|patch)\s*\(',
                r'(?:app|router)\s*\.\s*route\s*\(',
            ]
            
            for pattern in express_patterns:
                matches = re.findall(pattern, content)
                endpoint_count += len(matches)
            
            nestjs_patterns = [r'@(?:Get|Post|Put|Delete|Patch)\s*\(']
            
            for pattern in nestjs_patterns:
                matches = re.findall(pattern, content)
                endpoint_count += len(matches)
            
            return endpoint_count
            
        except Exception as e:
            logger.warning(f"JS/TS 解析失败: {file_path}, 错误: {e}")
            symbols = file_data.get('symbols', [])
            return len([s for s in symbols if s['type'] == 'function'])
    
    def _count_java_endpoints(self, file_data: Dict) -> int:
        """统计 Java API 端点"""
        file_path = file_data.get('file_path', '')
        
        if not file_path or not os.path.exists(file_path):
            symbols = file_data.get('symbols', [])
            return len([s for s in symbols if s['type'] == 'method'])
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
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
    
    def count_database_tables(self, analyzed_files: List[Dict]) -> int:
        """统计数据库表数量"""
        table_names = set()
        
        for file_data in analyzed_files:
            file_path = file_data.get('file_path', '')
            language = file_data.get('language', '')
            
            try:
                if file_path.lower().endswith('.sql'):
                    tables = self._parse_sql_tables(file_data)
                    table_names.update(tables)
                
                elif language == 'python' and self._is_python_model_file(file_path):
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
                
                elif language == 'java' and self._is_java_entity_file(file_path):
                    tables = self._parse_java_entity_tables(file_data)
                    table_names.update(tables)
                
                elif language in ['javascript', 'typescript'] and self._is_js_model_file(file_path):
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
            
            patterns = [
                r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"\']?(\w+)[`"\']?',
                r'create\s+table\s+(?:if\s+not\s+exists\s+)?[`"\']?(\w+)[`"\']?',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if not match.lower().startswith('temp_') and not match.lower().startswith('tmp_'):
                        tables.add(match)
            
        except Exception as e:
            logger.warning(f"SQL 解析失败: {file_path}, 错误: {e}")
        
        return tables
    
    def _is_python_model_file(self, file_path: str) -> bool:
        """判断是否为 Python ORM 模型文件"""
        file_path_lower = file_path.lower()
        return any(keyword in file_path_lower for keyword in ['model', 'models', 'entity', 'entities'])
    
    def _parse_python_orm_tables(self, file_data: Dict) -> set:
        """解析 Python ORM 模型"""
        file_path = file_data.get('file_path', '')
        tables = set()
        
        if not os.path.exists(file_path):
            symbols = file_data.get('symbols', [])
            for symbol in symbols:
                if symbol['type'] == 'class' and not self._is_base_class(symbol['name']):
                    tables.add(symbol['name'])
            return tables
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                    
                    if self._is_base_class(class_name):
                        continue
                    
                    is_model = False
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_name = base.id
                            if base_name in ['Base', 'Model', 'Document']:
                                is_model = True
                                break
                        elif isinstance(base, ast.Attribute):
                            if base.attr in ['Model', 'Document']:
                                is_model = True
                                break
                    
                    if is_model:
                        tables.add(class_name)
            
        except Exception as e:
            logger.warning(f"Python ORM 解析失败: {file_path}, 错误: {e}")
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
        """解析 Java JPA Entity"""
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
            
            entity_pattern = r'@Entity[^}]*?class\s+(\w+)'
            matches = re.findall(entity_pattern, content, re.DOTALL)
            
            for class_name in matches:
                tables.add(class_name)
            
            table_pattern = r'@Table\s*\(\s*name\s*=\s*["\'](\w+)["\']'
            table_matches = re.findall(table_pattern, content)
            
            for table_name in table_matches:
                tables.add(table_name)
            
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
        """解析 JavaScript/TypeScript ORM 模型"""
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
            
            typeorm_pattern = r'@Entity\s*\([^)]*\)[^}]*?(?:export\s+)?class\s+(\w+)'
            matches = re.findall(typeorm_pattern, content, re.DOTALL)
            tables.update(matches)
            
            sequelize_pattern = r'\.define\s*\(\s*["\'](\w+)["\']'
            matches = re.findall(sequelize_pattern, content)
            tables.update(matches)
            
        except Exception as e:
            logger.warning(f"JS/TS ORM 解析失败: {file_path}, 错误: {e}")
            symbols = file_data.get('symbols', [])
            for symbol in symbols:
                if symbol['type'] == 'class':
                    tables.add(symbol['name'])
        
        return tables
    
    def _is_base_class(self, class_name: str) -> bool:
        """判断是否为基类"""
        base_class_keywords = [
            'Base', 'Mixin', 'Abstract', 'Meta', 'Config',
            'BaseModel', 'AbstractModel', 'ModelMixin'
        ]
        return any(keyword in class_name for keyword in base_class_keywords)
    
    def detect_external_services(self, analyzed_files: List[Dict]) -> List[Dict]:
        """检测外部依赖服务"""
        services = defaultdict(int)
        
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
        
        logger.info(f"[外部服务检测] 🔍 开始检测外部服务，文件数: {len(analyzed_files)}")
        files_with_imports = 0
        files_without_imports = 0
        total_imports = 0
        
        for file_data in analyzed_files:
            file_path = file_data.get('file_path', '')
            file_path_lower = file_path.lower()
            
            is_config = any(keyword in file_path_lower for keyword in [
                '.env', 'config', 'settings', 'application', 
                'docker-compose', 'dockerfile', '.yml', '.yaml', '.json',
                'package.json', 'requirements.txt', 'pom.xml', 'build.gradle'
            ])
            
            imports = file_data.get('imports', [])
            if imports:
                files_with_imports += 1
                total_imports += len(imports)
                # 调试：检查前几个导入的格式
                if files_with_imports <= 3:
                    logger.debug(f"[外部服务检测] 🔍   示例导入格式 (文件: {file_path}): {imports[:3]}")
            else:
                files_without_imports += 1
                # 如果没有 imports 字段，尝试从 content 中提取
                content = file_data.get('content', '')
                if not content and os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()[:50]  # 只读取前50行（通常是导入部分）
                            content = ''.join(lines)
                    except Exception:
                        pass
                
                if content:
                    # 从 content 中提取导入语句
                    import re
                    # Python imports
                    py_imports = re.findall(r'^(?:from\s+(\S+)\s+)?import\s+(\S+)', content, re.MULTILINE)
                    # JavaScript/TypeScript imports
                    js_imports = re.findall(r'import\s+(?:.*?\s+from\s+)?[\'"]([^\'"]+)[\'"]', content)
                    # Node.js require
                    requires = re.findall(r'require\([\'"]([^\'"]+)[\'"]\)', content)
                    
                    if py_imports or js_imports or requires:
                        imports = []
                        for imp in py_imports:
                            module = (imp[0] or imp[1]).strip()
                            if module:
                                imports.append({'module': module})
                        for imp in js_imports + requires:
                            if imp:
                                imports.append({'module': imp.strip()})
                        
                        if imports:
                            files_with_imports += 1
                            total_imports += len(imports)
                            logger.debug(f"[外部服务检测] 🔍   从文件内容提取到 {len(imports)} 个导入: {file_path}")
            
            for imp in imports:
                # 支持多种导入格式
                module = None
                if isinstance(imp, str):
                    module = imp.lower()
                elif isinstance(imp, dict):
                    module = imp.get('module', '').lower()
                    if not module:
                        module = imp.get('name', '').lower()
                    if not module:
                        module = imp.get('import', '').lower()
                    if not module:
                        module = imp.get('from', '').lower()
                else:
                    module = str(imp).lower()
                
                if not module or not module.strip():
                    continue
                
                module = module.strip()
                
                # 调试：记录前几个模块名称（仅在前10个导入时）
                if files_with_imports <= 3 and total_imports <= 20:
                    logger.debug(f"[外部服务检测] 🔍   检查模块: {module} (原始: {imp})")
                
                # 检查是否匹配服务关键词
                matched = False
                for keyword, service_name in service_keywords.items():
                    strict_patterns = {
                        'mysql': ['mysql', 'pymysql', 'mysql2', 'mysql-connector', 'mysqlclient'],
                        'opensearch': ['opensearch', '@opensearch-project/opensearch'],
                        'elasticsearch': ['elasticsearch', '@elastic/elasticsearch'],
                        'redis': ['redis', 'ioredis', 'node_redis', 'redis-py'],
                        'postgresql': ['psycopg2', 'pg', 'postgres', 'postgresql', 'pg8000'],
                        'mongodb': ['pymongo', 'mongodb', 'mongoose'],
                        'kafka': ['kafka', 'kafka-python', 'confluent-kafka'],
                        'rabbitmq': ['pika', 'rabbitmq', 'amqp'],
                    }
                    
                    if keyword in strict_patterns:
                        for pattern in strict_patterns[keyword]:
                            if (module.startswith(pattern) or 
                                f'.{pattern}' in module or 
                                f'/{pattern}' in module or
                                f'@{pattern}' in module):
                                services[service_name] += 1
                                if files_with_imports <= 3:
                                    logger.debug(f"[外部服务检测] 🔍   ✅ 匹配服务: {service_name} (模块: {module}, 模式: {pattern})")
                                matched = True
                                break
                        if matched:
                            break
                    else:
                        # 通用匹配：检查关键词是否在模块名中
                        if keyword in module and len(module) < 50:
                            # 避免误匹配（如 'redis' 匹配到 'rediscover'）
                            if keyword == module or module.startswith(keyword + '.') or module.startswith(keyword + '/'):
                                services[service_name] += 1
                                if files_with_imports <= 3:
                                    logger.debug(f"[外部服务检测] 🔍   ✅ 匹配服务: {service_name} (模块: {module})")
                                matched = True
                                break
            
            if is_config:
                config_content = None
                # 优先使用 file_data 中的 content
                if file_data.get('content'):
                    config_content = file_data.get('content', '').lower()
                elif os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            config_content = f.read().lower()
                    except Exception as e:
                        logger.debug(f"[外部服务检测] 🔍   无法读取配置文件: {file_path}, 错误: {e}")
                
                if config_content:
                    for keyword, service_name in service_keywords.items():
                        config_patterns = [
                            f'{keyword}://',
                            f'{keyword}_',
                            f'{keyword}=',
                            f'"{keyword}"',
                            f"'{keyword}'",
                            f':{keyword}',
                        ]
                        for pattern in config_patterns:
                            if pattern in config_content:
                                logger.debug(f"[外部服务检测] 🔍   从配置文件检测到: {service_name} (文件: {file_path}, 模式: {pattern})")
                                services[service_name] += 1
                                break
            
            if 'dockerfile' in file_path_lower or 'docker-compose' in file_path_lower:
                services['Docker'] += 1
            if 'kubernetes' in file_path_lower or 'k8s' in file_path_lower:
                services['Kubernetes'] += 1
        
        result = [
            {
                'name': name,
                'type': self._get_service_type(name),
                'count': count
            }
            for name, count in sorted(services.items(), key=lambda x: x[1], reverse=True)
        ]
        
        logger.info(f"[外部服务检测] 🔍 检测完成: "
                   f"有导入的文件={files_with_imports}, 无导入的文件={files_without_imports}, "
                   f"总导入数={total_imports}, "
                   f"检测到的服务={len(result)}: {[s['name'] for s in result]}")
        
        # 如果关键词匹配检测到的服务很少，使用 LLM 补充检测
        if len(result) < 3 and total_imports > 100:
            logger.info(f"[外部服务检测] 🔍 检测结果较少，使用 LLM 补充检测...")
            llm_services = self._detect_services_with_llm(analyzed_files)
            if llm_services:
                # 合并结果，避免重复
                existing_names = {s['name'] for s in result}
                for llm_service in llm_services:
                    if llm_service['name'] not in existing_names:
                        result.append(llm_service)
                        logger.info(f"[外部服务检测] 🔍   LLM 补充检测到: {llm_service['name']}")
                # 重新排序
                result = sorted(result, key=lambda x: x['count'], reverse=True)
        
        if len(result) == 0:
            logger.warning(f"[外部服务检测] ⚠️ 未检测到外部服务，可能原因：")
            logger.warning(f"[外部服务检测] ⚠️   1. analyzed_files 中没有 imports 字段")
            logger.warning(f"[外部服务检测] ⚠️   2. analyzed_files 中没有 content 字段")
            logger.warning(f"[外部服务检测] ⚠️   3. 代码中确实没有使用外部服务")
            logger.warning(f"[外部服务检测] ⚠️   4. 导入语句格式不匹配检测模式")
        
        return result
    
    def _detect_services_with_llm(self, analyzed_files: List[Dict]) -> List[Dict]:
        """使用 LLM 检测外部服务（补充检测）"""
        try:
            import requests
            from app.config.settings import settings
            
            # 收集所有导入和配置文件内容
            all_imports = []
            config_files = []
            
            for file_data in analyzed_files:
                file_path = file_data.get('file_path', '')
                imports = file_data.get('imports', [])
                
                # 收集导入
                for imp in imports[:10]:  # 每个文件最多取前10个导入
                    if isinstance(imp, str):
                        all_imports.append(imp)
                    elif isinstance(imp, dict):
                        module = imp.get('module') or imp.get('name') or imp.get('import', '')
                        if module:
                            all_imports.append(module)
                
                # 收集配置文件
                if any(kw in file_path.lower() for kw in ['.env', 'package.json', 'requirements.txt', 'pom.xml', 'docker-compose']):
                    content = file_data.get('content', '')
                    if content:
                        config_files.append({
                            'path': file_path,
                            'content': content[:2000]  # 限制长度
                        })
            
            # 如果导入和配置都很少，跳过 LLM 检测
            if len(all_imports) < 10 and len(config_files) == 0:
                return []
            
            # 构建 prompt
            imports_text = '\n'.join(all_imports[:100])  # 最多100个导入
            configs_text = '\n'.join([f"{cf['path']}:\n{cf['content'][:500]}" for cf in config_files[:5]])
            
            prompt = f"""分析以下代码库的导入语句和配置文件，识别使用的外部服务（数据库、缓存、消息队列、搜索引擎等）。

导入语句（前100个）：
{imports_text}

配置文件：
{configs_text}

请识别所有外部服务，返回 JSON 格式：
{{
  "services": [
    {{"name": "服务名称", "type": "数据库/缓存/消息队列/搜索引擎/其他", "evidence": "检测依据"}}
  ]
}}

只返回 JSON，不要其他内容。"""
            
            # 调用 LLM
            ollama_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
            code_llm_model = getattr(settings, 'CODE_LLM_MODEL', 'qwen2.5-coder:7b')
            
            response = requests.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": code_llm_model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            content = result.get("response", "").strip()
            
            # 解析 JSON 响应
            import json
            import re
            
            # 提取 JSON 部分
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                services = data.get('services', [])
                
                # 转换为标准格式
                result = []
                for svc in services:
                    result.append({
                        'name': svc.get('name', ''),
                        'type': svc.get('type', '其他'),
                        'count': 1  # LLM 检测到的统一设为 1
                    })
                
                logger.info(f"[外部服务检测] 🔍 LLM 检测到 {len(result)} 个服务: {[s['name'] for s in result]}")
                return result
            
            return []
            
        except Exception as e:
            logger.warning(f"[外部服务检测] ⚠️ LLM 补充检测失败: {e}")
            return []
    
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
