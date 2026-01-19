"""
Wiki 内容生成模块
负责生成 Wiki 页面的所有 AI 内容
"""

import os
import re
import json
import hashlib
from typing import Dict, List, Optional
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from app.core.logging import logger
from app.services.code_architecture_analyzer import CodeArchitectureAnalyzer


class CodeWikiGenerator:
    """Wiki 内容生成器"""
    
    # 忽略的目录
    IGNORE_PATTERNS = [
        'node_modules', 'dist', 'build', '__pycache__', '.git',
        'venv', 'env', '.venv', 'target', 'out', '.next',
        'coverage', '.pytest_cache', '.mypy_cache'
    ]
    
    def __init__(self, architecture_analyzer: Optional[CodeArchitectureAnalyzer] = None, db=None, repository_id: Optional[int] = None):
        """
        初始化 Wiki 生成器
        
        Args:
            architecture_analyzer: 架构分析器（可选，如果提供则使用，否则创建新实例）
            db: 数据库会话（用于 LLM 缓存）
            repository_id: 仓库ID（用于 LLM 缓存关联）
        """
        self.architecture_analyzer = architecture_analyzer or CodeArchitectureAnalyzer(db=db, repository_id=repository_id)
        self.db = db
        self.repository_id = repository_id
        self._llm_service = None  # 延迟初始化
    
    def generate_wiki_content(self, repo_path: str, repo_name: str, analyzed_files: List[Dict], statistics: Dict, dependencies: Dict) -> Dict:
        """
        生成 Wiki 页面的所有 AI 内容
        
        Args:
            repo_path: 仓库本地路径
            repo_name: 仓库名称
            analyzed_files: 已分析的文件列表
            statistics: 统计信息
            dependencies: 依赖关系图
            
        Returns:
            Wiki 内容字典
        """
        logger.info(f"开始生成 Wiki 内容: {repo_path}")
        
        # 1. 构建基础上下文信息
        context = self.build_wiki_context(analyzed_files, statistics, repo_path, repo_name)
        
        # 2. 提取依赖和模块信息
        module_structure = self.extract_module_structure(analyzed_files, repo_path)
        dependency_info = self.extract_dependency_info(repo_path)
        deployment_info = self.extract_deployment_info(repo_path)
        readme_content = self.extract_readme_content(repo_path)
        
        # 3. 提取架构详细信息
        external_services = statistics.get('external_services', [])
        arch_details = self.architecture_analyzer.extract_architecture_details(analyzed_files, repo_path, external_services)
        
        # 4. 使用 LLM 生成基础内容
        wiki_content = self.generate_wiki_content_with_llm(context, repo_name, statistics)
        
        # 5. 使用 LLM 生成系统架构
        wiki_content['system_architecture'] = self.architecture_analyzer.generate_system_architecture_llm(
            analyzed_files, module_structure, repo_name, statistics, repo_path
        )
        
        # 6. 并行生成扩展内容
        import concurrent.futures
        
        def safe_generate_tech_stack():
            try:
                return self.architecture_analyzer.generate_tech_stack_llm(dependency_info, statistics, repo_path)
            except Exception as e:
                logger.error(f"生成技术栈失败: {e}")
                return {"core_technologies": "生成失败", "key_dependencies_table": [], "technology_choices": ""}
        
        def safe_generate_component_relationships():
            try:
                return self.architecture_analyzer.generate_component_relationships_llm(dependencies, module_structure, repo_name)
            except Exception as e:
                logger.error(f"生成组件关系失败: {e}")
                return {"service_dependencies": "生成失败", "component_relationships": "", "data_flow": ""}
        
        def safe_generate_deployment_models():
            try:
                return self.architecture_analyzer.generate_deployment_models_llm(deployment_info, repo_path, repo_name)
            except Exception as e:
                logger.error(f"生成部署模型失败: {e}")
                return {"deployment_steps": [], "deployment_requirements": ""}
        
        def safe_generate_getting_started():
            try:
                return self.architecture_analyzer.generate_getting_started_llm(readme_content, dependency_info, repo_path, repo_name)
            except Exception as e:
                logger.error(f"生成快速开始指南失败: {e}")
                return {"prerequisites": [], "installation_steps": [], "key_endpoints": [], "quick_start_summary": ""}
        
        logger.info("开始并行生成 Wiki 扩展内容（技术栈、组件关系、部署模型、快速开始）")
        start_time = datetime.now()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                'technology_stack': executor.submit(safe_generate_tech_stack),
                'component_relationships': executor.submit(safe_generate_component_relationships),
                'deployment_models': executor.submit(safe_generate_deployment_models),
                'getting_started': executor.submit(safe_generate_getting_started),
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
        logger.info(f"✅ 并行生成完成，耗时: {parallel_time:.2f} 秒")
        
        # 7. 补充核心组件的统计数据（根据名称匹配实际文件，使用 LLM 增强）
        if wiki_content.get('core_components'):
            wiki_content['core_components'] = self._enrich_core_components_statistics(
                wiki_content['core_components'], analyzed_files, module_structure, repo_path
            )
        
        # 8. 补充功能子系统的前后端路径（根据 service_files 和架构详情匹配，使用 LLM 增强）
        if wiki_content.get('system_architecture', {}).get('functional_subsystems_table'):
            # 使用之前提取的架构详情（包含 API 路由和前端视图信息）
            wiki_content['system_architecture']['functional_subsystems_table'] = self._enrich_subsystems_paths(
                wiki_content['system_architecture']['functional_subsystems_table'], analyzed_files, statistics, arch_details, repo_path
            )
        
        # 9. 添加关键文件列表
        key_files = self.identify_key_files(repo_path)
        wiki_content['key_files'] = key_files[:30]
        
        logger.info(f"Wiki 内容生成完成: repo_path={repo_path}, 关键文件数={len(key_files)}")
        return wiki_content
    
    def build_wiki_context(
        self,
        analyzed_files: List[Dict],
        statistics: Dict,
        repo_path: str,
        repo_name: str
    ) -> str:
        """构建 Wiki 内容生成的上下文"""
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
        
        context += "\n## 主要文件（按重要性排序）\n"
        key_files = self.identify_key_files(repo_path)
        
        file_types = {}
        for key_file in key_files[:20]:
            file_type = key_file['type']
            if file_type not in file_types:
                file_types[file_type] = []
            file_types[file_type].append(key_file)
        
        type_order = ['readme', 'entry', 'config', 'core', 'build', 'doc', 'test']
        for file_type in type_order:
            if file_type in file_types:
                context += f"\n### {file_type.upper()} 文件\n"
                for key_file in file_types[file_type][:5]:
                    context += f"- {key_file['path']} (重要性: {key_file['importance']})\n"
        
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
    
    def generate_wiki_content_with_llm(
        self,
        context: str,
        repo_name: str,
        statistics: Dict
    ) -> Dict:
        """使用 LLM 生成所有 Wiki 内容"""
        import requests
        from app.config.settings import settings
        
        prompt = f"""请基于以下代码仓库信息，生成 Wiki 页面的所有内容。请以 JSON 格式返回：

{context}

请生成以下内容（JSON 格式）：

1. project_overview: 项目概述（200-300字）
2. what_is_project: 项目是什么（100-150字）
3. core_components: 核心组件列表（前10个）
4. value_propositions: 核心价值主张列表（3-5个）
5. key_features: 主要特性列表（5-8个）

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
        
        logger.info(f"[LLM调用] Wiki 基础内容生成使用模型 {settings.CODE_LLM_MODEL}, prompt 长度: {len(prompt)} 字符")
        
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
        
        logger.info(f"[LLM调用] Wiki 基础内容生成成功，响应长度: {len(content)} 字符")
        
        if not content:
            raise Exception("LLM 返回空内容")
        
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        try:
            wiki_data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"[LLM调用] Wiki 基础内容 JSON 解析失败: {e}, 响应前500字符: {content[:500]}")
            raise Exception(f"LLM 返回的 JSON 格式错误: {str(e)}")
        
        required_fields = ['project_overview', 'what_is_project', 'core_components', 'value_propositions', 'key_features']
        for field in required_fields:
            if field not in wiki_data:
                raise Exception(f"LLM 返回数据缺少必需字段: {field}")
        
        if not isinstance(wiki_data.get('core_components'), list):
            raise Exception("core_components 必须是数组")
        if not isinstance(wiki_data.get('value_propositions'), list):
            raise Exception("value_propositions 必须是数组")
        if not isinstance(wiki_data.get('key_features'), list):
            raise Exception("key_features 必须是数组")
        
        logger.info(f"Wiki 内容生成成功: project_overview={len(wiki_data.get('project_overview', ''))} 字符")
        return wiki_data
    
    def extract_module_structure(self, analyzed_files: List[Dict], repo_path: str) -> Dict:
        """提取模块结构信息"""
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
        
        for file_data in analyzed_files:
            path = file_data['file_path']
            parts = [p for p in path.split('/') if p]  # 过滤空字符串
            
            # 智能识别模块名（支持多级目录）
            module_name = 'root'
            if len(parts) >= 2:
                # 优先使用前两级目录
                module_name = f"{parts[0]}/{parts[1]}"
            elif len(parts) == 1:
                # 单级目录，检查是否是常见的前缀目录
                first_part = parts[0].lower()
                if first_part in ['src', 'lib', 'app', 'apps', 'tools', 'utils', 'core', 'common']:
                    module_name = parts[0]
                else:
                    module_name = 'root'
            
            # 如果模块名是 root，尝试从路径中提取有意义的模块名
            if module_name == 'root' and len(parts) > 0:
                # 检查路径中是否有常见的模块标识
                for part in parts:
                    part_lower = part.lower()
                    if part_lower not in ['src', 'lib', 'app', 'apps', 'tools', 'utils', 'core', 'common', 'test', 'tests']:
                        module_name = part
                        break
            
            module_map[module_name]['files'].append(path)
            module_map[module_name]['lines'] += file_data.get('lines', 0)
            if file_data.get('symbols'):
                module_map[module_name]['symbols'] += len(file_data['symbols'])
            if file_data.get('language'):
                module_map[module_name]['languages'].add(file_data['language'])
            
            for imp in file_data.get('imports', []):
                module_map[module_name]['imports'].add(imp.get('module', ''))
            
            if '/api/' in path or '/routes/' in path:
                for symbol in file_data.get('symbols', []):
                    if symbol.get('type') in ['function', 'method']:
                        module_map[module_name]['api_endpoints'].append({
                            'name': symbol.get('name', ''),
                            'file': path,
                            'line': symbol.get('line', 0)
                        })
            
            if '/service' in path.lower() or '/services/' in path:
                for symbol in file_data.get('symbols', []):
                    if symbol.get('type') in ['function', 'method']:
                        module_map[module_name]['service_methods'].append({
                            'name': symbol.get('name', ''),
                            'file': path,
                            'line': symbol.get('line', 0)
                        })
        
        modules = []
        for name, data in sorted(module_map.items(), key=lambda x: x[1]['lines'], reverse=True):
            responsibilities = self.infer_module_responsibilities(name, data, analyzed_files)
            module_dependencies = self.analyze_module_dependencies(name, data, analyzed_files, module_map)
            
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
    
    def infer_module_responsibilities(self, module_name: str, module_data: Dict, analyzed_files: List[Dict]) -> List[str]:
        """推断模块职责"""
        responsibilities = []
        
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
        
        if module_data.get('api_endpoints'):
            responsibilities.append('API 端点定义')
        if module_data.get('service_methods'):
            responsibilities.append('服务方法实现')
        
        imports = module_data.get('imports', set())
        if any('db' in imp.lower() or 'database' in imp.lower() for imp in imports):
            responsibilities.append('数据访问')
        if any('http' in imp.lower() or 'request' in imp.lower() for imp in imports):
            responsibilities.append('HTTP 请求处理')
        
        return list(set(responsibilities)) if responsibilities else ['通用功能']
    
    def analyze_module_dependencies(self, module_name: str, module_data: Dict, analyzed_files: List[Dict], module_map: Dict) -> List[Dict]:
        """分析模块依赖关系"""
        dependencies = []
        
        for file_path in module_data['files']:
            file_data = next((f for f in analyzed_files if f['file_path'] == file_path), None)
            if not file_data:
                continue
            
            for imp in file_data.get('imports', []):
                import_module = imp.get('module', '')
                if not import_module:
                    continue
                
                target_module = self.match_import_to_module(import_module, module_map)
                if target_module and target_module != module_name:
                    if not any(dep['module'] == target_module for dep in dependencies):
                        dependencies.append({
                            'module': target_module,
                            'type': 'import',
                            'count': 1
                        })
                    else:
                        for dep in dependencies:
                            if dep['module'] == target_module:
                                dep['count'] += 1
        
        return dependencies
    
    def match_import_to_module(self, import_module: str, module_map: Dict) -> Optional[str]:
        """将导入模块匹配到实际模块"""
        import_module = import_module.lstrip('./')
        
        for module_name in module_map.keys():
            if import_module.startswith(module_name) or module_name in import_module:
                return module_name
        
        import_parts = import_module.split('/')
        if import_parts:
            first_part = import_parts[0]
            for module_name in module_map.keys():
                if module_name.startswith(first_part) or first_part in module_name:
                    return module_name
        
        return None
    
    def extract_dependency_info(self, repo_path: str) -> Dict:
        """提取依赖信息"""
        dependency_info = {
            'python': [],
            'javascript': [],
            'rust': [],
            'java': [],
            'other': []
        }
        
        for dep_file in ['requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile']:
            file_path = os.path.join(repo_path, dep_file)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if dep_file == 'requirements.txt':
                            for line in content.split('\n'):
                                line = line.strip()
                                if line and not line.startswith('#'):
                                    dep = line.split('==')[0].split('>=')[0].split('<=')[0].strip()
                                    if dep:
                                        dependency_info['python'].append(dep)
                        elif dep_file in ['setup.py', 'pyproject.toml']:
                            deps = re.findall(r'["\']([^"\']+)["\']', content)
                            dependency_info['python'].extend(deps[:20])
                except Exception as e:
                    logger.warning(f"解析依赖文件失败: {file_path}, {e}")
        
        package_json = os.path.join(repo_path, 'package.json')
        if os.path.exists(package_json):
            try:
                with open(package_json, 'r', encoding='utf-8', errors='ignore') as f:
                    data = json.load(f)
                    deps = data.get('dependencies', {})
                    dev_deps = data.get('devDependencies', {})
                    dependency_info['javascript'] = list(deps.keys())[:30] + list(dev_deps.keys())[:20]
            except Exception as e:
                logger.warning(f"解析 package.json 失败: {e}")
        
        cargo_toml = os.path.join(repo_path, 'Cargo.toml')
        if os.path.exists(cargo_toml):
            try:
                with open(cargo_toml, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    deps = re.findall(r'\[dependencies\.([^\]]+)\]', content)
                    dependency_info['rust'].extend(deps[:30])
            except Exception as e:
                logger.warning(f"解析 Cargo.toml 失败: {e}")
        
        return dependency_info
    
    def extract_deployment_info(self, repo_path: str) -> Dict:
        """提取部署信息"""
        deployment_info = {
            'dockerfile': None,
            'docker_compose': None,
            'config_files': [],
            'scripts': []
        }
        
        for dockerfile in ['Dockerfile', 'Dockerfile.prod', 'Dockerfile.dev']:
            file_path = os.path.join(repo_path, dockerfile)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        deployment_info['dockerfile'] = f.read()[:2000]
                        break
                except Exception as e:
                    logger.warning(f"读取 Dockerfile 失败: {e}")
        
        for compose_file in ['docker-compose.yml', 'docker-compose.yaml', 'compose.yml']:
            file_path = os.path.join(repo_path, compose_file)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        deployment_info['docker_compose'] = f.read()[:2000]
                        break
                except Exception as e:
                    logger.warning(f"读取 docker-compose 失败: {e}")
        
        config_patterns = ['.env.example', 'config.toml', 'config.yaml', 'config.yml', 'settings.py']
        for pattern in config_patterns:
            file_path = os.path.join(repo_path, pattern)
            if os.path.exists(file_path):
                deployment_info['config_files'].append(pattern)
        
        script_patterns = ['start.sh', 'run.sh', 'deploy.sh', 'build.sh']
        for pattern in script_patterns:
            file_path = os.path.join(repo_path, pattern)
            if os.path.exists(file_path):
                deployment_info['scripts'].append(pattern)
        
        return deployment_info
    
    def extract_readme_content(self, repo_path: str) -> str:
        """提取 README 内容"""
        readme_files = ['README.md', 'README.txt', 'README.rst', 'README', 'README_zh.md', 'README_zh_CN.md']
        for readme_file in readme_files:
            file_path = os.path.join(repo_path, readme_file)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                        getting_started_sections = []
                        lines = content.split('\n')
                        in_getting_started = False
                        current_section = []
                        
                        section_keywords = [
                            'quick start', '快速开始', 'getting started', 'installation', 
                            '安装', 'setup', '设置', 'run', '运行', 'usage', '使用',
                            'prerequisites', '前置要求', 'requirements', '依赖'
                        ]
                        
                        for i, line in enumerate(lines):
                            line_lower = line.lower().strip()
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
                                if line_lower.startswith('# ') and not any(keyword in line_lower for keyword in section_keywords):
                                    break
                                current_section.append(line)
                        
                        if current_section:
                            getting_started_sections.extend(current_section)
                        
                        if getting_started_sections:
                            result = '\n'.join(getting_started_sections)
                            logger.info(f"从 README 提取到快速开始相关章节，长度: {len(result)} 字符")
                            return result[:8000]
                        else:
                            logger.info(f"未找到快速开始章节，使用 README 前8000字符")
                            return content[:8000]
                            
                except Exception as e:
                    logger.warning(f"读取 README 失败: {e}")
        return ""
    
    def identify_key_files(self, repo_path: str) -> List[Dict]:
        """识别关键文件"""
        key_files = []
        
        entry_file_patterns = {
            'python': ['main.py', 'app.py', '__init__.py', 'manage.py', 'run.py', 'server.py', 'wsgi.py', 'asgi.py'],
            'javascript': ['index.js', 'index.ts', 'server.js', 'app.js', 'main.js', 'index.mjs'],
            'typescript': ['index.ts', 'index.tsx', 'server.ts', 'app.ts', 'main.ts'],
            'rust': ['main.rs', 'lib.rs'],
            'java': ['Application.java', 'Main.java', 'App.java'],
            'go': ['main.go'],
            'csharp': ['Program.cs', 'Startup.cs'],
        }
        
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
        
        doc_file_patterns = [
            'docs/', '*.md', '*.rst', '*.txt', '*.adoc',
            'CHANGELOG', 'LICENSE', 'AUTHORS', 'CONTRIBUTING'
        ]
        
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in self.IGNORE_PATTERNS]
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, repo_path)
                
                file_type, importance = self.score_file_importance(rel_path, file, entry_file_patterns, build_file_patterns, doc_file_patterns)
                
                if file_type:
                    key_files.append({
                        'path': rel_path,
                        'type': file_type,
                        'importance': importance
                    })
        
        key_files.sort(key=lambda x: x['importance'], reverse=True)
        return key_files
    
    def score_file_importance(self, rel_path: str, file_name: str, entry_patterns: Dict, build_patterns: List[str], doc_patterns: List[str]) -> tuple:
        """评分文件重要性"""
        rel_path_lower = rel_path.lower()
        file_name_lower = file_name.lower()
        
        if 'readme' in file_name_lower:
            return ('readme', 10)
        
        for lang, patterns in entry_patterns.items():
            if any(pattern in file_name_lower for pattern in patterns):
                return ('entry', 9)
        
        if any(pattern in rel_path_lower for pattern in build_patterns):
            return ('build', 8)
        
        if 'config' in rel_path_lower or 'setting' in rel_path_lower:
            return ('config', 7)
        
        if any(keyword in rel_path_lower for keyword in ['core', 'main', 'base', 'common']):
            return ('core', 6)
        
        if any(pattern in rel_path_lower for pattern in doc_patterns) or file_name_lower.endswith(('.md', '.rst', '.txt', '.adoc')):
            return ('doc', 6)
        
        if any(keyword in rel_path_lower for keyword in ['test', 'spec', '__test__', '__tests__']):
            return ('test', 3)
        
        return (None, 1)
    
    def _get_llm_service(self):
        """获取 LLM 增强服务（延迟初始化）"""
        if self._llm_service is None:
            from app.services.llm_enhancement_service import LLMEnhancementService
            self._llm_service = LLMEnhancementService(db=self.db, repository_id=self.repository_id)
        return self._llm_service
    
    def _enrich_core_components_statistics(self, core_components: List[Dict], analyzed_files: List[Dict], module_structure: Dict, repo_path: str) -> List[Dict]:
        """
        补充核心组件的统计数据（文件数、代码行数、符号数）
        
        Args:
            core_components: LLM 生成的核心组件列表（只有 name 和 purpose）
            analyzed_files: 已分析的文件列表
            module_structure: 模块结构信息（包含按目录分组的统计）
            
        Returns:
            补充了统计数据后的核心组件列表
        """
        # 中英文关键词映射（用于匹配中文组件名到英文目录名）
        CHINESE_ENGLISH_MAPPING = {
            '可视化': ['visualize', 'visualization', 'trace', 'track', 'view', 'ui', 'display'],
            '追踪': ['trace', 'track', 'tracking', 'monitor', 'log'],
            '评估': ['evaluate', 'evaluation', 'benchmark', 'test', 'metric'],
            '基准测试': ['benchmark', 'test', 'testing', 'evaluation', 'metric'],
            '输入处理': ['input', 'process', 'handler', 'parse', 'preprocess'],
            '答案生成': ['answer', 'generate', 'output', 'response', 'result'],
            '配置管理': ['config', 'configuration', 'setting', 'settings', 'conf'],
            '工具库': ['tool', 'tools', 'util', 'utils', 'helper', 'helpers'],
            '日志处理': ['log', 'logging', 'logger', 'trace'],
            '单元测试': ['test', 'testing', 'unit', 'spec'],
            '智能体': ['agent', 'agents', 'bot', 'bots'],
            '推理': ['reason', 'reasoning', 'infer', 'inference', 'think'],
            '任务执行': ['task', 'tasks', 'execute', 'execution', 'run'],
            '数据收集': ['collect', 'collection', 'gather', 'data'],
            '流式处理': ['stream', 'streaming', 'flow', 'pipeline'],
            '前端': ['frontend', 'front', 'ui', 'view', 'web'],
            '后端': ['backend', 'back', 'server', 'api', 'service'],
            '服务': ['service', 'services', 'server', 'api'],
            '模块': ['module', 'modules', 'component', 'components'],
            '系统': ['system', 'systems', 'platform']
        }
        # 从模块结构中获取目录统计（更准确）
        modules_map = {}
        if module_structure and 'modules' in module_structure:
            for module in module_structure['modules']:
                module_name = module.get('name', '')
                modules_map[module_name.lower()] = {
                    'files': module.get('files_count', 0),
                    'lines': module.get('lines', 0),
                    'symbols': module.get('symbols', 0),
                    'languages': module.get('languages', [])
                }
        
        # 如果模块结构为空，按目录分组统计
        if not modules_map:
            dir_stats = defaultdict(lambda: {
                'files': 0,
                'lines': 0,
                'symbols': 0,
                'languages': set()
            })
            
            for file_data in analyzed_files:
                path = file_data['file_path']
                parts = path.split('/')
                # 按前两级目录分组
                if len(parts) >= 2:
                    dir_key = f"{parts[0]}/{parts[1]}"
                elif len(parts) == 1:
                    dir_key = parts[0]
                else:
                    dir_key = 'root'
                
                dir_stats[dir_key]['files'] += 1
                dir_stats[dir_key]['lines'] += file_data.get('lines', 0)
                if file_data.get('symbols'):
                    dir_stats[dir_key]['symbols'] += len(file_data['symbols'])
                if file_data.get('language'):
                    dir_stats[dir_key]['languages'].add(file_data['language'])
            
            # 转换为 modules_map 格式
            for dir_key, stats in dir_stats.items():
                modules_map[dir_key.lower()] = {
                    'files': stats['files'],
                    'lines': stats['lines'],
                    'symbols': stats['symbols'],
                    'languages': list(stats['languages'])
                }
        
        # 匹配组件名称到目录/模块
        enriched_components = []
        for comp in core_components:
            comp_name = comp.get('name', '').lower()
            comp_purpose = comp.get('purpose', '').lower()
            
            # 提取组件关键词（从名称和职责中）
            comp_keywords = []
            # 从名称中提取关键词
            comp_keywords.extend(comp_name.replace(' ', '-').replace('_', '-').split('-'))
            
            # 处理中文组件名：转换为英文关键词
            comp_name_original = comp.get('name', '')
            for chinese_key, english_keywords in CHINESE_ENGLISH_MAPPING.items():
                if chinese_key in comp_name_original:
                    comp_keywords.extend(english_keywords)
            
            # 从职责中提取关键词（常见的技术词汇）
            tech_keywords = ['agent', 'ui', 'client', 'server', 'service', 'api', 'chat', 'search', 'component', 'view', 'page', 'trace', 'track', 'visualize', 'evaluate', 'test', 'config', 'tool', 'log']
            for keyword in tech_keywords:
                if keyword in comp_purpose:
                    comp_keywords.append(keyword)
            
            # 去重并过滤太短的词
            comp_keywords = list(set([k for k in comp_keywords if len(k) > 2]))
            
            matched_stats = {'files': 0, 'lines': 0, 'symbols': 0, 'languages': []}
            best_match_score = 0
            
            # 方法1：精确匹配目录名
            comp_normalized = comp_name.replace(' ', '-').replace('_', '-').lower()
            for module_name, stats in modules_map.items():
                module_normalized = module_name.replace('_', '-').lower()
                if comp_normalized == module_normalized or comp_normalized in module_normalized or module_normalized in comp_normalized:
                    if stats['files'] > matched_stats['files']:
                        matched_stats = stats.copy()
                        matched_stats['languages'] = stats['languages'] if isinstance(stats['languages'], list) else list(stats['languages'])
                        best_match_score = 100
                        break
            
            # 方法2：关键词匹配（计算匹配度）
            if best_match_score < 50:
                for module_name, stats in modules_map.items():
                    module_lower = module_name.lower()
                    score = 0
                    
                    # 计算关键词匹配度
                    matched_keywords = 0
                    for keyword in comp_keywords:
                        if keyword and len(keyword) > 2:  # 忽略太短的词
                            if keyword in module_lower:
                                matched_keywords += 1
                                score += 20
                    
                    # 如果匹配了多个关键词，增加分数
                    if matched_keywords > 1:
                        score += matched_keywords * 10
                    
                    # 如果文件数多，也增加分数（更可能是主要组件）
                    if stats['files'] > 0:
                        score += min(stats['files'] / 10, 20)
                    
                    if score > best_match_score and score >= 20:  # 至少匹配一个关键词
                        matched_stats = stats.copy()
                        matched_stats['languages'] = stats['languages'] if isinstance(stats['languages'], list) else list(stats['languages'])
                        best_match_score = score
            
            # 方法3：如果还是没匹配到，尝试从文件路径中直接匹配（支持深层路径）
            if matched_stats['files'] == 0:
                # 提取组件名称中的关键词（支持多种分隔符）
                comp_name_lower = comp.get('name', '').lower()
                comp_name_parts = re.split(r'[/\\_\-\.]', comp_name_lower)
                comp_keywords_extended = comp_keywords + [p for p in comp_name_parts if len(p) > 2]
                
                # 也提取职责描述中的关键词
                purpose_lower = comp.get('purpose', '').lower()
                purpose_keywords = [w for w in re.split(r'[^\w]', purpose_lower) if len(w) > 3]
                comp_keywords_extended.extend(purpose_keywords[:5])  # 最多添加5个关键词
                
                for file_data in analyzed_files:
                    path = file_data.get('file_path', '').lower()
                    file_name = os.path.basename(path).lower()
                    
                    # 检查路径中是否包含组件关键词（支持部分匹配）
                    matched = False
                    for keyword in comp_keywords_extended:
                        if keyword and len(keyword) > 2:
                            # 检查完整路径
                            if keyword in path:
                                matched = True
                                break
                            # 检查文件名（不含扩展名）
                            if keyword in file_name.split('.')[0]:
                                matched = True
                                break
                            # 检查路径的各个部分（支持深层路径）
                            path_parts = path.split('/')
                            for part in path_parts:
                                if keyword in part:
                                    matched = True
                                    break
                            if matched:
                                break
                    
                    if matched:
                        matched_stats['files'] += 1
                        matched_stats['lines'] += file_data.get('lines', 0)
                        if file_data.get('symbols'):
                            matched_stats['symbols'] += len(file_data['symbols'])
                        if file_data.get('language'):
                            if file_data['language'] not in matched_stats['languages']:
                                matched_stats['languages'].append(file_data['language'])
            
            # 构建增强后的组件对象
            enriched_comp = {
                'name': comp.get('name', ''),
                'purpose': comp.get('purpose', ''),
                'files_count': matched_stats['files'],
                'lines_count': matched_stats['lines'],
                'symbols_count': matched_stats['symbols'],
                'languages': matched_stats['languages'] if isinstance(matched_stats['languages'], list) else list(matched_stats['languages'])
            }
            enriched_components.append(enriched_comp)
        
        matched_count = sum(1 for c in enriched_components if c['files_count'] > 0)
        logger.info(f"核心组件统计数据补充完成: 组件数={len(enriched_components)}, 有数据的组件数={matched_count}")
        
        # 如果未匹配的组件较多，使用 LLM 增强匹配
        unmatched_components = [c for c in enriched_components if c['files_count'] == 0]
        if unmatched_components and len(unmatched_components) > 0:
            logger.info(f"[组件匹配] 发现 {len(unmatched_components)} 个未匹配组件，使用 LLM 增强匹配")
            try:
                enriched_components = self.match_components_with_llm(
                    enriched_components, unmatched_components, analyzed_files, module_structure, repo_path
                )
                # 重新统计匹配数量
                matched_count_after_llm = sum(1 for c in enriched_components if c['files_count'] > 0)
                logger.info(f"[组件匹配] LLM 增强后: 已匹配={matched_count_after_llm}/{len(enriched_components)} (提升 {matched_count_after_llm - matched_count} 个)")
            except Exception as e:
                logger.warning(f"[组件匹配] LLM 增强匹配失败: {e}，使用原有匹配结果")
        
        if matched_count < len(enriched_components):
            # 记录未匹配的组件详细信息
            unmatched_components = [c for c in enriched_components if c['files_count'] == 0]
            if unmatched_components:
                logger.warning(f"核心组件匹配情况: 已匹配={matched_count}/{len(enriched_components)}, 未匹配={len(unmatched_components)}")
                for comp in unmatched_components[:3]:  # 只记录前3个
                    logger.warning(f"  - 未匹配组件: 名称='{comp['name']}', 职责='{comp['purpose'][:100]}...'")
        
        return enriched_components
    
    def _extract_module_code_samples(self, module_files: List[str], repo_path: str, max_lines: int = 1500) -> str:
        """
        提取模块的代码样本（充分利用长上下文）
        
        Args:
            module_files: 模块文件列表
            repo_path: 仓库路径
            max_lines: 最大行数（默认 1500，考虑批量处理时的 token 分配）
        """
        samples = []
        total_lines = 0
        
        # 充分利用长上下文，可以分析更多文件
        # 256K tokens ≈ 可以分析 10-12 个文件的完整内容（考虑批量处理）
        max_files = 10  # 最多分析 10 个文件
        
        for file_path in module_files[:max_files]:
            if total_lines >= max_lines:
                break
            
            full_path = os.path.join(repo_path, file_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        file_line_count = len(lines)
                        
                        # 如果文件不大，直接包含完整文件
                        if file_line_count <= 1000:
                            f.seek(0)
                            file_content = f.read()
                            samples.append(f"# {file_path} (完整文件，{file_line_count} 行)\n{file_content}")
                            total_lines += file_line_count
                        else:
                            # 大文件：包含开头和结尾（通常包含关键信息）
                            remaining = max_lines - total_lines
                            if remaining > 500:
                                # 保留前 60% 和后 40%
                                head_lines = int(remaining * 0.6)
                                tail_lines = remaining - head_lines
                                file_sample = ''.join(
                                    lines[:head_lines] + 
                                    [f'\n# ... (省略 {file_line_count - head_lines - tail_lines} 行) ...\n'] + 
                                    lines[-tail_lines:]
                                )
                                samples.append(f"# {file_path} (采样，共 {file_line_count} 行)\n{file_sample}")
                                total_lines += head_lines + tail_lines
                            else:
                                # 剩余空间很小，只保留开头
                                file_sample = ''.join(lines[:remaining])
                                samples.append(f"# {file_path} (前 {remaining} 行，共 {file_line_count} 行)\n{file_sample}")
                                total_lines += remaining
                except Exception as e:
                    logger.debug(f"[模块采样] 读取文件失败: {file_path}, {e}")
                    pass
        
        return '\n\n'.join(samples)
    
    def match_components_with_llm(self, enriched_components: List[Dict], unmatched_components: List[Dict], analyzed_files: List[Dict], module_structure: Dict, repo_path: str) -> List[Dict]:
        """
        使用 LLM 增强核心组件匹配（批量处理优化）
        
        Args:
            enriched_components: 已补充统计的组件列表
            unmatched_components: 未匹配的组件列表
            analyzed_files: 已分析的文件列表
            module_structure: 模块结构信息
            repo_path: 仓库路径
            
        Returns:
            匹配后的组件列表
        """
        if not unmatched_components:
            return enriched_components
        
        # 批量处理：一次处理多个组件（充分利用长上下文）
        # qwen3-coder 256K tokens ≈ 可以同时处理 8-12 个组件的匹配（考虑每个组件的代码量）
        batch_size = 10  # 每次处理 10 个组件（平衡 token 使用和效率）
        
        # 从模块结构中获取模块文件映射
        modules_map = {}
        if module_structure and 'modules' in module_structure:
            for module in module_structure['modules']:
                module_name = module.get('name', '')
                modules_map[module_name] = module.get('files', [])
        else:
            # 如果没有模块结构，按目录分组
            from collections import defaultdict
            dir_files = defaultdict(list)
            for file_data in analyzed_files:
                path = file_data.get('file_path', '')
                parts = path.split('/')
                if len(parts) >= 2:
                    dir_key = f"{parts[0]}/{parts[1]}"
                elif len(parts) == 1:
                    dir_key = parts[0]
                else:
                    dir_key = 'root'
                dir_files[dir_key].append(path)
            modules_map = dict(dir_files)
        
        for i in range(0, len(unmatched_components), batch_size):
            batch_components = unmatched_components[i:i+batch_size]
            
            # 为每个组件准备候选模块
            component_candidates = []
            for comp in batch_components:
                comp_name = comp.get('name', '')
                comp_purpose = comp.get('purpose', '')
                
                # 提取候选模块（基于关键词预筛选）
                candidate_modules = {}
                comp_keywords = comp_name.lower().replace(' ', '-').replace('_', '-').split('-')
                comp_keywords.extend(comp_purpose.lower().split()[:5])
                
                # 从所有模块中筛选候选（最多 12 个）
                for module_name, module_files in list(modules_map.items())[:20]:
                    module_lower = module_name.lower()
                    # 简单的关键词匹配筛选
                    if any(kw in module_lower for kw in comp_keywords if len(kw) > 2):
                        candidate_modules[module_name] = module_files[:5]  # 每个模块最多 5 个文件
                    if len(candidate_modules) >= 12:
                        break
                
                # 如果候选模块太少，添加一些文件数较多的模块
                if len(candidate_modules) < 5:
                    for module_name, module_files in sorted(modules_map.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
                        if module_name not in candidate_modules:
                            candidate_modules[module_name] = module_files[:5]
                        if len(candidate_modules) >= 12:
                            break
                
                # 为每个候选模块提取代码片段
                module_samples = []
                for module_name, module_files in list(candidate_modules.items())[:12]:  # 最多 12 个候选
                    if not module_files:
                        continue
                    # 提取模块的关键文件内容
                    samples = self._extract_module_code_samples(module_files, repo_path, max_lines=1500)
                    module_samples.append({
                        'name': module_name,
                        'file_count': len(module_files),
                        'samples': samples
                    })
                
                component_candidates.append({
                    'name': comp_name,
                    'purpose': comp_purpose,
                    'candidate_modules': module_samples
                })
            
            # 批量使用 LLM 匹配
            prompt = f"""分析以下组件和候选模块，为每个组件找到最匹配的模块。

