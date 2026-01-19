"""
代码库异步任务主入口
所有任务已按功能拆分到不同文件

文件结构：
- code_repository_helpers.py: 辅助函数（缓存、导入解析等）
- code_repository_clone_helpers.py: 克隆任务辅助函数（保存文件和符号）
- code_repository_clone_tasks.py: 克隆相关任务（clone_and_analyze, update_repository）
- code_repository_wiki_tasks.py: Wiki 相关任务（generate_wiki_content, delayed_release_wiki_lock）
- code_repository_delete_tasks.py: 删除相关任务（delete_repository, cleanup_old_repositories）
- code_repository_analysis_tasks.py: 分析相关任务（analyze_with_agent, analyze_code_structure）
"""

# 从各个任务模块导入所有任务，确保 Celery 能够发现它们
from app.tasks.code_repository_clone_tasks import (
    clone_and_analyze,
    update_repository
)

from app.tasks.code_repository_wiki_tasks import (
    generate_wiki_content,
    delayed_release_wiki_lock
)

from app.tasks.code_repository_delete_tasks import (
    delete_repository,
    cleanup_old_repositories
)

from app.tasks.code_repository_analysis_tasks import (
    analyze_with_agent,
    analyze_code_structure
)

# 导出所有任务，确保可以被 Celery 发现
__all__ = [
    'clone_and_analyze',
    'update_repository',
    'generate_wiki_content',
    'delayed_release_wiki_lock',
    'delete_repository',
    'cleanup_old_repositories',
    'analyze_with_agent',
    'analyze_code_structure',
]
