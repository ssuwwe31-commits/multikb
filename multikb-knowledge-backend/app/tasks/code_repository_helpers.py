"""
代码库任务辅助函数
提供缓存管理、导入解析等工具函数
"""

import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.core.logging import logger


def delete_cache(db_session, repo_id: int, cache_type: str = None):
    """
    删除缓存（包括 MinIO 文件）
    
    Args:
        db_session: 数据库会话
        repo_id: 仓库ID
        cache_type: 缓存类型（如果为 None，删除所有类型的缓存）
    """
    try:
        # 1. 先查询所有需要删除的缓存记录（获取 minio_path，向后兼容）
        minio_paths = []
        try:
            if cache_type:
                query = text("""SELECT minio_path FROM code_analysis_cache 
                WHERE repository_id = :repo_id AND cache_type = :cache_type""")
                params = {"repo_id": repo_id, "cache_type": cache_type}
            else:
                query = text("""SELECT minio_path FROM code_analysis_cache 
                WHERE repository_id = :repo_id""")
                params = {"repo_id": repo_id}
            
            result = db_session.execute(query, params)
            minio_paths = [row[0] for row in result if row[0]]  # 只获取非空的 minio_path
        except Exception as e:
            # 如果表没有 minio_path 字段，跳过 MinIO 删除（向后兼容）
            if 'minio_path' in str(e).lower() or 'unknown column' in str(e).lower():
                logger.debug(f"表结构不支持 minio_path，跳过 MinIO 文件删除")
            else:
                raise
        
        # 2. 删除 MinIO 文件
        if minio_paths:
            try:
                from app.services.minio_storage_service import MinioStorageService
                minio_service = MinioStorageService()
                deleted_count = 0
                for minio_path in minio_paths:
                    try:
                        minio_service.delete_file(minio_path)
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"删除 MinIO 文件失败: {minio_path}, 错误: {e}")
                if deleted_count > 0:
                    logger.info(f"已删除 {deleted_count} 个 MinIO 缓存文件")
            except Exception as minio_error:
                logger.warning(f"删除 MinIO 缓存文件时出错: {minio_error}")
        
        # 3. 删除 MySQL 记录
        if cache_type:
            db_session.execute(
                text("DELETE FROM code_analysis_cache WHERE repository_id = :repo_id AND cache_type = :cache_type"),
                {"repo_id": repo_id, "cache_type": cache_type}
            )
        else:
            db_session.execute(
                text("DELETE FROM code_analysis_cache WHERE repository_id = :repo_id"),
                {"repo_id": repo_id}
            )
        db_session.commit()
        
    except Exception as e:
        logger.error(f"删除缓存失败: repo_id={repo_id}, cache_type={cache_type}, 错误: {e}")
        db_session.rollback()
        raise


def get_cache_data(db_session, repo_id: int, cache_type: str, cache_key: str = 'full') -> Optional[Dict[Any, Any]]:
    """
    从缓存中读取数据（支持 MySQL 和 MinIO）
    
    Args:
        db_session: 数据库会话
        repo_id: 仓库ID
        cache_type: 缓存类型
        cache_key: 缓存键（默认 'full'）
        
    Returns:
        缓存数据（字典），如果不存在则返回 None
    """
    try:
        # 向后兼容：先尝试查询包含 minio_path 的字段，如果失败则降级
        try:
            result = db_session.execute(
                text("""SELECT cache_data, minio_path FROM code_analysis_cache 
                WHERE repository_id = :repo_id AND cache_type = :cache_type AND cache_key = :cache_key
                AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY created_at DESC LIMIT 1"""),
                {"repo_id": repo_id, "cache_type": cache_type, "cache_key": cache_key}
            ).fetchone()
            
            if not result:
                return None
            
            cache_data_json, minio_path = result
        except Exception as e:
            # 如果表没有 minio_path 字段，降级到只查询 cache_data
            if 'minio_path' in str(e).lower() or 'unknown column' in str(e).lower():
                logger.debug(f"表结构不支持 minio_path，使用降级查询")
                result = db_session.execute(
                    text("""SELECT cache_data FROM code_analysis_cache 
                    WHERE repository_id = :repo_id AND cache_type = :cache_type AND cache_key = :cache_key
                    AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY created_at DESC LIMIT 1"""),
                    {"repo_id": repo_id, "cache_type": cache_type, "cache_key": cache_key}
                ).fetchone()
                
                if not result:
                    return None
                
                cache_data_json = result[0]
                minio_path = None
            else:
                raise
        
        # 如果数据存储在 MinIO
        if minio_path:
            try:
                from app.services.minio_storage_service import MinioStorageService
                minio_service = MinioStorageService()
                file_content = minio_service.download_file(minio_path)
                cache_data = json.loads(file_content.decode('utf-8'))
                logger.debug(f"从 MinIO 读取缓存: {minio_path}")
                return cache_data
            except Exception as minio_error:
                logger.error(f"从 MinIO 读取缓存失败: {minio_path}, 错误: {minio_error}")
                # 如果 MinIO 读取失败，尝试从 MySQL 读取（降级）
                if cache_data_json:
                    return json.loads(cache_data_json)
                return None
        
        # 如果数据存储在 MySQL
        if cache_data_json:
            return json.loads(cache_data_json)
        
        return None
        
    except Exception as e:
        logger.error(f"读取缓存失败: repo_id={repo_id}, cache_type={cache_type}, 错误: {e}")
        return None


