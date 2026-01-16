"""
Git 服务
负责代码仓库的克隆、拉取和管理
"""

import os
import shutil
from typing import Optional, Callable
from pathlib import Path

import git
from git import Repo, GitCommandError

from app.core.logging import logger
from app.config.settings import settings


class GitService:
    """Git 仓库管理服务"""
    
    def __init__(self):
        """初始化 Git 服务"""
        self.base_path = getattr(settings, 'CODE_REPO_CLONE_DIR', '/data/code_repositories')
        # 确保基础目录存在
        os.makedirs(self.base_path, exist_ok=True)
        logger.info(f"Git 服务初始化完成，存储路径: {self.base_path}")
    
    def get_repo_path(self, repo_id: int) -> str:
        """
        获取仓库本地路径
        
        Args:
            repo_id: 仓库ID
            
        Returns:
            本地路径字符串
        """
        return os.path.join(self.base_path, str(repo_id))
    
    def clone_repository(
        self, 
        repo_id: int, 
        repo_url: str,
        branch: str = 'main',
        shallow: bool = True,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> str:
        """
        克隆仓库到本地
        
        Args:
            repo_id: 仓库ID
            repo_url: 仓库URL
            branch: 分支名称
            shallow: 是否浅克隆（默认True，节省空间）
            progress_callback: 进度回调函数
            
        Returns:
            本地路径
            
        Raises:
            GitCommandError: Git 命令执行失败
        """
        local_path = self.get_repo_path(repo_id)
        
        # 如果目录已存在，先删除
        if os.path.exists(local_path):
            logger.warning(f"目录已存在，删除旧目录: {local_path}")
            shutil.rmtree(local_path)
        
        try:
            logger.info(f"开始克隆仓库: {repo_url} -> {local_path}")
            
            # 克隆配置
            clone_kwargs = {
                'depth': 1 if shallow else None,  # 浅克隆只拉取最近一次提交
                'single_branch': True,  # 只克隆指定分支
                'branch': branch,
                # 跳过 Git LFS 文件下载（避免 LFS 预算问题，且对代码分析不重要）
                'env': {
                    'GIT_LFS_SKIP_SMUDGE': '1'  # 跳过 LFS 文件的实际下载
                }
            }
            
            # 注意：GitPython 的进度回调在某些环境下不稳定，暂时禁用
            # 我们通过任务状态更新来跟踪进度
            # if progress_callback:
            #     clone_kwargs['progress'] = ...
            
            # 如果提供了进度回调，在开始时调用一次表示开始
            if progress_callback:
                try:
                    progress_callback(0.1)  # 10% - 开始克隆
                except Exception as e:
                    logger.debug(f"进度回调失败: {e}")
            
            # 执行克隆
            repo = Repo.clone_from(repo_url, local_path, **clone_kwargs)
            
            logger.info(f"克隆完成: {local_path}")
            
            # 如果提供了进度回调，在完成时调用表示完成
            if progress_callback:
                try:
                    progress_callback(1.0)  # 100% - 克隆完成
                except Exception as e:
                    logger.debug(f"进度回调失败: {e}")
            
            # 返回最后一次提交信息
            last_commit = repo.head.commit
            logger.info(f"最新提交: {last_commit.hexsha[:8]} - {last_commit.message.strip()}")
            
            return local_path
            
        except GitCommandError as e:
            logger.error(f"克隆失败: {e}")
            # 清理失败的克隆（使用权限处理函数）
            if os.path.exists(local_path):
                try:
                    import stat
                    def handle_remove_readonly(func, path, exc):
                        """处理只读文件删除"""
                        try:
                            os.chmod(path, stat.S_IWRITE)
                            func(path)
                        except Exception:
                            pass
                    shutil.rmtree(local_path, onerror=handle_remove_readonly)
                except Exception as cleanup_error:
                    logger.warning(f"清理失败的克隆目录时出错: {cleanup_error}")
            raise
        except Exception as e:
            logger.error(f"克隆过程出错: {e}")
            if os.path.exists(local_path):
                shutil.rmtree(local_path)
            raise
    
    def pull_repository(
        self, 
        repo_id: int,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> dict:
        """
        拉取仓库更新（增量更新）
        
        Args:
            repo_id: 仓库ID
            progress_callback: 进度回调
            
        Returns:
            更新信息字典，包含：
            - old_commit: 更新前的 commit hash
            - new_commit: 更新后的 commit hash
            - changed: 是否有更新
            - changed_files: 变更文件列表
        """
        local_path = self.get_repo_path(repo_id)
        
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"仓库路径不存在: {local_path}")
        
        try:
            repo = Repo(local_path)
            
            # 获取更新前的 commit
            old_commit = repo.head.commit.hexsha
            logger.info(f"当前 commit: {old_commit[:8]}")
            
            # 执行 pull
            origin = repo.remotes.origin
            
            if progress_callback:
                class ProgressPrinter(git.RemoteProgress):
                    def update(self, op_code, cur_count, max_count=None, message=''):
                        if max_count:
                            progress = cur_count / max_count
                            progress_callback(progress)
                
                origin.pull(progress=ProgressPrinter())
            else:
                origin.pull()
            
            # 获取更新后的 commit
            new_commit = repo.head.commit.hexsha
            logger.info(f"更新后 commit: {new_commit[:8]}")
            
            # 检查是否有变更
            if old_commit == new_commit:
                logger.info("没有新的更新")
                return {
                    'old_commit': old_commit,
                    'new_commit': new_commit,
                    'changed': False,
                    'changed_files': []
                }
            
            # 获取变更文件列表
            changed_files = self.get_changed_files(repo_id, old_commit, new_commit)
            
            logger.info(f"更新完成，变更文件数: {len(changed_files)}")
            
            return {
                'old_commit': old_commit,
                'new_commit': new_commit,
                'changed': True,
                'changed_files': changed_files
            }
            
        except GitCommandError as e:
            logger.error(f"拉取失败: {e}")
            raise
    
    def get_changed_files(self, repo_id: int, old_commit: str, new_commit: str) -> list:
        """
        获取两个 commit 之间的变更文件
        
        Args:
            repo_id: 仓库ID
            old_commit: 旧 commit hash
            new_commit: 新 commit hash
            
        Returns:
            变更文件列表，每项包含：
            - path: 文件路径
            - change_type: 变更类型 (A/M/D/R)
        """
        local_path = self.get_repo_path(repo_id)
        repo = Repo(local_path)
        
        try:
            old = repo.commit(old_commit)
            new = repo.commit(new_commit)
            
            # 对比差异
            diff = old.diff(new)
            
            changed_files = []
            for item in diff:
                # A = Added, M = Modified, D = Deleted, R = Renamed
                if item.a_path:
                    changed_files.append({
                        'path': item.a_path,
                        'change_type': item.change_type
                    })
                
                # 处理重命名
                if item.change_type == 'R' and item.b_path:
                    changed_files.append({
                        'path': item.b_path,
                        'change_type': 'A'  # 重命名后的文件视为新增
                    })
            
            return changed_files
            
        except Exception as e:
            logger.error(f"获取变更文件失败: {e}")
            return []
    
    def get_repo_info(self, repo_id: int) -> dict:
        """
        获取仓库信息
        
        Args:
            repo_id: 仓库ID
            
        Returns:
            仓库信息字典
        """
        local_path = self.get_repo_path(repo_id)
        
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"仓库路径不存在: {local_path}")
        
        repo = Repo(local_path)
        
        # 获取最新 commit
        last_commit = repo.head.commit
        
        # 统计文件数（排除 .git 目录）
        total_files = sum(1 for _ in Path(local_path).rglob('*') 
                         if _.is_file() and '.git' not in str(_))
        
        # 转换日期时间为 MySQL 可接受的格式（去掉时区信息）
        commit_datetime = last_commit.committed_datetime
        # 移除时区信息，使用本地时间
        if commit_datetime.tzinfo is not None:
            commit_datetime = commit_datetime.replace(tzinfo=None)
        
        return {
            'local_path': local_path,
            'branch': repo.active_branch.name,
            'last_commit_hash': last_commit.hexsha,
            'last_commit_date': commit_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'last_commit_message': last_commit.message.strip(),
            'total_files': total_files,
            'repo_size_mb': self.get_directory_size(local_path) / (1024 * 1024)
        }
    
    def delete_repository(self, repo_id: int) -> bool:
        """
        删除本地仓库（处理 Windows 文件权限问题）
        
        Args:
            repo_id: 仓库ID
            
        Returns:
            是否成功删除
        """
        import stat
        
        local_path = self.get_repo_path(repo_id)
        
        if not os.path.exists(local_path):
            logger.warning(f"仓库路径不存在: {local_path}")
            return False
        
        def handle_remove_readonly(func, path, exc):
            """处理只读文件删除"""
            try:
                # 移除只读属性
                os.chmod(path, stat.S_IWRITE)
                # 重新尝试删除
                func(path)
            except Exception as e:
                logger.warning(f"无法删除文件: {path}, 错误: {e}")
        
        try:
            shutil.rmtree(local_path, onerror=handle_remove_readonly)
            logger.info(f"删除仓库成功: {local_path}")
            return True
        except Exception as e:
            logger.error(f"删除仓库失败: {e}")
            return False
    
    @staticmethod
    def get_directory_size(path: str) -> int:
        """
        计算目录大小（字节）
        
        Args:
            path: 目录路径
            
        Returns:
            大小（字节）
        """
        total = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total += os.path.getsize(filepath)
        except Exception as e:
            logger.error(f"计算目录大小失败: {e}")
        
        return total
    
    def cleanup_old_repositories(self, days: int = 30) -> int:
        """
        清理长期未使用的仓库
        
        Args:
            days: 天数阈值
            
        Returns:
            清理的仓库数量
        """
        import time
        from datetime import datetime, timedelta
        
        threshold = time.time() - (days * 24 * 60 * 60)
        cleaned = 0
        
        try:
            for dir_name in os.listdir(self.base_path):
                repo_path = os.path.join(self.base_path, dir_name)
                
                if not os.path.isdir(repo_path):
                    continue
                
                # 检查最后访问时间
                last_access = os.path.getatime(repo_path)
                
                if last_access < threshold:
                    logger.info(f"清理旧仓库: {dir_name}")
                    shutil.rmtree(repo_path)
                    cleaned += 1
            
            logger.info(f"清理完成，共清理 {cleaned} 个仓库")
            return cleaned
            
        except Exception as e:
            logger.error(f"清理仓库失败: {e}")
            return cleaned
