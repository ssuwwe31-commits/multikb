"""
Graph Storage Service
图存储服务（NebulaGraph集成）
"""

from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
import json
import atexit
from app.core.logging import logger
from app.config.settings import settings


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
    async def list_entities(
        self,
        space: str,
        entity_type: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        size: int = 20
    ) -> Dict[str, Any]:
        """查询实体列表（支持分页和筛选）"""
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
        self._initialized_spaces = set()  # 缓存已初始化的空间，避免重复检查
    
    def _ensure_initialized(self):
        """确保连接池已初始化"""
        if not self._initialized:
            try:
                from nebula3.gclient.net import ConnectionPool
                from nebula3.Config import Config
                from app.config.settings import settings
                import logging
                
                # 设置 nebula3 的日志级别为 WARNING（减少连接相关的INFO日志）
                nebula_logger = logging.getLogger('nebula3')
                nebula_logger.setLevel(logging.WARNING)
                # 同时设置子日志记录器
                for handler in nebula_logger.handlers:
                    handler.setLevel(logging.WARNING)
                
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
            except ImportError as e:
                logger.error("nebula3-python未安装，NebulaGraph功能不可用")
                from app.core.exceptions import CustomException, ErrorCode
                raise CustomException(
                    ErrorCode.INTERNAL_ERROR,
                    "NebulaGraph功能不可用：nebula3-python模块未安装。请安装nebula3-python包：pip install nebula3-python"
                ) from e
            except Exception as e:
                logger.error(f"NebulaGraph连接池初始化失败: {e}")
                from app.core.exceptions import CustomException, ErrorCode
                raise CustomException(
                    ErrorCode.INTERNAL_ERROR,
                    f"NebulaGraph连接池初始化失败: {str(e)}"
                ) from e
    
    def _get_session(self):
        """获取会话"""
        self._ensure_initialized()
        return self.pool.get_session(self._user, self._password)
    
    def close(self):
        """关闭连接池（应用关闭时调用）"""
        if self._initialized and self.pool:
            try:
                # 关闭连接池中的所有连接
                self.pool.close()
                logger.info("NebulaGraph连接池已关闭")
            except Exception as e:
                # 忽略关闭时的错误（连接可能已经关闭）
                logger.debug(f"关闭NebulaGraph连接池时出错（可忽略）: {e}")
            finally:
                self._initialized = False
                self.pool = None
                # 清空缓存
                self._initialized_spaces.clear()
    
    async def _execute(self, nGQL: str, space: Optional[str] = None) -> List[Dict]:
        """执行nGQL查询
        
        Args:
            nGQL: nGQL查询语句
            space: 可选的空间名称，如果提供，会在执行查询前先执行 USE space
        """
        from app.core.exceptions import CustomException, ErrorCode
        
        session = None
        try:
            session = self._get_session()
            
            # 如果指定了空间，先执行 USE
            if space:
                use_result = session.execute(f"USE {space};")
                if not use_result.is_succeeded():
                    error_msg = use_result.error_msg()
                    logger.error(f"NebulaGraph USE空间失败: {error_msg}, space: {space}")
                    raise CustomException(
                        ErrorCode.INTERNAL_ERROR,
                        f"NebulaGraph USE空间失败: {error_msg}"
                    )
            
            # 只在非例行操作时记录DEBUG日志（减少日志量）
            # 例行操作包括：SHOW SPACES, SHOW HOSTS, USE space, CREATE ... IF NOT EXISTS, FETCH PROP, INSERT
            is_routine_op = any(keyword in nGQL.upper() for keyword in [
                'SHOW SPACES', 'SHOW HOSTS', 'USE ', 'CREATE TAG IF NOT EXISTS', 
                'CREATE EDGE IF NOT EXISTS', 'CREATE INDEX IF NOT EXISTS',
                'FETCH PROP', 'INSERT VERTEX', 'INSERT EDGE'
            ])
            # 仅在启用详细日志时记录非例行操作的查询
            if not is_routine_op and settings.KG_VERBOSE_LOGGING:
                logger.debug("执行nGQL查询: %s", nGQL[:200] if len(nGQL) <= 200 else nGQL[:200] + "...")
            
            result = session.execute(nGQL)
            
            if not result.is_succeeded():
                error_msg = result.error_msg()
                # 对于某些非关键错误，使用较低的日志级别
                # 使用repr查看原始字符串，避免格式化问题
                if "Existed!" in error_msg or "existed" in error_msg.lower():
                    logger.debug("NebulaGraph查询失败（资源已存在）: %s, nGQL (repr, 前500字符): %s", error_msg, repr(nGQL[:500]))
                elif "Invalid param!" in error_msg:
                    logger.debug("NebulaGraph查询失败（参数无效，可能是不支持的语法）: %s, nGQL (repr, 前500字符): %s", error_msg, repr(nGQL[:500]))
                else:
                    logger.error("NebulaGraph查询失败: %s, nGQL (repr, 前500字符): %s", error_msg, repr(nGQL[:500]))
                raise CustomException(
                    ErrorCode.INTERNAL_ERROR,
                    f"NebulaGraph查询失败: {error_msg}"
                )
            
            # 解析结果
            data = []
            if result.row_size() > 0:
                # 获取列名列表
                column_names = result.keys()
                for row in result:
                    row_data = {}
                    # 获取行值列表
                    row_values = row.values()
                    for i, col in enumerate(column_names):
                        value = row_values[i]
                        
                        # 调试日志：仅在启用详细日志时记录
                        if settings.KG_VERBOSE_LOGGING and i == 0 and len(data) == 0:  # 只记录第一行第一个字段作为示例
                            logger.debug(f"[_execute调试] 第一个字段 {col}: type={type(value)}")
                        
                        # 尝试获取字符串值
                        # ValueWrapper对象内部有_value属性，是Value对象，包含sVal、iVal、fVal、nVal等属性
                        # 对于NULL值，Value对象有nVal=0属性，且没有sVal、iVal、fVal等其他值
                        # 通过字符串表示来判断：Value(nVal=0) 表示 NULL，Value(sVal=b'...') 表示有值
                        # 注意：对于Map类型（如properties(vertex)），ValueWrapper会自动转换为字典
                        is_null = False
                        extracted_value = None
                        
                        # 首先检查ValueWrapper是否已经自动转换为字典（Map类型）
                        if isinstance(value, dict):
                            # ValueWrapper已经自动转换为字典（如properties(vertex)返回的Map）
                            row_data[col] = value
                            if settings.KG_VERBOSE_LOGGING:
                                logger.debug(f"[_execute调试] 字段 {col}: 已自动转换为字典")
                            continue
                        
                        if hasattr(value, '_value'):
                            inner_value = value._value
                            
                            # 首先检查是否为Map类型（mVal）- 直接尝试访问mVal属性（更可靠）
                            try:
                                # 直接尝试访问mVal属性（使用多种方式，因为Thrift生成的类型可能有不同的访问方式）
                                mval = None
                                # 方式1: 使用getattr
                                try:
                                    mval = getattr(inner_value, 'mVal', None)
                                except:
                                    pass
                                
                                # 方式2: 如果getattr失败，尝试直接属性访问
                                if mval is None:
                                    try:
                                        if hasattr(inner_value, 'mVal'):
                                            mval = inner_value.mVal
                                    except:
                                        pass
                                
                                # 方式3: 通过__dict__访问value字段（Thrift Value对象的结构）
                                if mval is None:
                                    try:
                                        if hasattr(inner_value, '__dict__'):
                                            inner_dict = inner_value.__dict__
                                            # Thrift Value对象通过value字段存储实际值
                                            if 'value' in inner_dict:
                                                value_obj = inner_dict['value']
                                                # value_obj可能就是NMap对象（如果有kvs属性）
                                                if hasattr(value_obj, 'kvs') or (hasattr(value_obj, '__dict__') and 'kvs' in value_obj.__dict__):
                                                    mval = value_obj  # 这就是NMap对象
                                    except Exception as e:
                                        if settings.KG_VERBOSE_LOGGING:
                                            logger.debug(f"[_execute调试] 字段 {col}: __dict__访问失败: {e}")
                                
                                # 方式4: 尝试直接访问value属性
                                if mval is None:
                                    try:
                                        if hasattr(inner_value, 'value'):
                                            value_obj = inner_value.value
                                            # 检查value_obj是否是NMap（有kvs属性）
                                            if hasattr(value_obj, 'kvs') or (hasattr(value_obj, '__dict__') and 'kvs' in value_obj.__dict__):
                                                mval = value_obj
                                    except Exception as e:
                                        if settings.KG_VERBOSE_LOGGING:
                                            logger.debug(f"[_execute调试] 字段 {col}: value属性访问失败: {e}")
                                
                                if mval is not None:
                                    # mVal是NMap对象，尝试访问kvs（使用多种方式）
                                    kvs = None
                                    try:
                                        kvs = getattr(mval, 'kvs', None)
                                    except:
                                        pass
                                    if kvs is None:
                                        try:
                                            if hasattr(mval, 'kvs'):
                                                kvs = mval.kvs
                                        except:
                                            pass
                                    if kvs is None:
                                        try:
                                            if hasattr(mval, '__dict__') and 'kvs' in mval.__dict__:
                                                kvs = mval.__dict__['kvs']
                                        except:
                                            pass
                                    
                                    if kvs and isinstance(kvs, dict):
                                        # kvs是字典，键是字节串，值是Value对象
                                        result_dict = {}
                                        for key_bytes, val_value in kvs.items():
                                            # 将键从字节串转换为字符串
                                            key_str = key_bytes.decode('utf-8') if isinstance(key_bytes, bytes) else str(key_bytes)
                                            
                                            # 解析值：Value对象需要通过value字段访问实际值
                                            val_actual = None
                                            # 先尝试通过value字段访问
                                            if hasattr(val_value, '__dict__') and 'value' in val_value.__dict__:
                                                val_actual = val_value.__dict__['value']
                                            elif hasattr(val_value, 'value'):
                                                val_actual = val_value.value
                                            else:
                                                val_actual = val_value
                                            
                                            # 如果val_actual是基本类型，直接使用
                                            if isinstance(val_actual, (str, int, float, bool)):
                                                result_dict[key_str] = val_actual
                                            elif isinstance(val_actual, bytes):
                                                result_dict[key_str] = val_actual.decode('utf-8')
                                            else:
                                                # 如果是Value对象，尝试访问其属性
                                                val_sval = getattr(val_actual, 'sVal', None) if hasattr(val_actual, 'sVal') else None
                                                val_ival = getattr(val_actual, 'iVal', None) if hasattr(val_actual, 'iVal') else None
                                                val_fval = getattr(val_actual, 'fVal', None) if hasattr(val_actual, 'fVal') else None
                                                val_bval = getattr(val_actual, 'bVal', None) if hasattr(val_actual, 'bVal') else None
                                                
                                                if val_sval is not None:
                                                    result_dict[key_str] = val_sval.decode('utf-8') if isinstance(val_sval, bytes) else str(val_sval)
                                                elif val_ival is not None:
                                                    result_dict[key_str] = val_ival
                                                elif val_fval is not None:
                                                    result_dict[key_str] = val_fval
                                                elif val_bval is not None:
                                                    result_dict[key_str] = val_bval
                                                else:
                                                    # 如果都没有，尝试字符串表示
                                                    result_dict[key_str] = str(val_value)
                                        
                                        row_data[col] = result_dict
                                        if settings.KG_VERBOSE_LOGGING:
                                            logger.debug(f"[_execute调试] 字段 {col}: 解析Map成功，{len(result_dict)}个键")
                                        continue
                                # 如果mVal是None，也通过字符串检查作为备用方案
                                value_str = str(inner_value)
                                if 'mVal=NMap' in value_str or 'mVal = NMap' in value_str or 'mVal=' in value_str:
                                    # 字符串表示显示有Map，但getattr返回None，可能是Thrift版本问题
                                    # 尝试通过__dict__或其他方式访问
                                    if settings.KG_VERBOSE_LOGGING:
                                        logger.debug(f"[_execute调试] 字段 {col}: 字符串检测到Map，尝试通过__dict__访问")
                                    # 尝试通过__dict__直接访问
                                    try:
                                        if hasattr(inner_value, '__dict__'):
                                            inner_dict = inner_value.__dict__
                                            # Thrift对象可能在__dict__中有mVal
                                            if 'mVal' in inner_dict:
                                                mval = inner_dict['mVal']
                                            # 或者直接访问属性（不通过getattr）
                                            elif hasattr(inner_value, 'mVal'):
                                                mval = inner_value.mVal
                                            else:
                                                mval = None
                                        else:
                                            # 尝试直接属性访问（不使用getattr）
                                            try:
                                                mval = inner_value.mVal
                                            except AttributeError:
                                                mval = None
                                        
                                        if mval is not None:
                                            # 同样尝试访问kvs
                                            if hasattr(mval, 'kvs'):
                                                kvs = mval.kvs
                                            elif hasattr(mval, '__dict__') and 'kvs' in mval.__dict__:
                                                kvs = mval.__dict__['kvs']
                                            else:
                                                kvs = None
                                            
                                            if kvs and isinstance(kvs, dict):
                                                result_dict = {}
                                                for key_bytes, val_value in kvs.items():
                                                    key_str = key_bytes.decode('utf-8') if isinstance(key_bytes, bytes) else str(key_bytes)
                                                    
                                                    val_sval = getattr(val_value, 'sVal', None)
                                                    val_ival = getattr(val_value, 'iVal', None)
                                                    val_fval = getattr(val_value, 'fVal', None)
                                                    val_bval = getattr(val_value, 'bVal', None)
                                                    
                                                    if val_sval is not None:
                                                        result_dict[key_str] = val_sval.decode('utf-8') if isinstance(val_sval, bytes) else str(val_sval)
                                                    elif val_ival is not None:
                                                        result_dict[key_str] = val_ival
                                                    elif val_fval is not None:
                                                        result_dict[key_str] = val_fval
                                                    elif val_bval is not None:
                                                        result_dict[key_str] = val_bval
                                                    else:
                                                        result_dict[key_str] = str(val_value)
                                                
                                                row_data[col] = result_dict
                                                if settings.KG_VERBOSE_LOGGING:
                                                    logger.debug(f"[_execute调试] 字段 {col}: 备用方式解析Map成功，{len(result_dict)}个键")
                                                continue
                                    except Exception as e:
                                        if settings.KG_VERBOSE_LOGGING:
                                            logger.debug(f"[_execute调试] 字段 {col}: 备用方式解析Map失败: {e}")
                            except Exception as e:
                                if settings.KG_VERBOSE_LOGGING:
                                    logger.debug(f"[_execute调试] 字段 {col}: Map类型检测/解析失败: {e}")
                            # 额外检查：如果字段名是props，强制尝试解析Map
                            if col == 'props' and not isinstance(row_data.get(col), dict):
                                try:
                                    # 重新检查一次
                                    inner_value = value._value
                                    value_str = str(inner_value)
                                    if 'mVal' in value_str or 'NMap' in value_str:
                                        mval = getattr(inner_value, 'mVal', None)
                                        if mval is not None:
                                            kvs = getattr(mval, 'kvs', None)
                                            if kvs and isinstance(kvs, dict):
                                                result_dict = {}
                                                for key_bytes, val_value in kvs.items():
                                                    key_str = key_bytes.decode('utf-8') if isinstance(key_bytes, bytes) else str(key_bytes)
                                                    val_sval = getattr(val_value, 'sVal', None)
                                                    val_ival = getattr(val_value, 'iVal', None)
                                                    val_fval = getattr(val_value, 'fVal', None)
                                                    
                                                    if val_sval is not None:
                                                        result_dict[key_str] = val_sval.decode('utf-8') if isinstance(val_sval, bytes) else str(val_sval)
                                                    elif val_ival is not None:
                                                        result_dict[key_str] = val_ival
                                                    elif val_fval is not None:
                                                        result_dict[key_str] = val_fval
                                                    else:
                                                        result_dict[key_str] = str(val_value)
                                                
                                                row_data[col] = result_dict
                                                if settings.KG_VERBOSE_LOGGING:
                                                    logger.debug(f"[_execute调试] 字段 {col}: 强制解析Map成功，{len(result_dict)}个键")
                                                continue
                                except Exception as e:
                                    if settings.KG_VERBOSE_LOGGING:
                                        logger.debug(f"[_execute调试] 字段 {col}: 强制解析Map失败: {e}")
                            
                            # 首先尝试直接访问Value对象的属性（这是最可靠的方法）
                            try:
                                # 直接访问sVal属性（字节串）
                                if hasattr(inner_value, 'sVal'):
                                    try:
                                        sval_bytes = inner_value.sVal
                                        if sval_bytes is not None:
                                            # 解码字节串为字符串
                                            extracted_value = sval_bytes.decode('utf-8')
                                    except Exception as e:
                                        if settings.KG_VERBOSE_LOGGING:
                                            logger.debug(f"[_execute调试] 字段 {col}: sVal属性访问失败: {e}")
                                
                                # 如果sVal没有值，尝试iVal
                                if extracted_value is None and hasattr(inner_value, 'iVal'):
                                    try:
                                        ival = inner_value.iVal
                                        if ival is not None:
                                            extracted_value = ival
                                    except Exception as e:
                                        if settings.KG_VERBOSE_LOGGING:
                                            logger.debug(f"[_execute调试] 字段 {col}: iVal属性访问失败: {e}")
                                
                                # 如果iVal没有值，尝试fVal
                                if extracted_value is None and hasattr(inner_value, 'fVal'):
                                    try:
                                        fval = inner_value.fVal
                                        if fval is not None:
                                            extracted_value = fval
                                    except Exception as e:
                                        if settings.KG_VERBOSE_LOGGING:
                                            logger.debug(f"[_execute调试] 字段 {col}: fVal属性访问失败: {e}")
                                
                                # 如果所有属性都没有值，检查是否为NULL
                                if extracted_value is None:
                                    # 通过字符串表示检查是否为NULL：Value(nVal=0)
                                    try:
                                        value_str = str(inner_value)
                                        if ('nVal=0' in value_str or 'nVal = 0' in value_str) and \
                                           'sVal=' not in value_str and 'iVal=' not in value_str and 'fVal=' not in value_str:
                                            is_null = True
                                            if settings.KG_VERBOSE_LOGGING:
                                                logger.debug(f"[_execute调试] 字段 {col}: 检测到NULL值")
                                    except Exception as e:
                                        if settings.KG_VERBOSE_LOGGING:
                                            logger.debug(f"[_execute调试] 字段 {col}: 字符串表示检查失败: {e}")
                            except Exception as e:
                                if settings.KG_VERBOSE_LOGGING:
                                    logger.debug(f"[_execute调试] 字段 {col}: 属性访问失败: {e}")
                        
                                # 如果是NULL值，根据字段类型返回空字符串或0
                        if is_null:
                            if col in ['name', 'type', 'description', 'aliases', 'metadata', 'relation_type', 'vid']:
                                row_data[col] = ''
                            else:
                                row_data[col] = 0
                            if settings.KG_VERBOSE_LOGGING:
                                logger.debug(f"[_execute调试] 字段 {col}: NULL值")
                        elif extracted_value is not None:
                            # 有提取到的值，处理它
                            if isinstance(extracted_value, bytes):
                                decoded = extracted_value.decode('utf-8')
                                row_data[col] = decoded
                            elif isinstance(extracted_value, (int, float)):
                                row_data[col] = extracted_value
                            else:
                                row_data[col] = str(extracted_value)
                            if settings.KG_VERBOSE_LOGGING:
                                logger.debug(f"[_execute调试] 字段 {col}: 解析成功")
                        else:
                            # 如果字符串表示方法失败，尝试其他方法（向后兼容）
                            sval = None
                            if hasattr(value, 'get_sVal'):
                                try:
                                    sval = value.get_sVal()
                                except:
                                    pass
                            elif hasattr(value, 'get_sval'):
                                try:
                                    sval = value.get_sval()
                                except:
                                    pass
                            elif hasattr(value, 'as_string'):
                                try:
                                    sval = value.as_string()
                                except:
                                    pass
                            elif hasattr(value, 'asString'):
                                try:
                                    sval = value.asString()
                                except:
                                    pass
                            
                            if sval is not None:
                                # 如果是字节串，解码为字符串；如果是None或NULL字符串，使用空字符串
                                if isinstance(sval, bytes):
                                    decoded = sval.decode('utf-8')
                                    # 检查是否是NULL标记字符串
                                    if decoded.upper() in ('__NULL__', 'NULL', 'NONE', ''):
                                        row_data[col] = ''
                                        if settings.KG_VERBOSE_LOGGING:
                                            logger.debug(f"[_execute调试] 字段 {col}: NULL字符串")
                                    else:
                                        row_data[col] = decoded  # 修复：使用decoded而不是未定义的sval_str
                                        if settings.KG_VERBOSE_LOGGING:
                                            logger.debug(f"[_execute调试] 字段 {col}: 字符串解析成功")
                                else:
                                    # sval不是bytes，直接使用
                                    row_data[col] = str(sval)
                                    logger.debug(f"[_execute调试] 字段 {col}: 字符串解析成功")
                            else:
                                # sval是None，尝试其他类型
                                if hasattr(value, '_value'):
                                    # 通过_value访问内部的Value对象
                                    inner_value = value._value
                                    # 尝试获取整数值
                                    if hasattr(inner_value, 'iVal') and inner_value.iVal is not None:
                                        row_data[col] = inner_value.iVal
                                    elif hasattr(inner_value, 'get_iVal'):
                                        try:
                                            ival = inner_value.get_iVal()
                                            row_data[col] = ival if ival is not None else 0
                                        except:
                                            row_data[col] = 0
                                    # 尝试获取浮点数值
                                    elif hasattr(inner_value, 'fVal') and inner_value.fVal is not None:
                                        row_data[col] = inner_value.fVal
                                    elif hasattr(inner_value, 'get_fVal'):
                                        try:
                                            fval = inner_value.get_fVal()
                                            row_data[col] = fval if fval is not None else 0.0
                                        except:
                                            row_data[col] = 0.0
                                    # 尝试获取布尔值
                                    elif hasattr(inner_value, 'bVal') and inner_value.bVal is not None:
                                        row_data[col] = inner_value.bVal
                                    elif hasattr(inner_value, 'get_bVal'):
                                        try:
                                            bval = inner_value.get_bVal()
                                            row_data[col] = bval if bval is not None else False
                                        except:
                                            row_data[col] = False
                                    else:
                                        row_data[col] = ''
                                elif hasattr(value, 'get_iVal'):
                                    # 尝试获取整数值
                                    try:
                                        ival = value.get_iVal()
                                        row_data[col] = ival if ival is not None else 0
                                    except:
                                        # 如果get_iVal失败，尝试其他方法
                                        try:
                                            ival = value.get_ival()
                                            row_data[col] = ival if ival is not None else 0
                                        except:
                                            row_data[col] = 0
                                elif hasattr(value, 'get_fVal'):
                                    # 尝试获取浮点数值
                                    try:
                                        fval = value.get_fVal()
                                        row_data[col] = fval if fval is not None else 0.0
                                    except:
                                        row_data[col] = 0.0
                                elif hasattr(value, 'get_bVal'):
                                    # 尝试获取布尔值
                                    try:
                                        bval = value.get_bVal()
                                        row_data[col] = bval if bval is not None else False
                                    except:
                                        row_data[col] = False
                                else:
                                    # 最后尝试直接转换为字符串
                                    try:
                                        val_str = str(value) if value is not None else ''
                                        if val_str and val_str.upper() not in ('__NULL__', 'NULL', 'NONE', ''):
                                            row_data[col] = val_str
                                        else:
                                            row_data[col] = ''
                                    except:
                                        row_data[col] = ''
                            
                            # 确保row_data[col]被设置（如果所有路径都失败，使用空字符串）
                            if col not in row_data:
                                row_data[col] = ''
                                logger.warning(f"[_execute调试] 字段 {col}: 所有解析方法都失败，设置为空字符串")
                    
                    data.append(row_data)
            
            return data
        except CustomException:
            # 如果是CustomException，直接抛出
            raise
        except Exception as e:
            logger.error(f"执行NebulaGraph查询失败: {e}, nGQL: {nGQL}")
            raise CustomException(
                ErrorCode.INTERNAL_ERROR,
                f"NebulaGraph查询失败: {str(e)}"
            ) from e
        finally:
            # 确保session总是被释放
            if session:
                try:
                    session.release()
                except Exception as release_error:
                    # 忽略关闭时的错误（连接可能已经关闭）
                    logger.debug(f"释放NebulaGraph会话时出错（可忽略）: {release_error}")
    
    async def create_space_if_not_exists(self, space: str):
        """创建图空间（如果不存在）"""
        from app.core.exceptions import CustomException, ErrorCode
        
        # 如果空间已经在缓存中，直接返回（避免重复检查）
        if space in self._initialized_spaces:
            return
        
        try:
            # 检查空间是否存在
            check_nGQL = f"SHOW SPACES;"
            result = await self._execute(check_nGQL)
            spaces = [row.get('Name', '') for row in result]
            
            if space in spaces:
                # 空间已存在，验证schema是否存在，然后添加到缓存
                try:
                    # 尝试使用空间，如果成功则说明空间可用
                    use_nGQL = f"USE {space};"
                    await self._execute(use_nGQL)
                    # 验证schema是否存在（通过尝试创建schema，如果已存在则不会报错）
                    await self._create_schema(space)
                    # 添加到缓存
                    self._initialized_spaces.add(space)
                    return
                except Exception as e:
                    # 如果验证失败，记录日志但继续处理
                    logger.warning(f"验证空间 {space} schema 失败: {e}，尝试重新创建schema")
                    try:
                        # 尝试重新创建schema
                        await self._create_schema(space)
                        # 添加到缓存
                        self._initialized_spaces.add(space)
                        return
                    except Exception as schema_error:
                        # 如果schema创建也失败，记录警告但添加到缓存（避免重复尝试）
                        logger.warning(f"重新创建空间 {space} 的schema失败: {schema_error}，但空间已存在，添加到缓存")
                        self._initialized_spaces.add(space)
                        return
            
            # 空间不存在，需要创建
            if space not in spaces:
                # 先检查 storaged 节点状态
                # 根据 NebulaGraph 官方文档，SHOW HOSTS 返回的字段包括：Host, Port, Status, Role 等
                # storaged 节点的默认端口是 9779
                try:
                    hosts_nGQL = "SHOW HOSTS;"
                    hosts_result = await self._execute(hosts_nGQL)
                    
                    # 检查返回的数据结构（用于调试）
                    if hosts_result and len(hosts_result) > 0:
                        logger.debug(f"SHOW HOSTS 返回的字段: {list(hosts_result[0].keys())}")
                    
                    # 方法1: 根据 Port 字段检查（storaged 默认端口是 9779）
                    storaged_hosts_by_port = [
                        h for h in hosts_result 
                        if h.get('Status') == 'ONLINE' and str(h.get('Port', '')) == '9779'
                    ]
                    
                    # 方法2: 根据 Role 字段检查（如果存在）
                    storaged_hosts_by_role = [
                        h for h in hosts_result 
                        if h.get('Status') == 'ONLINE' and 'storage' in str(h.get('Role', '')).lower()
                    ]
                    
                    # 合并两种方法的结果
                    storaged_hosts = storaged_hosts_by_port or storaged_hosts_by_role
                    
                    if not storaged_hosts:
                        logger.debug("未找到可用的 storaged 节点，使用 partition_num=1 创建空间")
                        # 仍然尝试创建，但使用更小的 partition_num
                        partition_num = 1
                    else:
                        partition_num = 10
                        logger.debug(f"找到 {len(storaged_hosts)} 个 storaged 节点，使用 partition_num=10")
                except CustomException:
                    # 如果是CustomException，直接抛出，不捕获
                    raise
                except Exception as e:
                    logger.debug(f"检查 storaged 节点状态失败: {e}，使用默认配置 partition_num=10")
                    partition_num = 10
                
                # 创建空间
                create_nGQL = f"""
                CREATE SPACE IF NOT EXISTS {space}(
                    partition_num={partition_num}, 
                    replica_factor=1,
                    vid_type=FIXED_STRING(256)
                );
                """
                await self._execute(create_nGQL)
                logger.info(f"创建NebulaGraph空间: {space} (partition_num={partition_num})")
                
                # 等待空间创建完成（NebulaGraph 需要时间初始化）
                import asyncio
                await asyncio.sleep(5)  # 增加等待时间到5秒
                
                # 创建Schema（带重试逻辑）
                await self._create_schema(space)
            
            # 空间已存在或创建成功，添加到缓存
            self._initialized_spaces.add(space)
        except CustomException:
            # 如果是CustomException，直接抛出
            raise
        except Exception as e:
            error_msg = str(e)
            if "Host not enough" in error_msg or "not enough" in error_msg.lower():
                logger.error(f"创建NebulaGraph空间失败: {error_msg}")
                logger.error("可能原因：storaged 节点未运行或未注册到 metad。请检查 NebulaGraph 集群状态。")
                raise CustomException(
                    ErrorCode.INTERNAL_ERROR,
                    f"NebulaGraph 存储节点不足，无法创建图空间。请确保 storaged 服务正常运行并已注册到 metad。错误详情：{error_msg}"
                )
            logger.error(f"创建NebulaGraph空间失败: {e}")
            raise
    
    async def _create_schema(self, space: str):
        """创建Schema（Tag和Edge Type）"""
        import asyncio
        from app.core.exceptions import CustomException, ErrorCode
        
        # 重试逻辑：等待空间就绪
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                use_nGQL = f"USE {space};"
                await self._execute(use_nGQL)
                break  # 成功，退出重试循环
            except CustomException:
                # 如果是CustomException，直接抛出，不重试
                raise
            except Exception as e:
                error_msg = str(e)
                if "SpaceNotFound" in error_msg or "Space not found" in error_msg:
                    if attempt < max_retries - 1:
                        logger.info(f"空间 {space} 尚未就绪，等待 {retry_delay} 秒后重试 ({attempt + 1}/{max_retries})")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        logger.error(f"空间 {space} 创建后等待 {max_retries * retry_delay} 秒仍未就绪")
                        raise CustomException(
                            ErrorCode.INTERNAL_ERROR,
                            f"NebulaGraph 空间 {space} 创建后未能及时就绪，请检查 NebulaGraph 集群状态"
                        )
                else:
                    # 其他错误直接抛出
                    raise
        
        try:
            # 创建实体Tag（使用 space 参数确保在同一个 session 中执行 USE）
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
            await self._execute(create_tag_nGQL, space=space)
            
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
            await self._execute(create_edge_nGQL, space=space)
            
            # 创建索引（索引创建失败不影响主流程，静默处理）
            # 注意：NebulaGraph 3.x 可能对索引语法有特殊要求，如果创建失败可以忽略
            # 由于索引创建可能失败且不影响功能，仅在第一次失败时记录警告，后续静默处理
            index_creation_commands = [
                ("CREATE TAG INDEX IF NOT EXISTS entity_name_index ON entity(name(20));", "entity_name_index"),
                ("CREATE TAG INDEX IF NOT EXISTS entity_type_index ON entity(type);", "entity_type_index"),
                ("CREATE EDGE INDEX IF NOT EXISTS relationship_type_index ON relationship(relation_type);", "relationship_type_index"),
            ]
            
            index_failures = []
            for index_cmd, index_name in index_creation_commands:
                try:
                    await self._execute(index_cmd, space=space)
                    # 索引创建成功不记录日志（减少日志量）
                except Exception as e:
                    error_msg = str(e)
                    # 索引创建失败是正常的（可能已存在或语法不支持），收集失败信息
                    if "existed" in error_msg.lower() or "already exists" in error_msg.lower() or "Existed!" in error_msg:
                        # 索引已存在，完全静默处理
                        pass
                    elif "Invalid param!" in error_msg or "syntax" in error_msg.lower():
                        # 语法不支持，记录但不影响流程
                        index_failures.append(f"{index_name}(语法不支持)")
                    else:
                        index_failures.append(f"{index_name}({error_msg[:50]})")
            
            # 如果有索引创建失败，记录一次汇总信息（而不是每个都记录）
            if index_failures:
                logger.debug(f"NebulaGraph索引创建（部分失败，可忽略）: {', '.join(index_failures)}")
            
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
            
            # 转义字符串中的特殊字符（包括JSON字符串中的引号）
            def escape_string(s: str) -> str:
                if s is None or s == "":
                    return ""  # 空字符串，不是 NULL
                # 先转义反斜杠，再转义双引号
                return str(s).replace('\\', '\\\\').replace('"', '\\"')
            
            # 获取字段值，确保不为 None
            name = entity_data.get('name')
            entity_type = entity_data.get('type')
            description = entity_data.get('description')
            mysql_id = int(entity_data.get('mysql_id', 0)) if entity_data.get('mysql_id') is not None else 0
            user_id = int(entity_data.get('user_id', 0)) if entity_data.get('user_id') is not None else 0
            confidence = float(entity_data.get('confidence', settings.KG_ENTITY_DEFAULT_CONFIDENCE)) if entity_data.get('confidence') is not None else settings.KG_ENTITY_DEFAULT_CONFIDENCE
            
            # 验证必填字段
            if not name or not name.strip():
                raise ValueError(f"实体名称不能为空: entity_data={entity_data}")
            if not entity_type or not entity_type.strip():
                raise ValueError(f"实体类型不能为空: entity_data={entity_data}")
            
            # 转义字符串字段
            name = escape_string(name)
            entity_type = escape_string(entity_type)
            description = escape_string(description or "")
            
            # JSON字符串需要额外转义
            aliases = entity_data.get('aliases', [])
            if not aliases:
                aliases = []
            aliases_str = json.dumps(aliases).replace('\\', '\\\\').replace('"', '\\"')
            
            metadata = entity_data.get('metadata', {})
            if not metadata:
                metadata = {}
            metadata_str = json.dumps(metadata).replace('\\', '\\\\').replace('"', '\\"')
            
            # 详细日志：仅在启用详细日志时输出
            if settings.KG_VERBOSE_LOGGING:
                logger.info(f"[插入实体] 准备插入实体到NebulaGraph: vid={vid}, name={name}, type={entity_type}, mysql_id={mysql_id}, user_id={user_id}")
                logger.debug(f"[插入实体] 详细数据: description长度={len(description)}, aliases={aliases}, confidence={confidence}, metadata={metadata}")
            
            # 验证数据完整性
            if not name or name.strip() == "":
                raise ValueError(f"实体名称不能为空: vid={vid}")
            if not entity_type or entity_type.strip() == "":
                raise ValueError(f"实体类型不能为空: vid={vid}, name={name}")
            
            # 先检查实体是否存在
            check_nGQL = f'FETCH PROP ON entity "{vid}" YIELD properties(vertex) as props;'
            try:
                check_result = await self._execute(check_nGQL, space=space)
                if check_result and len(check_result) > 0:
                    # 实体已存在，使用 UPDATE
                    if settings.KG_VERBOSE_LOGGING:
                        logger.info(f"[插入实体] 实体已存在，使用UPDATE: vid={vid}")
                    return await self.update_entity(space, entity_data)
            except Exception as check_error:
                # 查询失败，可能是实体不存在，继续执行 INSERT
                if settings.KG_VERBOSE_LOGGING:
                    logger.debug(f"[插入实体] 检查实体存在性失败（可能不存在）: {check_error}")
            
            # 实体不存在，使用 INSERT
            # 使用单行格式，避免换行导致的语法错误
            # NebulaGraph 的 INSERT VERTEX 语法：所有字段都必须有值，空字符串也是值
            nGQL = f'INSERT VERTEX entity(name, type, description, aliases, confidence, metadata, mysql_id, user_id, created_at, updated_at) VALUES "{vid}":("{name}", "{entity_type}", "{description}", "{aliases_str}", {confidence}, "{metadata_str}", {mysql_id}, {user_id}, timestamp(), timestamp());'
            
            # 调试：仅在启用详细日志时记录生成的 nGQL
            if settings.KG_VERBOSE_LOGGING:
                logger.debug(f"[插入实体] 生成的INSERT语句（前500字符）: {nGQL[:500]}")
            
            await self._execute(nGQL, space=space)
            if settings.KG_VERBOSE_LOGGING:
                logger.info(f"[插入实体] 创建实体成功: vid={vid}, name={name}, type={entity_type}, mysql_id={mysql_id} in space={space}")
            return vid
        except Exception as e:
            logger.error(f"[插入实体] 创建NebulaGraph实体失败: vid={vid}, name={entity_data.get('name')}, type={entity_data.get('type')}, 错误={e}, entity_data={entity_data}", exc_info=True)
            raise
    
    async def update_entity(self, space: str, entity_data: Dict) -> str:
        """使用 nGQL 更新节点"""
        vid = None
        try:
            await self.create_space_if_not_exists(space)
            
            vid = entity_data.get("id") or f"entity_{entity_data.get('mysql_id')}"
            if not vid:
                raise ValueError("必须提供id或mysql_id")
            
            # 转义字符串中的特殊字符（包括JSON字符串中的引号）
            def escape_string(s: str) -> str:
                if s is None or s == "":
                    return ""  # 空字符串，不是 NULL
                # 先转义反斜杠，再转义双引号
                return str(s).replace('\\', '\\\\').replace('"', '\\"')
            
            # 获取字段值，确保不为 None
            name = entity_data.get('name')
            entity_type = entity_data.get('type')
            description = entity_data.get('description')
            mysql_id = int(entity_data.get('mysql_id', 0)) if entity_data.get('mysql_id') is not None else 0
            user_id = int(entity_data.get('user_id', 0)) if entity_data.get('user_id') is not None else 0
            confidence = float(entity_data.get('confidence', settings.KG_ENTITY_DEFAULT_CONFIDENCE)) if entity_data.get('confidence') is not None else settings.KG_ENTITY_DEFAULT_CONFIDENCE
            
            # 验证必填字段
            if not name or not name.strip():
                raise ValueError(f"实体名称不能为空: entity_data={entity_data}")
            if not entity_type or not entity_type.strip():
                raise ValueError(f"实体类型不能为空: entity_data={entity_data}")
            
            # 转义字符串字段
            name = escape_string(name)
            entity_type = escape_string(entity_type)
            description = escape_string(description or "")
            
            # JSON字符串需要额外转义
            aliases = entity_data.get('aliases', [])
            if not aliases:
                aliases = []
            aliases_str = json.dumps(aliases).replace('\\', '\\\\').replace('"', '\\"')
            
            metadata = entity_data.get('metadata', {})
            if not metadata:
                metadata = {}
            metadata_str = json.dumps(metadata).replace('\\', '\\\\').replace('"', '\\"')
            
            # 使用 DELETE + INSERT 方式更新实体
            # 注意：UPDATE VERTEX 在 NebulaGraph 某些版本中可能不支持或不可靠，直接使用 DELETE + INSERT 方式
            if settings.KG_VERBOSE_LOGGING:
                logger.debug(f"[更新实体] 使用DELETE + INSERT方式更新: vid={vid}, name={name}, type={entity_type}, mysql_id={mysql_id}")
            
            try:
                # 删除旧节点（会自动删除相关的关系）
                await self._execute(f'DELETE VERTEX "{vid}";', space=space)
                
                # 使用INSERT VERTEX重新插入（包含所有字段）
                insert_nGQL = f'INSERT VERTEX entity(name, type, description, aliases, confidence, metadata, mysql_id, user_id, created_at, updated_at) VALUES "{vid}":("{name}", "{entity_type}", "{description}", "{aliases_str}", {confidence}, "{metadata_str}", {mysql_id}, {user_id}, timestamp(), timestamp());'
                await self._execute(insert_nGQL, space=space)
                
                if settings.KG_VERBOSE_LOGGING:
                    logger.info(f"[更新实体] 使用DELETE + INSERT方式更新成功: vid={vid}, name={name}, type={entity_type}, mysql_id={mysql_id} in space={space}")
            except Exception as e:
                logger.error(f"[更新实体] DELETE + INSERT方式失败: {e}")
                raise
            return vid
        except Exception as e:
            logger.error(f"[更新实体] 更新NebulaGraph实体失败: vid={vid}, name={entity_data.get('name')}, type={entity_data.get('type')}, 错误={e}, entity_data={entity_data}", exc_info=True)
            raise
    
    async def create_relationship(
        self, space: str, source_vid: str, target_vid: str, rel_data: Dict
    ) -> bool:
        """创建关系（边）"""
        try:
            await self.create_space_if_not_exists(space)
            
            # 转义字符串中的特殊字符（包括JSON字符串中的引号）
            def escape_string(s: str) -> str:
                if s is None:
                    return ""
                # 先转义反斜杠，再转义双引号
                return str(s).replace('\\', '\\\\').replace('"', '\\"')
            
            relation_type = escape_string(rel_data.get('relation_type', 'related_to'))
            description = escape_string(rel_data.get('description', ''))
            weight = float(rel_data.get("weight", 0.5)) if rel_data.get("weight") is not None else 0.5
            confidence = float(rel_data.get("confidence", settings.KG_RELATIONSHIP_DEFAULT_CONFIDENCE)) if rel_data.get("confidence") is not None else settings.KG_RELATIONSHIP_DEFAULT_CONFIDENCE
            mysql_id = int(rel_data.get("mysql_id", 0)) if rel_data.get("mysql_id") is not None else 0
            user_id = int(rel_data.get("user_id", 0)) if rel_data.get("user_id") is not None else 0
            
            # 验证数据
            if not relation_type or relation_type.strip() == "":
                raise ValueError(f"关系类型不能为空: source_vid={source_vid}, target_vid={target_vid}")
            
            # JSON字符串需要额外转义
            metadata = rel_data.get('metadata', {}) if isinstance(rel_data.get('metadata'), dict) else {}
            metadata_str = json.dumps(metadata).replace('\\', '\\\\').replace('"', '\\"')
            
            # 使用单行格式，避免换行导致的语法错误
            nGQL = f'INSERT EDGE relationship(relation_type, description, weight, confidence, metadata, mysql_id, user_id, created_at, updated_at) VALUES "{source_vid}" -> "{target_vid}":("{relation_type}", "{description}", {weight}, {confidence}, "{metadata_str}", {mysql_id}, {user_id}, timestamp(), timestamp());'
            
            await self._execute(nGQL, space=space)
            # 不再记录每个关系的成功日志，只在错误时记录
            return True
        except Exception as e:
            logger.error(f"[插入关系] 创建NebulaGraph关系失败: source_vid={source_vid}, target_vid={target_vid}, "
                        f"type={rel_data.get('relation_type')}, 错误={e}, rel_data={rel_data}", exc_info=True)
            raise
    
    async def find_paths(
        self, space: str, source_vid: str, target_vid: str, max_hops: int = 3
    ) -> List[Dict]:
        """使用 nGQL 查找路径"""
        try:
            await self.create_space_if_not_exists(space)
            
            nGQL = f"""
            FIND SHORTEST PATH FROM "{source_vid}" TO "{target_vid}" 
            OVER relationship 
            UPTO {max_hops} STEPS;
            """
            result = await self._execute(nGQL, space=space)
            
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
            MATCH (v:entity)-[e:relationship]->(n:entity)
            WHERE id(v) == "{entity_vid}"
            {"AND " + relation_filter if relation_filter else ""}
            RETURN id(n) as vid, n.name as name, n.type as type, e.relation_type as relation_type, e.weight as weight
            LIMIT 100;
            """
            result = await self._execute(nGQL, space=space)
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
            MATCH (n:entity)
            WHERE n.name CONTAINS "{keyword}"
            {type_filter}
            RETURN id(n) as vid, n.name as name, n.type as type, n.description as description
            LIMIT 50;
            """
            result = await self._execute(nGQL, space=space)
            return result
        except Exception as e:
            logger.error(f"NebulaGraph实体搜索失败: {e}")
            raise
    
    async def list_entities(
        self,
        space: str,
        entity_type: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        size: int = 20
    ) -> Dict[str, Any]:
        """查询实体列表（支持分页和筛选）"""
        try:
            await self.create_space_if_not_exists(space)
            
            # 构建WHERE条件
            where_conditions = []
            if entity_type:
                where_conditions.append(f"n.type == '{entity_type}'")
            if keyword:
                where_conditions.append(f'n.name CONTAINS "{keyword}" OR n.description CONTAINS "{keyword}"')
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # 计算分页
            skip = (page - 1) * size
            
            # 查询总数
            count_nGQL = f"""
            MATCH (n:entity)
            {where_clause}
            RETURN count(n) as total;
            """
            count_result = await self._execute(count_nGQL, space=space)
            total = count_result[0].get('total', 0) if count_result else 0
            
            # 查询实体列表
            # 注意：NebulaGraph 的 ORDER BY 只能使用 RETURN 中定义的别名，不能使用属性路径
            list_nGQL = f"""
            MATCH (n:entity)
            {where_clause}
            RETURN id(n) as vid, n.name as name, n.type as type, n.description as description,
                   n.aliases as aliases, n.confidence as confidence, n.metadata as metadata,
                   n.mysql_id as mysql_id, n.user_id as user_id, n.created_at as created_at, n.updated_at as updated_at
            ORDER BY created_at DESC
            SKIP {skip} LIMIT {size};
            """
            entities = await self._execute(list_nGQL, space=space)
            
            # 解析结果
            result_list = []
            for entity in entities:
                # 解析JSON字段
                aliases = json.loads(entity.get('aliases', '[]')) if isinstance(entity.get('aliases'), str) else entity.get('aliases', [])
                metadata = json.loads(entity.get('metadata', '{}')) if isinstance(entity.get('metadata'), str) else entity.get('metadata', {})
                
                result_list.append({
                    'id': entity.get('mysql_id', 0),  # 使用MySQL ID作为主键
                    'vid': entity.get('vid'),
                    'name': entity.get('name'),
                    'type': entity.get('type'),
                    'description': entity.get('description'),
                    'aliases': aliases,
                    'confidence': float(entity.get('confidence', settings.KG_ENTITY_DEFAULT_CONFIDENCE)),
                    'metadata': metadata,
                    'user_id': entity.get('user_id', 0),
                    'created_at': entity.get('created_at'),
                    'updated_at': entity.get('updated_at')
                })
            
            return {
                'entities': result_list,
                'total': total,
                'page': page,
                'size': size
            }
        except Exception as e:
            logger.error(f"NebulaGraph实体列表查询失败: {e}")
            raise
    
    async def delete_entity(self, space: str, vid: str) -> bool:
        """删除实体"""
        try:
            await self.create_space_if_not_exists(space)
            
            nGQL = f"""
            DELETE VERTEX "{vid}";
            """
            await self._execute(nGQL, space=space)
            logger.debug(f"删除实体成功: {vid} in {space}")
            return True
        except Exception as e:
            logger.error(f"删除NebulaGraph实体失败: {e}")
            raise
    
    async def batch_delete_entities(self, space: str, vids: List[str]) -> Dict[str, int]:
        """批量删除实体
        
        Args:
            space: 图空间名称
            vids: 实体VID列表
            
        Returns:
            包含成功和失败数量的字典 {"success": int, "failed": int}
        """
        if not vids:
            return {"success": 0, "failed": 0}
        
        try:
            await self.create_space_if_not_exists(space)
            
            # NebulaGraph支持批量删除：DELETE VERTEX vid1, vid2, vid3
            # 但为了更好的错误处理和性能，我们分批删除（每批50个）
            batch_size = 50
            total_success = 0
            total_failed = 0
            
            for i in range(0, len(vids), batch_size):
                batch_vids = vids[i:i + batch_size]
                # 构建批量删除的nGQL语句
                vid_list = ", ".join([f'"{vid}"' for vid in batch_vids])
                nGQL = f"DELETE VERTEX {vid_list};"
                
                try:
                    await self._execute(nGQL, space=space)
                    total_success += len(batch_vids)
                    # 改为每10个批次或最后一批才打印日志，减少日志量
                    batch_num = i//batch_size + 1
                    total_batches = (len(vids) + batch_size - 1) // batch_size
                    if batch_num % 10 == 0 or batch_num == total_batches:
                        logger.debug(f"[批量删除] 批次 {batch_num}/{total_batches}: 已删除 {len(batch_vids)} 个实体 (累计: {total_success}/{len(vids)})")
                except Exception as e:
                    # 如果批量删除失败，回退到逐个删除
                    logger.warning(f"批量删除失败，回退到逐个删除: {e}")
                    for vid in batch_vids:
                        try:
                            await self.delete_entity(space, vid)
                            total_success += 1
                        except Exception as err:
                            total_failed += 1
                            logger.error(f"删除实体失败: vid={vid}, 错误={err}")
            
            logger.debug(f"[批量删除] ✅ 批量删除完成: 成功={total_success}, 失败={total_failed}, 总计={len(vids)}")
            return {"success": total_success, "failed": total_failed}
        except Exception as e:
            logger.error(f"批量删除NebulaGraph实体失败: {e}")
            # 如果批量删除完全失败，返回失败信息，但不抛出异常（允许继续执行）
            return {"success": 0, "failed": len(vids)}
    
    async def delete_relationship(
        self, space: str, source_vid: str, target_vid: str, relation_type: Optional[str] = None
    ) -> bool:
        """删除关系"""
        try:
            await self.create_space_if_not_exists(space)
            
            type_filter = f"AND e.relation_type == '{relation_type}'" if relation_type else ""
            
            nGQL = f"""
            MATCH (v:entity)-[e:relationship]->(n:entity)
            WHERE id(v) == "{source_vid}" AND id(n) == "{target_vid}"
            {type_filter}
            DELETE e;
            """
            await self._execute(nGQL, space=space)
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