def resolve_import_to_file_path(
    module: str, 
    source_file: str, 
    all_files: List[str],
    repo_path: Optional[str] = None
) -> Optional[str]:
    """
    解析导入模块，查找对应的本地文件路径
    
    Args:
        module: 模块名
        source_file: 源文件路径
        all_files: 所有文件路径列表
        repo_path: 仓库根路径（可选）
        
    Returns:
        目标文件路径，如果不是本地文件则返回 None
    """
    if not module:
        return None
    
    # 跳过外部包（简单启发式）
    if not module.startswith('.') and not module.startswith('/'):
        # 如果不包含路径分隔符，可能是外部包
        if '/' not in module and '\\' not in module:
            return None
    
    # 处理相对导入（Python/TypeScript）
    if module.startswith('.'):
        source_dir = os.path.dirname(source_file)
        # 处理多个点（如 ..module）
        dots = 0
        while module.startswith('.'):
            dots += 1
            module = module[1:]
        if dots > 1:
            for _ in range(dots - 1):
                source_dir = os.path.dirname(source_dir)
        
        # 尝试不同扩展名
        for ext in ['', '.py', '.js', '.ts', '.jsx', '.tsx']:
            potential_path = os.path.join(source_dir, module + ext).replace('\\', '/')
            # 标准化路径
            potential_path = os.path.normpath(potential_path).replace('\\', '/')
            # 检查是否在文件列表中
            for file_path in all_files:
                if file_path.replace('\\', '/') == potential_path or file_path.replace('\\', '/').endswith(potential_path):
                    return file_path
    
    # 处理绝对路径或相对路径
    else:
        # 移除可能的扩展名
        module_base = module.rsplit('.', 1)[0] if '.' in module else module
        # 尝试不同扩展名
        for ext in ['', '.py', '.js', '.ts', '.jsx', '.tsx']:
            potential_path = (module_base + ext).replace('\\', '/')
            # 检查是否在文件列表中
            for file_path in all_files:
                file_path_normalized = file_path.replace('\\', '/')
                if file_path_normalized == potential_path or file_path_normalized.endswith('/' + potential_path):
                    return file_path
                # 也检查文件名匹配
                if os.path.basename(file_path_normalized) == os.path.basename(potential_path):
                    return file_path
    
    return None