组件列表:
{json.dumps(component_candidates, ensure_ascii=False, indent=2)}

请为每个组件判断：
1. 哪个模块最匹配该组件（基于职责和代码内容）
2. 匹配度评分（0-100）
3. 匹配理由

返回 JSON 格式：
{{
  "matches": [
    {{
      "component_name": "可视化追踪系统",
      "matched_module": "apps/visualize-trace",
      "confidence": 0.85,
      "reason": "该模块包含可视化相关的代码，与组件职责匹配"
    }}
  ]
}}

注意：
- 如果某个组件没有匹配的模块，matched_module 设为 null
- confidence 低于 0.6 的匹配可以忽略
"""
            
            # 调用 LLM（使用缓存）
            try:
                llm_service = self._get_llm_service()
                cache_key = f"component_match:{hashlib.md5(str(component_candidates).encode()).hexdigest()[:16]}"
                llm_result = llm_service.call_llm_with_cache(prompt, cache_key=cache_key)
                parsed_result = llm_service.parse_json_response(llm_result)
                matches = parsed_result.get('matches', [])
                
                # 应用匹配结果
                for match in matches:
                    comp_name = match.get('component_name')
                    matched_module = match.get('matched_module')
                    confidence = match.get('confidence', 0)
                    
                    if matched_module and confidence >= 0.6:
                        # 找到对应的组件并更新统计数据
                        for comp in enriched_components:
                            if comp.get('name') == comp_name and comp.get('files_count', 0) == 0:
                                # 从模块结构中获取统计数据
                                if matched_module in modules_map:
                                    module_files = modules_map[matched_module]
                                    comp['files_count'] = len(module_files)
                                    # 计算行数和符号数
                                    total_lines = 0
                                    total_symbols = 0
                                    languages = set()
                                    for file_path in module_files:
                                        for file_data in analyzed_files:
                                            if file_data.get('file_path') == file_path:
                                                total_lines += file_data.get('lines', 0)
                                                if file_data.get('symbols'):
                                                    total_symbols += len(file_data['symbols'])
                                                if file_data.get('language'):
                                                    languages.add(file_data['language'])
                                    comp['lines_count'] = total_lines
                                    comp['symbols_count'] = total_symbols
                                    comp['languages'] = list(languages)
                                    comp['matched_module'] = matched_module
                                    comp['match_confidence'] = confidence
                                    comp['match_reason'] = match.get('reason', '')
                                    break
                
                logger.info(f"[组件匹配] LLM 匹配了 {len(matches)} 个组件")
            except Exception as e:
                logger.warning(f"[组件匹配] LLM 匹配失败: {e}")
                # 降级：使用关键词匹配的结果
        
        return enriched_components
    
    def _enrich_subsystems_paths(self, subsystems: List[Dict], analyzed_files: List[Dict], statistics: Dict, arch_details: Dict, repo_path: str) -> List[Dict]:
        """
        补充功能子系统的前后端路径
        
        Args:
            subsystems: LLM 生成的功能子系统列表
            analyzed_files: 已分析的文件列表
            statistics: 统计信息（包含 api_endpoints）
            arch_details: 架构详情（包含 api_routes, frontend_views, frontend_components）
            
        Returns:
            补充了前后端路径后的子系统列表
        """
        # 从架构详情中提取前端路径和后端路由
        frontend_paths_map = {}  # 路径 -> 文件列表
        backend_routes_map = {}  # 路由 -> 文件列表
        
        # 从 frontend_views 和 frontend_components 中提取前端路径
        for view in arch_details.get('frontend_views', []):
            path = view.get('path', '')
            parts = path.split('/')
            if len(parts) >= 2:
                frontend_path = '/'.join(parts[:2])
                if frontend_path not in frontend_paths_map:
                    frontend_paths_map[frontend_path] = []
                frontend_paths_map[frontend_path].append(path)
        
        for comp in arch_details.get('frontend_components', []):
            path = comp.get('path', '')
            parts = path.split('/')
            if len(parts) >= 2:
                frontend_path = '/'.join(parts[:2])
                if frontend_path not in frontend_paths_map:
                    frontend_paths_map[frontend_path] = []
                frontend_paths_map[frontend_path].append(path)
        
        # 从 api_routes 中提取后端路由
        for route in arch_details.get('api_routes', []):
            path = route.get('path', '')
            # 提取 API 路由路径
            if '/api/' in path:
                api_part = path.split('/api/')[-1]
                if api_part:
                    route_path = f"/api/{api_part.split('/')[0]}"
                    if route_path not in backend_routes_map:
                        backend_routes_map[route_path] = []
                    backend_routes_map[route_path].append(path)
            elif '/routes/' in path or '/endpoints/' in path:
                parts = path.split('/')
                for i, part in enumerate(parts):
                    if part in ['routes', 'endpoints', 'api'] and i + 1 < len(parts):
                        route_path = f"/{parts[i]}/{parts[i+1]}"
                        if route_path not in backend_routes_map:
                            backend_routes_map[route_path] = []
                        backend_routes_map[route_path].append(path)
                        break
        
        # 匹配子系统到路径
        enriched_subsystems = []
        for subsystem in subsystems:
            service_files = subsystem.get('service_files', [])
            subsystem_name = subsystem.get('subsystem_name', '').lower()
            subsystem_resp = subsystem.get('key_responsibilities', '').lower()
            
            # 提取子系统关键词
            subsystem_keywords = []
            subsystem_keywords.extend(subsystem_name.split())
            # 从职责中提取关键词
            if '前端' in subsystem_resp or 'ui' in subsystem_resp or '界面' in subsystem_resp or '组件' in subsystem_resp:
                subsystem_keywords.extend(['frontend', 'ui', 'component', 'view', 'page'])
            if '后端' in subsystem_resp or 'api' in subsystem_resp or '服务' in subsystem_resp or '接口' in subsystem_resp:
                subsystem_keywords.extend(['backend', 'api', 'service', 'route'])
            
            matched_frontend_path = None
            matched_backend_route = None
            
            # 方法1：从 service_files 路径中推断
            for file_path in service_files:
                if not file_path:
                    continue
                
                file_path_lower = file_path.lower()
                
                # 检查是否为前端文件
                if any(keyword in file_path_lower for keyword in ['component', 'page', 'view', 'ui', 'app/', 'src/', '.tsx', '.vue', '.jsx']):
                    parts = file_path.split('/')
                    if len(parts) >= 2:
                        candidate_path = '/'.join(parts[:2])
                        # 检查这个路径是否在前端路径映射中
                        if candidate_path in frontend_paths_map:
                            matched_frontend_path = candidate_path
                        elif not matched_frontend_path:  # 如果没有精确匹配，使用候选路径
                            matched_frontend_path = candidate_path
                
                # 检查是否为后端路由文件
                if any(keyword in file_path_lower for keyword in ['api/', 'route', 'controller', 'handler', 'endpoint']):
                    # 提取 API 路径
                    if '/api/' in file_path_lower:
                        api_part = file_path_lower.split('/api/')[-1]
                        if api_part:
                            candidate_route = f"/api/{api_part.split('/')[0]}"
                            if candidate_route in backend_routes_map:
                                matched_backend_route = candidate_route
                            elif not matched_backend_route:
                                matched_backend_route = candidate_route
                    elif '/routes/' in file_path_lower or '/endpoints/' in file_path_lower:
                        parts = file_path.split('/')
                        for i, part in enumerate(parts):
                            if part in ['routes', 'endpoints', 'api', 'controllers'] and i + 1 < len(parts):
                                candidate_route = f"/{parts[i]}/{parts[i+1]}"
                                if candidate_route in backend_routes_map:
                                    matched_backend_route = candidate_route
                                elif not matched_backend_route:
                                    matched_backend_route = candidate_route
                                break
            
            # 方法2：根据子系统名称和职责匹配（如果方法1未找到）
            if not matched_frontend_path:
                best_match_score = 0
                for frontend_path in frontend_paths_map.keys():
                    path_lower = frontend_path.lower()
                    score = 0
                    # 计算关键词匹配度
                    for keyword in subsystem_keywords:
                        if keyword and len(keyword) > 2 and keyword in path_lower:
                            score += 10
                    # 如果文件数多，增加分数
                    if len(frontend_paths_map[frontend_path]) > 0:
                        score += min(len(frontend_paths_map[frontend_path]) / 5, 10)
                    if score > best_match_score and score >= 10:
                        matched_frontend_path = frontend_path
                        best_match_score = score
            
            if not matched_backend_route:
                best_match_score = 0
                for backend_route in backend_routes_map.keys():
                    route_lower = backend_route.lower()
                    score = 0
                    # 计算关键词匹配度
                    for keyword in subsystem_keywords:
                        if keyword and len(keyword) > 2 and keyword in route_lower:
                            score += 10
                    # 如果文件数多，增加分数
                    if len(backend_routes_map[backend_route]) > 0:
                        score += min(len(backend_routes_map[backend_route]) / 5, 10)
                    if score > best_match_score and score >= 10:
                        matched_backend_route = backend_route
                        best_match_score = score
            
            # 方法3：如果还是没找到，尝试从 analyzed_files 中直接匹配
            if not matched_frontend_path or not matched_backend_route:
                for file_data in analyzed_files:
                    path = file_data.get('file_path', '').lower()
                    
                    # 检查前端路径
                    if not matched_frontend_path and any(keyword in path for keyword in ['component', 'page', 'view', 'ui', '.tsx', '.vue']):
                        for keyword in subsystem_keywords:
                            if keyword and len(keyword) > 2 and keyword in path:
                                parts = file_data.get('file_path', '').split('/')
                                if len(parts) >= 2:
                                    matched_frontend_path = '/'.join(parts[:2])
                                    break
                    
                    # 检查后端路由
                    if not matched_backend_route and any(keyword in path for keyword in ['api/', 'route', 'controller']):
                        for keyword in subsystem_keywords:
                            if keyword and len(keyword) > 2 and keyword in path:
                                if '/api/' in path:
                                    api_part = path.split('/api/')[-1]
                                    if api_part:
                                        matched_backend_route = f"/api/{api_part.split('/')[0]}"
                                        break
                                elif '/routes/' in path:
                                    parts = file_data.get('file_path', '').split('/')
                                    for i, part in enumerate(parts):
                                        if part == 'routes' and i + 1 < len(parts):
                                            matched_backend_route = f"/routes/{parts[i+1]}"
                                            break
                                break
                    
                    if matched_frontend_path and matched_backend_route:
                        break
            
            # 如果找到了 service_files 但没有匹配到路由，默认标记为后端服务
            if not matched_backend_route and service_files:
                # 检查 service_files 是否包含后端文件（Python 文件且不在前端目录）
                backend_files = [f for f in service_files if f.endswith('.py') and 
                               not any(kw in f.lower() for kw in ['component', 'page', 'view', 'ui', '.tsx', '.vue', '.jsx'])]
                if backend_files:
                    matched_backend_route = f"后端服务: {len(backend_files)} 个文件"
            
            # 如果仍然没有匹配，基于关键词判断
            if not matched_frontend_path and not matched_backend_route:
                purpose_lower = subsystem.get('key_responsibilities', '').lower()
                name_lower = subsystem.get('subsystem_name', '').lower()
                
                # 检查是否有明显的后端关键词
                backend_keywords = ['服务', 'api', '处理', '逻辑', '数据', '存储', '计算', '分析', '执行', '任务', '追踪', '测试', '评估']
                frontend_keywords = ['界面', 'ui', '页面', '展示', '显示', '交互', '用户界面', '前端', '可视化界面']
                
                has_backend_keyword = any(kw in purpose_lower or kw in name_lower for kw in backend_keywords)
                has_frontend_keyword = any(kw in purpose_lower or kw in name_lower for kw in frontend_keywords)
                
                if has_backend_keyword and not has_frontend_keyword:
                    # 明显是后端，但没有找到路由，标记为后端服务
                    matched_backend_route = '后端服务（无 API 路由）'
                elif has_frontend_keyword and not has_backend_keyword:
                    # 明显是前端，但没有找到路径
                    matched_frontend_path = '前端界面（路径未识别）'
            
            # 构建增强后的子系统对象
            enriched_subsystem = {
                'subsystem_name': subsystem.get('subsystem_name', ''),
                'frontend_path': matched_frontend_path if matched_frontend_path else '无',
                'backend_route': matched_backend_route if matched_backend_route else '无',
                'service_files': subsystem.get('service_files', []),
                'key_responsibilities': subsystem.get('key_responsibilities', '')
            }
            enriched_subsystems.append(enriched_subsystem)
        
        frontend_matched = sum(1 for s in enriched_subsystems if s['frontend_path'] != '无')
        backend_matched = sum(1 for s in enriched_subsystems if s['backend_route'] != '无')
        logger.info(f"功能子系统路径补充完成: 子系统数={len(enriched_subsystems)}, "
                   f"有前端路径={frontend_matched}, 有后端路由={backend_matched}")
        
        # 记录未匹配的子系统详细信息
        unmatched_subsystems = []
        for subsystem in enriched_subsystems:
            if subsystem['frontend_path'] == '无' and subsystem['backend_route'] == '无':
                unmatched_subsystems.append(subsystem)
        
        # 如果未匹配的子系统较多，使用 LLM 增强匹配
        if unmatched_subsystems and len(unmatched_subsystems) > 0:
            logger.info(f"[子系统匹配] 发现 {len(unmatched_subsystems)} 个未匹配子系统，使用 LLM 增强匹配")
            try:
                enriched_subsystems = self.match_subsystem_paths_with_llm(
                    enriched_subsystems, unmatched_subsystems, analyzed_files, arch_details, repo_path
                )
                # 重新统计匹配数量
                frontend_matched_after_llm = sum(1 for s in enriched_subsystems if s['frontend_path'] != '无')
                backend_matched_after_llm = sum(1 for s in enriched_subsystems if s['backend_route'] != '无')
                logger.info(f"[子系统匹配] LLM 增强后: 前端={frontend_matched_after_llm} (提升 {frontend_matched_after_llm - frontend_matched}), "
                          f"后端={backend_matched_after_llm} (提升 {backend_matched_after_llm - backend_matched})")
            except Exception as e:
                logger.warning(f"[子系统匹配] LLM 增强匹配失败: {e}，使用原有匹配结果")
        
        # 重新统计未匹配的子系统（LLM 增强后可能已匹配）
        final_unmatched = [s for s in enriched_subsystems if s['frontend_path'] == '无' and s['backend_route'] == '无']
        if final_unmatched:
            logger.warning(f"功能子系统路径匹配情况: 已匹配前端={frontend_matched}, 已匹配后端={backend_matched}, 完全未匹配={len(final_unmatched)}")
            for sub in final_unmatched[:3]:  # 只记录前3个
                logger.warning(f"  - 未匹配子系统: 名称='{sub['subsystem_name']}', 职责='{sub['key_responsibilities'][:100]}...'")
                logger.info(f"    service_files: {sub['service_files'][:3] if sub['service_files'] else '[]'}")
        
        return enriched_subsystems
    
    def match_subsystem_paths_with_llm(self, enriched_subsystems: List[Dict], unmatched_subsystems: List[Dict], analyzed_files: List[Dict], arch_details: Dict, repo_path: str) -> List[Dict]:
        """
        使用 LLM 增强功能子系统路径匹配
        
        策略:
        1. 提取子系统的职责描述
        2. 提取相关的 service_files
        3. 使用 LLM 判断是前端还是后端，并匹配路径
        """
        if not unmatched_subsystems:
            return enriched_subsystems
        
        # 从架构详情中提取前端路径和后端路由
        frontend_paths_map = {}
        backend_routes_map = {}
        
        for view in arch_details.get('frontend_views', []):
            path = view.get('path', '')
            parts = path.split('/')
            if len(parts) >= 2:
                frontend_path = '/'.join(parts[:2])
                if frontend_path not in frontend_paths_map:
                    frontend_paths_map[frontend_path] = []
                frontend_paths_map[frontend_path].append(path)
        
        for comp in arch_details.get('frontend_components', []):
            path = comp.get('path', '')
            parts = path.split('/')
            if len(parts) >= 2:
                frontend_path = '/'.join(parts[:2])
                if frontend_path not in frontend_paths_map:
                    frontend_paths_map[frontend_path] = []
                frontend_paths_map[frontend_path].append(path)
        
        for route in arch_details.get('api_routes', []):
            path = route.get('path', '')
            if '/api/' in path:
                api_part = path.split('/api/')[-1]
                if api_part:
                    route_path = f"/api/{api_part.split('/')[0]}"
                    if route_path not in backend_routes_map:
                        backend_routes_map[route_path] = []
                    backend_routes_map[route_path].append(path)
        
        # 批量处理子系统（充分利用长上下文）
        for subsystem in unmatched_subsystems:
            subsystem_name = subsystem.get('subsystem_name', '')
            subsystem_resp = subsystem.get('key_responsibilities', '')
            service_files = subsystem.get('service_files', [])
            
            # 提取服务文件的代码片段（充分利用长上下文）
            file_samples = []
            # qwen3-coder 256K tokens ≈ 可以分析 10-15 个文件的完整内容（考虑 prompt 开销）
            for file_path in service_files[:12]:  # 分析前 12 个文件（充分利用长上下文）
                full_path = os.path.join(repo_path, file_path)
                if os.path.exists(full_path):
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        lines = content.split('\n')
                        
                        # 如果文件不大（< 1500 行），直接包含完整内容
                        if len(lines) <= 1500:
                            file_samples.append({
                                'path': file_path,
                                'content': content,
                                'line_count': len(lines)
                            })
                        else:
                            # 大文件：包含开头和结尾（通常包含关键信息）
                            # 前 2000 行 + 后 1000 行
                            file_content = '\n'.join(
                                lines[:2000] + 
                                [f'\n# ... (省略 {len(lines) - 3000} 行) ...\n'] + 
                                lines[-1000:]
                            )
                            file_samples.append({
                                'path': file_path,
                                'content': file_content,
                                'line_count': len(lines),
                                'sampled': True
                            })
                    except Exception as e:
                        logger.debug(f"[子系统匹配] 读取文件失败: {file_path}, {e}")
                        continue
            
            if not file_samples:
                continue
            
            prompt = f"""分析以下功能子系统，判断它是前端还是后端，并匹配相应的路径。

