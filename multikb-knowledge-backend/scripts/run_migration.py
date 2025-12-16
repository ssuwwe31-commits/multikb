"""
执行数据库迁移脚本
"""

import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# 添加项目根目录到路径
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from app.config.settings import settings

def execute_migration(migration_file: str):
    """执行迁移SQL文件"""
    try:
        print(f"正在读取迁移文件: {migration_file}")
        
        # 读取SQL文件
        migration_path = _project_root / "migrations" / migration_file
        if not migration_path.exists():
            print(f"错误: 迁移文件不存在: {migration_path}")
            return False
        
        with open(migration_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        print(f"数据库连接: {settings.DATABASE_URL.replace(settings.MYSQL_PASSWORD, '***')}")
        print("正在执行迁移...")
        
        # 创建数据库引擎
        engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=300,
        )
        
        # 执行SQL（按语句分割执行，因为SQL文件可能包含多个语句）
        with engine.connect() as conn:
            # 分割SQL语句（按分号和换行）
            statements = []
            current_statement = []
            
            for line in sql_content.split('\n'):
                # 跳过注释和空行
                stripped = line.strip()
                if not stripped or stripped.startswith('--'):
                    continue
                
                current_statement.append(line)
                
                # 如果行以分号结尾，表示一个完整语句
                if stripped.endswith(';'):
                    statement = '\n'.join(current_statement)
                    if statement.strip():
                        statements.append(statement)
                    current_statement = []
            
            # 处理最后一个语句（如果没有分号）
            if current_statement:
                statement = '\n'.join(current_statement)
                if statement.strip():
                    statements.append(statement)
            
            # 执行每个语句
            executed = 0
            skipped = 0
            errors = []
            for i, statement in enumerate(statements, 1):
                try:
                    # 跳过USE语句（SQLAlchemy已经连接到指定数据库）
                    if statement.strip().upper().startswith('USE '):
                        print(f"跳过语句 {i}: USE (已连接到数据库)")
                        skipped += 1
                        continue
                    
                    print(f"执行语句 {i}/{len(statements)}...")
                    conn.execute(text(statement))
                    executed += 1
                except SQLAlchemyError as e:
                    # 检查是否是"已存在"的错误（表、索引、约束等）
                    error_msg = str(e).lower()
                    if any(keyword in error_msg for keyword in ['already exists', 'duplicate', 'exists', 'cannot add foreign key constraint']):
                        print(f"  警告: 语句 {i} 已存在或约束冲突，跳过: {str(e)[:150]}")
                        skipped += 1
                        continue
                    else:
                        error_info = f"语句 {i} 失败: {str(e)[:150]}"
                        print(f"  错误: {error_info}")
                        errors.append(error_info)
                        # 继续执行其他语句
                        continue
            
            # 提交事务
            conn.commit()
            print(f"\n迁移完成！成功执行 {executed}/{len(statements)} 个语句，跳过 {skipped} 个")
            if errors:
                print(f"\n警告: 有 {len(errors)} 个语句执行失败（已跳过）")
                for err in errors[:5]:  # 只显示前5个错误
                    print(f"  - {err}")
                if len(errors) > 5:
                    print(f"  ... 还有 {len(errors) - 5} 个错误")
            return True
            
    except FileNotFoundError as e:
        print(f"错误: 文件未找到: {e}")
        return False
    except SQLAlchemyError as e:
        print(f"错误: 数据库操作失败: {e}")
        return False
    except Exception as e:
        print(f"错误: 执行迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        migration_file = sys.argv[1]
    else:
        migration_file = "2025012001_user_authentication_tables.sql"
    
    print("=" * 60)
    print("数据库迁移工具")
    print("=" * 60)
    print(f"迁移文件: {migration_file}")
    print()
    
    success = execute_migration(migration_file)
    
    if success:
        print("\n[成功] 迁移完成！")
        sys.exit(0)
    else:
        print("\n[失败] 迁移失败！")
        sys.exit(1)