def save_cache_with_retry(conn, repo_id: int, cache_type: str, cache_key: str, cache_data: str, expires_at: datetime, max_retries: int = 3):
    """
    保存缓存数据，带重试机制（处理 MySQL 连接超时问题）
    
    智能存储策略：
    - 小数据（< 1MB）：直接存储在 MySQL
    - 大数据（>= 1MB）：存储到 MinIO，MySQL 只存储路径
    
    注意：此函数会修改传入的 conn 对象（在重试时）
    
    Args:
        conn: 数据库连接（可能被修改）
        repo_id: 仓库ID
        cache_type: 缓存类型
        cache_key: 缓存键
        cache_data: 缓存数据（JSON 字符串）
        expires_at: 过期时间
        max_retries: 最大重试次数
    """
    from app.config.database import engine
    from sqlalchemy.exc import IntegrityError
    import time
    
    # 阈值：超过 1MB 的数据存储到 MinIO
    CACHE_SIZE_THRESHOLD = 1 * 1024 * 1024  # 1MB
    cache_size = len(cache_data.encode('utf-8'))
    cache_size_mb = cache_size / (1024 * 1024)
    
    # 如果数据超过阈值，存储到 MinIO
    if cache_size >= CACHE_SIZE_THRESHOLD:
        try:
            from app.services.minio_storage_service import MinioStorageService
            minio_service = MinioStorageService()
            
            # 生成 MinIO 路径：code-cache/{repo_id}/{cache_type}/{cache_key}.json
            minio_path = f"code-cache/{repo_id}/{cache_type}/{cache_key}.json"
            
            # 上传到 MinIO
            minio_service.upload_bytes(
                object_name=minio_path,
                data=cache_data.encode('utf-8'),
                content_type="application/json"
            )
            
            logger.info(f"✅ 大文件已存储到 MinIO: {minio_path} ({cache_size_mb:.2f} MB)")
            
            # MySQL 只存储元数据（路径和大小）
            # 注意：需要检查表是否有 minio_path 字段，如果没有则降级到精简数据
            try:
                conn.execute(
                    text("""INSERT INTO code_analysis_cache 
                    (repository_id, cache_type, cache_key, minio_path, file_size, expires_at)
                    VALUES (:repo_id, :cache_type, :cache_key, :minio_path, :file_size, :expires_at)
                    ON DUPLICATE KEY UPDATE minio_path = VALUES(minio_path), file_size = VALUES(file_size), expires_at = VALUES(expires_at), cache_data = NULL"""),
                    {
                        "repo_id": repo_id,
                        "cache_type": cache_type,
                        "cache_key": cache_key,
                        "minio_path": minio_path,
                        "file_size": cache_size,
                        "expires_at": expires_at
                    }
                )
                logger.info(f"✅ 缓存元数据已保存到 MySQL: repo_id={repo_id}, cache_type={cache_type}, minio_path={minio_path}")
                return  # 成功，退出
            except Exception as mysql_error:
                # 如果表结构不支持 minio_path（旧版本），保存占位记录
                error_str = str(mysql_error).lower()
                if 'minio_path' in error_str or 'unknown column' in error_str:
                    logger.warning(f"⚠️ 表结构不支持 minio_path，保存占位记录到 MySQL（数据已存储在 MinIO: {minio_path}）")
                    try:
                        # 保存一个占位记录，cache_data 为 NULL，表示数据在 MinIO
                        # 注意：这里不包含 minio_path，因为表不支持该字段
                        conn.execute(
                            text("""INSERT INTO code_analysis_cache 
                            (repository_id, cache_type, cache_key, cache_data, expires_at)
                            VALUES (:repo_id, :cache_type, :cache_key, NULL, :expires_at)
                            ON DUPLICATE KEY UPDATE cache_data = NULL, expires_at = VALUES(expires_at)"""),
                            {
                                "repo_id": repo_id,
                                "cache_type": cache_type,
                                "cache_key": cache_key,
                                "expires_at": expires_at
                            }
                        )
                        logger.warning(f"⚠️ 已保存占位记录（cache_data=NULL），但数据实际在 MinIO: {minio_path}")
                        logger.warning(f"⚠️ 提示：请运行数据库迁移脚本添加 minio_path 字段，否则无法从 MinIO 读取数据")
                        return  # 占位记录已保存，退出
                    except Exception as placeholder_error:
                        logger.error(f"❌ 保存占位记录也失败: {placeholder_error}")
                        # 继续执行精简逻辑（见下方）
                else:
                    # 其他 MySQL 错误，继续执行精简逻辑
                    logger.warning(f"⚠️ MySQL 保存失败，降级到精简数据: {mysql_error}")
        except Exception as minio_error:
            logger.error(f"❌ MinIO 存储失败，降级到精简数据: {minio_error}")
            # 继续执行精简逻辑（见下方）
    
    # 小数据或 MinIO 失败时，直接存储在 MySQL
    for attempt in range(max_retries):
        try:
            # 检查数据大小
            if cache_size_mb > 3:
                logger.warning(f"⚠️ 缓存数据较大 ({cache_size_mb:.2f} MB)，可能超过 MySQL max_allowed_packet (默认 4MB)")
                logger.info(f"   提示：如果保存失败，请增加 MySQL 的 max_allowed_packet 配置：SET GLOBAL max_allowed_packet=67108864; (64MB)")
            
            # 尝试执行插入
            conn.execute(
                text("""INSERT INTO code_analysis_cache 
                (repository_id, cache_type, cache_key, cache_data, expires_at)
                VALUES (:repo_id, :cache_type, :cache_key, :cache_data, :expires_at)
                ON DUPLICATE KEY UPDATE cache_data = VALUES(cache_data), expires_at = VALUES(expires_at)"""),
                {
                    "repo_id": repo_id,
                    "cache_type": cache_type,
                    "cache_key": cache_key,
                    "cache_data": cache_data,
                    "expires_at": expires_at
                }
            )
            return  # 成功，退出
            
        except IntegrityError as e:
            # 外键约束错误（1452）：仓库不存在
            error_code = e.orig.args[0] if hasattr(e, 'orig') and hasattr(e.orig, 'args') and len(e.orig.args) > 0 else None
            if error_code == 1452 and 'foreign key constraint fails' in str(e).lower():
                logger.warning(f"仓库 {repo_id} 不存在，跳过缓存保存（可能已被删除）")
                return  # 优雅地失败，不抛出异常
            else:
                # 其他完整性错误，直接抛出
                logger.error(f"保存缓存时发生完整性错误: {e}")
                raise
        except OperationalError as e:
            error_code = e.orig.args[0] if hasattr(e, 'orig') and hasattr(e.orig, 'args') and len(e.orig.args) > 0 else None
            error_msg = str(e).lower()
            
            # 检查是否是 max_allowed_packet 错误 (1153)
            if error_code == 1153 or 'max_allowed_packet' in error_msg:
                data_size_mb = len(cache_data.encode('utf-8')) / (1024 * 1024)
                logger.error(f"❌ MySQL max_allowed_packet 错误: 尝试保存 {data_size_mb:.2f} MB 的数据")
                logger.error(f"   错误详情: {e}")
                logger.error(f"   解决方案:")
                logger.error(f"   1. 增加 MySQL 的 max_allowed_packet 配置:")
                logger.error(f"      SET GLOBAL max_allowed_packet=67108864;  # 64MB")
                logger.error(f"   2. 或者在 my.cnf 中配置: max_allowed_packet=64M")
                logger.error(f"   3. 当前数据将被精简后重试")
                
                # 如果数据仍然很大，尝试进一步精简
                if data_size_mb > 1:
                    try:
                        cache_obj = json.loads(cache_data)
                        # 如果包含 files 列表，精简它
                        if 'files' in cache_obj and isinstance(cache_obj['files'], list):
                            logger.warning(f"   精简文件列表: {len(cache_obj['files'])} 个文件")
                            simplified_files = []
                            for file_data in cache_obj['files']:
                                if isinstance(file_data, dict):
                                    simplified_file = {
                                        'path': file_data.get('path', ''),
                                        'language': file_data.get('language', ''),
                                        'lines': file_data.get('lines', 0),
                                        'symbol_count': len(file_data.get('symbols', [])) if 'symbols' in file_data else 0
                                    }
                                    simplified_files.append(simplified_file)
                            cache_obj['files'] = simplified_files
                            cache_obj['note'] = '数据已精简：移除了详细的符号列表以符合 MySQL max_allowed_packet 限制'
                            cache_data = json.dumps(cache_obj)
                            new_size_mb = len(cache_data.encode('utf-8')) / (1024 * 1024)
                            logger.info(f"   ✅ 精简后大小: {data_size_mb:.2f} MB -> {new_size_mb:.2f} MB")
                            
                            # 如果精简后仍然太大，只保存统计信息
                            if new_size_mb > 3:
                                logger.warning(f"   精简后仍然过大，只保存统计信息")
                                if 'statistics' in cache_obj:
                                    cache_data = json.dumps({'statistics': cache_obj['statistics'], 'file_count': len(cache_obj.get('files', []))})
                                else:
                                    cache_data = json.dumps({'file_count': len(cache_obj.get('files', []))})
                    except Exception as simplify_error:
                        logger.warning(f"   精简数据失败: {simplify_error}，尝试只保存统计信息")
                        try:
                            cache_obj = json.loads(cache_data)
                            if 'statistics' in cache_obj:
                                cache_data = json.dumps({'statistics': cache_obj['statistics'], 'file_count': cache_obj.get('file_count', 0)})
                        except:
                            pass
                
                # 重试保存精简后的数据
                if attempt < max_retries - 1:
                    logger.info(f"   重试保存精简后的数据 (尝试 {attempt + 1}/{max_retries})")
                    continue
                else:
                    logger.error(f"   保存缓存失败，已重试 {max_retries} 次，数据已精简到最小")
                    raise
            
            # MySQL server has gone away (2006) 或连接被中止
            elif error_code in (2006, 2013) or 'gone away' in error_msg or 'ConnectionAbortedError' in str(e):
                if attempt < max_retries - 1:
                    logger.warning(f"数据库连接断开，重试 {attempt + 1}/{max_retries}: {e}")
                    time.sleep(1)  # 等待 1 秒后重试
                    
                    # 关闭旧连接并重新获取
                    try:
                        conn.close()
                    except:
                        pass
                    conn = engine.connect()
                    continue
                else:
                    logger.error(f"保存缓存失败，已重试 {max_retries} 次: {e}")
                    raise
            else:
                # 其他错误，直接抛出
                raise
        except Exception as e:
            logger.error(f"保存缓存时发生未知错误: {e}")
            raise
