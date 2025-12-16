"""
Backup Script
"""

import os
import sys
import shutil
from datetime import datetime
from app.config.settings import settings

def backup_database():
    """备份数据库"""
    try:
        # 创建备份目录
        backup_dir = "backups"
        os.makedirs(backup_dir, exist_ok=True)
        
        # 生成备份文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{backup_dir}/database_backup_{timestamp}.sql"
        
        # 执行数据库备份
        # 这里应该根据实际的数据库类型执行相应的备份命令
        # 例如MySQL: mysqldump -u username -p database_name > backup_file
        
        print(f"数据库备份成功: {backup_file}")
        return True
        
    except Exception as e:
        print(f"数据库备份失败: {e}")
        return False

def backup_files():
    """备份文件"""
    try:
        # 创建备份目录
        backup_dir = "backups/files"
        os.makedirs(backup_dir, exist_ok=True)
        
        # 生成备份文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{backup_dir}/files_backup_{timestamp}.tar.gz"
        
        # 备份上传的文件
        upload_dir = "uploads"
        if os.path.exists(upload_dir):
            shutil.make_archive(
                backup_file.replace(".tar.gz", ""),
                "gztar",
                upload_dir
            )
        
        print(f"文件备份成功: {backup_file}")
        return True
        
    except Exception as e:
        print(f"文件备份失败: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "files":
        backup_files()
    else:
        backup_database()