子系统名称: {subsystem_name}
子系统职责: {subsystem_resp}

相关文件:
{json.dumps(file_samples, ensure_ascii=False, indent=2)}

可用前端路径: {list(frontend_paths_map.keys())[:10]}
可用后端路由: {list(backend_routes_map.keys())[:10]}

请判断：
1. 是前端还是后端（或两者都有）
2. 匹配的前端路径（如果有，从可用前端路径中选择）
3. 匹配的后端路由（如果有，从可用后端路由中选择）
4. 判断理由

返回 JSON 格式：
{{
  "type": "backend",
  "frontend_path": null,
  "backend_route": "/api/trace",
  "reason": "该子系统包含 Python 服务文件，处理追踪逻辑，属于后端服务"
}}

注意：
- 如果类型是 "frontend"，frontend_path 不能为 null
- 如果类型是 "backend"，backend_route 不能为 null
- 如果类型是 "both"，frontend_path 和 backend_route 都不能为 null
- 如果无法判断，type 设为 "unknown"
"""
            
            # 调用 LLM
            try:
                llm_service = self._get_llm_service()
                cache_key = f"subsystem_match:{subsystem_name}:{hashlib.md5(str(service_files).encode()).hexdigest()[:16]}"
                match_result = llm_service.call_llm_with_cache(prompt, cache_key=cache_key)
                parsed_result = llm_service.parse_json_response(match_result)
                
                # 应用匹配结果
                match_type = parsed_result.get('type', 'unknown')
                frontend_path = parsed_result.get('frontend_path')
                backend_route = parsed_result.get('backend_route')
                
                # 更新子系统
                for enriched_sub in enriched_subsystems:
                    if enriched_sub.get('subsystem_name') == subsystem_name:
                        if match_type in ['frontend', 'both'] and frontend_path:
                            enriched_sub['frontend_path'] = frontend_path
                        if match_type in ['backend', 'both'] and backend_route:
                            enriched_sub['backend_route'] = backend_route
                        enriched_sub['match_reason'] = parsed_result.get('reason', '')
                        break
                
                logger.info(f"[子系统匹配] LLM 匹配成功: {subsystem_name} -> {match_type}")
            except Exception as e:
                logger.warning(f"[子系统匹配] LLM 匹配失败: {subsystem_name}, 错误: {e}")
                # 降级：使用关键词匹配的结果
        
        return enriched_subsystems