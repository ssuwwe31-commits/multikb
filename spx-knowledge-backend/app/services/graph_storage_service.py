"""
Graph Storage Service
图存储服务（NebulaGraph集成）
"""

from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
import json
from app.core.logging import logger


class GraphStorageInterface(ABC):
    """图存储接口抽象层"""
    
    @abstractmethod
    async def create_entity(self, space: str, entity_data: Dict) -> str:
        """创建实体（节点），返回VID"""
        pass
    
    @abstractmethod
    async def create_relationship(
        self, space: str, source_vid: str, target_vid: str, rel_data: Dict
    ) -> bool:
        """创建关系（边）"""
        pass
    
    @abstractmethod
    async def find_paths(
        self, space: str, source_vid: str, target_vid: str, max_hops: int = 3
    ) -> List[Dict]:
        """查找路径"""
        pass
    
    @abstractmethod
    async def get_entity_neighbors(
        self, space: str, entity_vid: str, relation_type: Optional[str] = None
    ) -> List[Dict]:
        """获取邻居节点"""
        pass
    
    @abstractmethod
    async def search_entities(
        self, space: str, keyword: str, entity_type: Optional[str] = None
    ) -> List[Dict]:
        """搜索实体"""
        pass
    
    @abstractmethod
    async def delete_entity(self, space: str, vid: str) -> bool:
        """删除实体"""
        pass
    
    @abstractmethod
    async def delete_relationship(
        self, space: str, source_vid: str, target_vid: str, relation_type: Optional[str] = None
    ) -> bool:
        """删除关系"""
        pass


