"""
Mermaid 图表生成模块
负责生成架构图、数据流图、API 图等
"""

from typing import Dict
from app.core.logging import logger


class CodeDiagramGenerator:
    """代码图表生成器"""
    
    def generate_architecture_diagram(self, arch_details: Dict, statistics: Dict) -> str:
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
        
        # 数据层（从架构信息推断，只使用实际检测到的存储系统）
        storage_systems = []
        if arch_details.get('storage_systems') and len(arch_details['storage_systems']) > 0:
            storage_systems = [s.get('name', '') for s in arch_details['storage_systems'][:3] if s.get('name')]
        
        # 如果没有检测到存储系统，不显示数据层（避免误报）
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
    
    def generate_data_flow_diagram(self, arch_details: Dict) -> str:
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
    
    def generate_api_diagram(self, arch_details: Dict) -> str:
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