# 全局图存储实例（用于应用关闭时清理）
_global_graph_storage_instance: Optional[NebulaGraphStorage] = None

def get_graph_storage() -> GraphStorageInterface:
    """获取图存储实例（根据配置返回NebulaGraph或Mock）"""
    global _global_graph_storage_instance
    
    try:
        from app.config.settings import settings
        
        # 检查是否启用NebulaGraph
        use_nebula = getattr(settings, 'USE_NEBULA_GRAPH', False)
        
        if use_nebula:
            # 如果已有全局实例，返回它（单例模式）
            if _global_graph_storage_instance is None:
                _global_graph_storage_instance = NebulaGraphStorage()
            return _global_graph_storage_instance
        else:
            logger.info("NebulaGraph未启用，使用Mock存储")
            return MockGraphStorage()
    except Exception as e:
        logger.warning(f"初始化NebulaGraph失败，使用Mock存储: {e}")
        return MockGraphStorage()

def close_global_graph_storage():
    """关闭全局图存储实例（应用关闭时调用）"""
    global _global_graph_storage_instance
    if _global_graph_storage_instance and hasattr(_global_graph_storage_instance, 'close'):
        _global_graph_storage_instance.close()
        _global_graph_storage_instance = None

# 注册退出时的清理函数（作为备用，防止lifespan未正确调用）
atexit.register(close_global_graph_storage)