class NebulaGraphStorage(GraphStorageInterface):
    """NebulaGraph实现"""
    
    def __init__(self, connection_pool=None):
        """
        初始化NebulaGraph存储
        
        Args:
            connection_pool: NebulaGraph连接池（可选，如果为None则延迟初始化）
        """
        self.pool = connection_pool
        self._initialized = False
    
    def _ensure_initialized(self):
        """确保连接池已初始化"""
        if not self._initialized:
            try:
                from nebula3.gclient.net import ConnectionPool
                from nebula3.Config import Config
                from app.config.settings import settings
                
                config = Config()
                config.max_connection_pool_size = 10
                
                # 从配置获取NebulaGraph地址
                nebula_hosts = getattr(settings, 'NEBULA_HOSTS', [('127.0.0.1', 9669)])
                nebula_user = getattr(settings, 'NEBULA_USER', 'root')
                nebula_password = getattr(settings, 'NEBULA_PASSWORD', 'password')
                
                self.pool = ConnectionPool()
                self.pool.init(nebula_hosts, config)
                self._user = nebula_user
                self._password = nebula_password
                self._initialized = True
                
                logger.info("NebulaGraph连接池初始化成功")
            except ImportError:
                logger.warning("nebula3-python未安装，NebulaGraph功能将不可用")
                raise
            except Exception as e:
                logger.error(f"NebulaGraph连接池初始化失败: {e}")
                raise
    
    def _get_session(self):
        """获取会话"""
        self._ensure_initialized()
        return self.pool.get_session(self._user, self._password)
    
    async def _execute(self, nGQL: str) -> List[Dict]:
        """执行nGQL查询"""
        try:
            session = self._get_session()
            result = session.execute(nGQL)
            
            if not result.is_succeeded():
                error_msg = result.error_msg()
                logger.error(f"NebulaGraph查询失败: {error_msg}, nGQL: {nGQL}")
                raise Exception(f"NebulaGraph查询失败: {error_msg}")
            
            # 解析结果
            data = []
            if result.row_size() > 0:
                for row in result:
                    row_data = {}
                    for i, col in enumerate(result.keys()):
                        row_data[col] = row.values[i].get_sVal() if hasattr(row.values[i], 'get_sVal') else str(row.values[i])
                    data.append(row_data)
            
            session.release()
            return data
        except Exception as e:
            logger.error(f"执行NebulaGraph查询失败: {e}, nGQL: {nGQL}")
            raise
    
    async def create_space_if_not_exists(self, space: str):
        """创建图空间（如果不存在）"""
        try:
            # 检查空间是否存在
            check_nGQL = f"SHOW SPACES;"
            result = await self._execute(check_nGQL)
            spaces = [row.get('Name', '') for row in result]
            
            if space not in spaces:
                # 创建空间
                create_nGQL = f"""
                CREATE SPACE IF NOT EXISTS {space}(
                    partition_num=10, 
                    replica_factor=1,
                    vid_type=FIXED_STRING(256)
                );
                """
                await self._execute(create_nGQL)
                logger.info(f"创建NebulaGraph空间: {space}")
                
                # 创建Schema
                await self._create_schema(space)
        except Exception as e:
            logger.error(f"创建NebulaGraph空间失败: {e}")
            raise
    
    async def _create_schema(self, space: str):
        """创建Schema（Tag和Edge Type）"""
        try:
            use_nGQL = f"USE {space};"
            await self._execute(use_nGQL)
            
            # 创建实体Tag
            create_tag_nGQL = """
            CREATE TAG IF NOT EXISTS entity(
                name string,
                type string,
                description string,
                aliases string,
                confidence double,
                metadata string,
                mysql_id int,
                user_id int,
                created_at timestamp,
                updated_at timestamp
            );
            """
            await self._execute(create_tag_nGQL)
            
            # 创建关系Edge Type
            create_edge_nGQL = """
            CREATE EDGE IF NOT EXISTS relationship(
                relation_type string,
                description string,
                weight double,
                confidence double,
                metadata string,
                mysql_id int,
                user_id int,
                created_at timestamp,
                updated_at timestamp
            );
            """
            await self._execute(create_edge_nGQL)
            
            # 创建索引
            try:
                await self._execute("CREATE TAG INDEX IF NOT EXISTS entity_name_index ON entity(name(20));")
                await self._execute("CREATE TAG INDEX IF NOT EXISTS entity_type_index ON entity(type);")
                await self._execute("CREATE EDGE INDEX IF NOT EXISTS relationship_type_index ON relationship(relation_type);")
            except Exception as e:
                # 索引可能已存在，忽略错误
                logger.debug(f"创建索引时出现警告（可能已存在）: {e}")
            
            logger.info(f"NebulaGraph Schema创建成功: {space}")
        except Exception as e:
            logger.error(f"创建NebulaGraph Schema失败: {e}")
            raise
    
    async def create_entity(self, space: str, entity_data: Dict) -> str:
        """使用 nGQL 插入节点"""
        try:
            await self.create_space_if_not_exists(space)
            
            vid = entity_data.get("id") or f"entity_{entity_data.get('mysql_id')}"
            if not vid:
                raise ValueError("必须提供id或mysql_id")
            
            # 转义字符串中的特殊字符
            def escape_string(s: str) -> str:
                if s is None:
                    return ""
                return str(s).replace('"', '\\"').replace("'", "\\'")
            
            name = escape_string(entity_data.get('name', ''))
            entity_type = escape_string(entity_data.get('type', ''))
            description = escape_string(entity_data.get('description', ''))
            aliases = json.dumps(entity_data.get('aliases', []))
            metadata = json.dumps(entity_data.get('metadata', {}))
            
            nGQL = f"""
            USE {space};
            INSERT VERTEX entity(name, type, description, aliases, confidence, metadata, mysql_id, user_id, created_at, updated_at)
            VALUES "{vid}":(
                "{name}",
                "{entity_type}",
                "{description}",
                "{aliases}",
                {entity_data.get('confidence', 0.7)},
                "{metadata}",
                {entity_data.get('mysql_id', 0)},
                {entity_data.get('user_id', 0)},
                timestamp(),
                timestamp()
            );
            """
            await self._execute(nGQL)
            logger.debug(f"创建实体成功: {vid} in {space}")
            return vid
        except Exception as e:
            logger.error(f"创建NebulaGraph实体失败: {e}, entity_data={entity_data}")
            raise
    
    async def create_relationship(
        self, space: str, source_vid: str, target_vid: str, rel_data: Dict
    ) -> bool:
        """创建关系（边）"""
        try:
            await self.create_space_if_not_exists(space)
            
            def escape_string(s: str) -> str:
                if s is None:
                    return ""
                return str(s).replace('"', '\\"').replace("'", "\\'")
            
            relation_type = escape_string(rel_data.get('relation_type', 'related_to'))
            description = escape_string(rel_data.get('description', ''))
            metadata = json.dumps(rel_data.get('metadata', {}))
            
            nGQL = f"""
            USE {space};
            INSERT EDGE relationship(relation_type, description, weight, confidence, metadata, mysql_id, user_id, created_at, updated_at)
            VALUES "{source_vid}" -> "{target_vid}":(
                "{relation_type}",
                "{description}",
                {rel_data.get('weight', 0.5)},
                {rel_data.get('confidence', 0.7)},
                "{metadata}",
                {rel_data.get('mysql_id', 0)},
                {rel_data.get('user_id', 0)},
                timestamp(),
                timestamp()
            );
            """
            await self._execute(nGQL)
            logger.debug(f"创建关系成功: {source_vid} -> {target_vid} in {space}")
            return True
        except Exception as e:
            logger.error(f"创建NebulaGraph关系失败: {e}, source_vid={source_vid}, target_vid={target_vid}")
            raise
    
    async def find_paths(
        self, space: str, source_vid: str, target_vid: str, max_hops: int = 3
    ) -> List[Dict]:
        """使用 nGQL 查找路径"""
        try:
            await self.create_space_if_not_exists(space)
            
            nGQL = f"""
            USE {space};
            FIND SHORTEST PATH FROM "{source_vid}" TO "{target_vid}" 
            OVER relationship 
            UPTO {max_hops} STEPS;
            """
            result = await self._execute(nGQL)
            
            # 解析路径结果
            paths = []
            for row in result:
                # TODO: 解析路径数据格式
                paths.append(row)
            
            return paths
        except Exception as e:
            logger.error(f"NebulaGraph路径查询失败: {e}")
            raise
    
    async def get_entity_neighbors(
        self, space: str, entity_vid: str, relation_type: Optional[str] = None
    ) -> List[Dict]:
        """获取邻居节点"""
        try:
            await self.create_space_if_not_exists(space)
            
            relation_filter = f"relationship.relation_type == '{relation_type}'" if relation_type else ""
            
            nGQL = f"""
            USE {space};
            MATCH (v:entity)-[e:relationship]->(n:entity)
            WHERE id(v) == "{entity_vid}"
            {"AND " + relation_filter if relation_filter else ""}
            RETURN id(n) as vid, n.name as name, n.type as type, e.relation_type as relation_type, e.weight as weight
            LIMIT 100;
            """
            result = await self._execute(nGQL)
            return result
        except Exception as e:
            logger.error(f"NebulaGraph邻居查询失败: {e}")
            raise
    
    async def search_entities(
        self, space: str, keyword: str, entity_type: Optional[str] = None
    ) -> List[Dict]:
        """搜索实体"""
        try:
            await self.create_space_if_not_exists(space)
            
            type_filter = f"AND n.type == '{entity_type}'" if entity_type else ""
            
            nGQL = f"""
            USE {space};
            MATCH (n:entity)
            WHERE n.name CONTAINS "{keyword}"
            {type_filter}
            RETURN id(n) as vid, n.name as name, n.type as type, n.description as description
            LIMIT 50;
            """
            result = await self._execute(nGQL)
            return result
        except Exception as e:
            logger.error(f"NebulaGraph实体搜索失败: {e}")
            raise
    
    async def delete_entity(self, space: str, vid: str) -> bool:
        """删除实体"""
        try:
            await self.create_space_if_not_exists(space)
            
            nGQL = f"""
            USE {space};
            DELETE VERTEX "{vid}";
            """
            await self._execute(nGQL)
            logger.debug(f"删除实体成功: {vid} in {space}")
            return True
        except Exception as e:
            logger.error(f"删除NebulaGraph实体失败: {e}")
            raise
    
    async def delete_relationship(
        self, space: str, source_vid: str, target_vid: str, relation_type: Optional[str] = None
    ) -> bool:
        """删除关系"""
        try:
            await self.create_space_if_not_exists(space)
            
            type_filter = f"AND e.relation_type == '{relation_type}'" if relation_type else ""
            
            nGQL = f"""
            USE {space};
            MATCH (v:entity)-[e:relationship]->(n:entity)
            WHERE id(v) == "{source_vid}" AND id(n) == "{target_vid}"
            {type_filter}
            DELETE e;
            """
            await self._execute(nGQL)
            logger.debug(f"删除关系成功: {source_vid} -> {target_vid} in {space}")
            return True
        except Exception as e:
            logger.error(f"删除NebulaGraph关系失败: {e}")
            raise


