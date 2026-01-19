"""
Wiki 内容生成模块
负责生成 Wiki 页面的所有 AI 内容
"""

import os
import re
import json
from typing import Dict, List, Optional
from collections import defaultdict
from datetime import datetime

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
    
    def __init__(self, architecture_analyzer: Optional[CodeArchitectureAnalyzer] = None):
        """
        初始化 Wiki 生成器
        
        Args:
            architecture_analyzer: 架构分析器（可选，如果提供则使用，否则创建新实例）
        """
        self.architecture_analyzer = architecture_analyzer or CodeArchitectureAnalyzer()
    
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
        
        # 7. 补充核心组件的统计数据（根据名称匹配实际文件）
        if wiki_content.get('core_components'):
            wiki_content['core_components'] = self._enrich_core_components_statistics(
                wiki_content['core_components'], analyzed_files, module_structure
            )
        
        # 8. 补充功能子系统的前后端路径（根据 service_files 和架构详情匹配）
        if wiki_content.get('system_architecture', {}).get('functional_subsystems_table'):
            # 使用之前提取的架构详情（包含 API 路由和前端视图信息）
            wiki_content['system_architecture']['functional_subsystems_table'] = self._enrich_subsystems_paths(
                wiki_content['system_architecture']['functional_subsystems_table'], analyzed_files, statistics, arch_details
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
            logger.error(f"LLM 返回的 JSON 解析失败: {e}")
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
    
    def _enrich_core_components_statistics(self, core_components: List[Dict], analyzed_files: List[Dict], module_structure: Dict) -> List[Dict]:
        """
        补充核心组件的统计数据（文件数、代码行数、符号数）
        
        Args:
            core_components: LLM 生成的核心组件列表（只有 name 和 purpose）
            analyzed_files: 已分析的文件列表
            module_structure: 模块结构信息（包含按目录分组的统计）
            
        Returns:
            补充了统计数据后的核心组件列表
        """
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
            # 从职责中提取关键词（常见的技术词汇）
            tech_keywords = ['agent', 'ui', 'client', 'server', 'service', 'api', 'chat', 'search', 'component', 'view', 'page']
            for keyword in tech_keywords:
                if keyword in comp_purpose:
                    comp_keywords.append(keyword)
            
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
            
            # 方法3：如果还是没匹配到，尝试从文件路径中直接匹配
            if matched_stats['files'] == 0:
                for file_data in analyzed_files:
                    path = file_data.get('file_path', '').lower()
                    # 检查路径中是否包含组件关键词
                    for keyword in comp_keywords:
                        if keyword and len(keyword) > 2 and keyword in path:
                            matched_stats['files'] += 1
                            matched_stats['lines'] += file_data.get('lines', 0)
                            if file_data.get('symbols'):
                                matched_stats['symbols'] += len(file_data['symbols'])
                            if file_data.get('language'):
                                if file_data['language'] not in matched_stats['languages']:
                                    matched_stats['languages'].append(file_data['language'])
                            break  # 每个文件只匹配一次
            
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
        if matched_count < len(enriched_components):
            # 记录未匹配的组件详细信息
            unmatched_components = [c for c in enriched_components if c['files_count'] == 0]
            logger.warning(f"核心组件匹配情况: 已匹配={matched_count}/{len(enriched_components)}, 未匹配={len(unmatched_components)}")
            for comp in unmatched_components:
                logger.warning(f"  - 未匹配组件: 名称='{comp['name']}', 职责='{comp['purpose'][:100]}...'")
                # 列出可能的匹配目录（前5个）
                possible_matches = []
                comp_keywords = comp['name'].lower().replace(' ', '-').replace('_', '-').split('-')
                for module_name, stats in list(modules_map.items())[:10]:
                    module_lower = module_name.lower()
                    for keyword in comp_keywords:
                        if keyword and len(keyword) > 2 and keyword in module_lower:
                            possible_matches.append(f"{module_name}(文件数={stats['files']})")
                            break
                if possible_matches:
                    logger.info(f"    可能的匹配目录: {', '.join(possible_matches[:5])}")
                else:
                    logger.info(f"    未找到可能的匹配目录，可用目录: {', '.join(list(modules_map.keys())[:5])}")
        return enriched_components
    
    def _enrich_subsystems_paths(self, subsystems: List[Dict], analyzed_files: List[Dict], statistics: Dict, arch_details: Dict) -> List[Dict]:
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
        
        if unmatched_subsystems:
            logger.warning(f"功能子系统路径匹配情况: 已匹配前端={frontend_matched}, 已匹配后端={backend_matched}, 完全未匹配={len(unmatched_subsystems)}")
            for sub in unmatched_subsystems:
                logger.warning(f"  - 未匹配子系统: 名称='{sub['subsystem_name']}', 职责='{sub['key_responsibilities'][:100]}...'")
                logger.info(f"    service_files: {sub['service_files'][:3] if sub['service_files'] else '[]'}")
                
                # 列出可用的前端路径和后端路由（前5个）
                if frontend_paths_map:
                    logger.info(f"    可用前端路径: {', '.join(list(frontend_paths_map.keys())[:5])}")
                if backend_routes_map:
                    logger.info(f"    可用后端路由: {', '.join(list(backend_routes_map.keys())[:5])}")
                
                # 分析为什么没匹配上
                subsystem_name = sub['subsystem_name'].lower()
                subsystem_resp = sub['key_responsibilities'].lower()
                subsystem_keywords = []
                subsystem_keywords.extend(subsystem_name.split())
                if '前端' in subsystem_resp or 'ui' in subsystem_resp or '界面' in subsystem_resp:
                    subsystem_keywords.extend(['frontend', 'ui', 'component'])
                if '后端' in subsystem_resp or 'api' in subsystem_resp or '服务' in subsystem_resp:
                    subsystem_keywords.extend(['backend', 'api', 'service'])
                
                logger.debug(f"    提取的关键词: {subsystem_keywords}")
                
                # 检查职责是否足够具体
                if len(sub['key_responsibilities']) < 50:
                    logger.warning(f"    ⚠️ 职责描述过短（{len(sub['key_responsibilities'])}字符），可能不够具体，无法提取有效关键词")
                elif not any(keyword in subsystem_resp for keyword in ['前端', '后端', 'api', 'ui', '界面', '组件', '服务', '路由']):
                    logger.warning(f"    ⚠️ 职责描述中缺少明确的前端/后端关键词，无法判断是前端还是后端子系统")
        
        return enriched_subsystems