class MockGraphStorage(GraphStorageInterface):
    """Mock图存储（用于测试或NebulaGraph未安装时）"""
    
    def __init__(self):
        self._entities = {}
        self._relationships = []
    
    async def create_entity(self, space: str, entity_data: Dict) -> str:
        vid = entity_data.get("id") or f"entity_{entity_data.get('mysql_id')}"
        self._entities[vid] = entity_data
        return vid
    
    async def create_relationship(
        self, space: str, source_vid: str, target_vid: str, rel_data: Dict
    ) -> bool:
        self._relationships.append({
            "source": source_vid,
            "target": target_vid,
            **rel_data
        })
        return True
    
    async def find_paths(
        self, space: str, source_vid: str, target_vid: str, max_hops: int = 3
    ) -> List[Dict]:
        # 简单的BFS实现
        paths = []
        queue = [(source_vid, [source_vid], [])]
        visited = {source_vid}
        
        while queue and len(paths) < 10:
            current, path, rels = queue.pop(0)
            
            if len(path) > max_hops + 1:
                continue
            
            if current == target_vid and len(path) > 1:
                paths.append({
                    "entities": path,
                    "relationships": rels,
                    "path_length": len(path) - 1
                })
                continue
            
            for rel in self._relationships:
                if rel["source"] == current and rel["target"] not in visited:
                    visited.add(rel["target"])
                    queue.append((rel["target"], path + [rel["target"]], rels + [rel]))
        
        return paths
    
    async def get_entity_neighbors(
        self, space: str, entity_vid: str, relation_type: Optional[str] = None
    ) -> List[Dict]:
        neighbors = []
        for rel in self._relationships:
            if rel["source"] == entity_vid:
                if not relation_type or rel.get("relation_type") == relation_type:
                    neighbors.append({
                        "vid": rel["target"],
                        "name": self._entities.get(rel["target"], {}).get("name", ""),
                        "relation_type": rel.get("relation_type"),
                    })
        return neighbors
    
    async def search_entities(
        self, space: str, keyword: str, entity_type: Optional[str] = None
    ) -> List[Dict]:
        results = []
        for vid, entity in self._entities.items():
            if keyword.lower() in entity.get("name", "").lower():
                if not entity_type or entity.get("type") == entity_type:
                    results.append({
                        "vid": vid,
                        "name": entity.get("name"),
                        "type": entity.get("type"),
                    })
        return results
    
    async def delete_entity(self, space: str, vid: str) -> bool:
        if vid in self._entities:
            del self._entities[vid]
        return True
    
    async def delete_relationship(
        self, space: str, source_vid: str, target_vid: str, relation_type: Optional[str] = None
    ) -> bool:
        self._relationships = [
            rel for rel in self._relationships
            if not (rel["source"] == source_vid and rel["target"] == target_vid and
                   (not relation_type or rel.get("relation_type") == relation_type))
        ]
        return True


def get_graph_storage() -> GraphStorageInterface:
    """获取图存储实例（根据配置返回NebulaGraph或Mock）"""
    try:
        from app.config.settings import settings
        
        # 检查是否启用NebulaGraph
        use_nebula = getattr(settings, 'USE_NEBULA_GRAPH', False)
        
        if use_nebula:
            return NebulaGraphStorage()
        else:
            logger.info("NebulaGraph未启用，使用Mock存储")
            return MockGraphStorage()
    except Exception as e:
        logger.warning(f"初始化NebulaGraph失败，使用Mock存储: {e}")
        return MockGraphStorage()

