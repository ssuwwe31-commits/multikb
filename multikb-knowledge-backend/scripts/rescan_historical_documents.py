"""
为历史文档进行安全扫描补扫
从 MinIO 读取历史文档文件，进行安全扫描，并更新数据库记录
"""

import sys
import io
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# 设置标准输出为 UTF-8 编码（Windows 兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from app.config.settings import settings
from app.services.file_validation_service import FileValidationService
from app.services.minio_storage_service import MinioStorageService
from app.core.logging import logger
import pymysql
from io import BytesIO

class HistoricalDocumentRescanner:
    """历史文档补扫描器"""
    
    def __init__(self):
        self.file_validation = FileValidationService()
        self.minio_storage = MinioStorageService()
        self._db_connection = None
    
    def _get_db_connection(self):
        """获取数据库连接"""
        if self._db_connection is None:
            db_url = settings.DATABASE_URL
            if db_url.startswith('mysql+pymysql://'):
                db_url = db_url.replace('mysql+pymysql://', '')
            
            parts = db_url.split('@')
            user_pass = parts[0].split(':')
            host_db = parts[1].split('/')
            
            username = user_pass[0]
            password = user_pass[1]
            host_port = host_db[0].split(':')
            host = host_port[0]
            port = int(host_port[1]) if len(host_port) > 1 else 3306
            database = host_db[1]
            
            self._db_connection = pymysql.connect(
                host=host,
                port=port,
                user=username,
                password=password,
                database=database,
                charset='utf8mb4'
            )
        return self._db_connection
    
    def _close_db_connection(self):
        """关闭数据库连接"""
        if self._db_connection:
            self._db_connection.close()
            self._db_connection = None
    
    def get_historical_documents(self, limit: Optional[int] = None) -> list:
        """获取需要补扫描的历史文档"""
        connection = self._get_db_connection()
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = """
                SELECT id, file_path, original_filename, file_type, file_size
                FROM documents
                WHERE (security_scan_status = 'pending' OR security_scan_status IS NULL)
                  AND (security_scan_method = 'none' OR security_scan_method IS NULL)
                  AND file_path IS NOT NULL
                  AND file_path != ''
                ORDER BY id ASC
            """
            if limit:
                sql += f" LIMIT {limit}"
            
            cursor.execute(sql)
            return cursor.fetchall()
    
    def download_file_from_minio(self, file_path: str) -> Optional[BytesIO]:
        """从 MinIO 下载文件"""
        try:
            file_data = self.minio_storage.download_file(file_path)
            if file_data:
                return BytesIO(file_data)
            return None
        except Exception as e:
            logger.error(f"下载文件失败 {file_path}: {e}")
            return None
    
    def scan_document(self, document: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """扫描单个文档"""
        doc_id = document['id']
        file_path = document['file_path']
        filename = document['original_filename']
        
        print(f"\n📄 扫描文档 ID={doc_id}: {filename}")
        
        # 1. 从 MinIO 下载文件
        print(f"   下载文件: {file_path}")
        file_data = self.download_file_from_minio(file_path)
        if not file_data:
            print(f"   ❌ 无法下载文件")
            return None
        
        # 2. 创建 UploadFile 对象用于验证
        from starlette.datastructures import UploadFile as StarletteUploadFile
        file_data.seek(0)
        content_type = self._guess_content_type(filename, document.get('file_type'))
        # 使用 starlette 的 UploadFile，可以设置 content_type
        upload_file = StarletteUploadFile(
            filename=filename,
            file=file_data,
            headers={"content-type": content_type}
        )
        
        # 3. 执行安全扫描
        try:
            print(f"   执行安全扫描...")
            validation_result = self.file_validation.validate_file(upload_file)
            security_scan = validation_result.get("security_scan", {})
            
            # 提取扫描结果
            scan_status = security_scan.get("scan_status", "pending")
            scan_method = security_scan.get("scan_method", "none")
            scan_result = {
                "virus_scan": security_scan.get("virus_scan"),
                "script_scan": security_scan.get("script_scan"),
                "threats_found": security_scan.get("threats_found", []),
                "scan_timestamp": datetime.utcnow().isoformat(),
                "is_historical_rescan": True
            }
            
            print(f"   ✅ 扫描完成: {scan_status} ({scan_method})")
            
            return {
                "security_scan_status": scan_status,
                "security_scan_method": scan_method,
                "security_scan_result": scan_result,
                "security_scan_timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"扫描文档 {doc_id} 失败: {e}")
            print(f"   ❌ 扫描失败: {e}")
            return None
        finally:
            file_data.close()
    
    def _guess_content_type(self, filename: str, file_type: Optional[str]) -> str:
        """根据文件名和类型猜测 MIME 类型"""
        ext = Path(filename).suffix.lower()
        mime_map = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.html': 'text/html',
            '.htm': 'text/html',
        }
        return mime_map.get(ext, 'application/octet-stream')
    
    def update_document_scan_result(self, doc_id: int, scan_result: Dict[str, Any]):
        """更新文档的扫描结果"""
        connection = self._get_db_connection()
        try:
            with connection.cursor() as cursor:
                sql = """
                    UPDATE documents
                    SET security_scan_status = %s,
                        security_scan_method = %s,
                        security_scan_result = %s,
                        security_scan_timestamp = %s
                    WHERE id = %s
                """
                cursor.execute(sql, (
                    scan_result['security_scan_status'],
                    scan_result['security_scan_method'],
                    json.dumps(scan_result['security_scan_result'], ensure_ascii=False),
                    scan_result['security_scan_timestamp'],
                    doc_id
                ))
                connection.commit()
                print(f"   ✅ 数据库已更新")
        except Exception as e:
            connection.rollback()
            logger.error(f"更新文档 {doc_id} 失败: {e}")
            print(f"   ❌ 更新失败: {e}")
    
    def rescan_historical_documents(self, limit: Optional[int] = None, dry_run: bool = False):
        """补扫描历史文档"""
        print("="*60)
        print("历史文档安全扫描补扫")
        print("="*60)
        
        # 获取历史文档列表
        print("\n📋 查询历史文档...")
        documents = self.get_historical_documents(limit)
        
        if not documents:
            print("✅ 没有需要补扫描的文档")
            return
        
        total = len(documents)
        print(f"📊 找到 {total} 个需要补扫描的文档\n")
        
        if dry_run:
            print("🔍 预览模式（不会实际更新数据库）\n")
        
        success_count = 0
        failed_count = 0
        
        for idx, doc in enumerate(documents, 1):
            print(f"\n[{idx}/{total}] 处理文档 ID={doc['id']}")
            
            # 扫描文档
            scan_result = self.scan_document(doc)
            
            if scan_result:
                if not dry_run:
                    # 更新数据库
                    self.update_document_scan_result(doc['id'], scan_result)
                else:
                    print(f"   [预览] 将更新为: {scan_result['security_scan_status']} ({scan_result['security_scan_method']})")
                success_count += 1
            else:
                failed_count += 1
        
        print("\n" + "="*60)
        print("补扫描完成")
        print("="*60)
        print(f"✅ 成功: {success_count}")
        print(f"❌ 失败: {failed_count}")
        print(f"📊 总计: {total}")
        
        self._close_db_connection()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='历史文档安全扫描补扫')
    parser.add_argument('--limit', type=int, help='限制扫描数量（用于测试）')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不实际更新数据库')
    parser.add_argument('--yes', '-y', action='store_true', help='自动确认，跳过交互式提示')
    
    args = parser.parse_args()
    
    if not args.yes:
        if args.dry_run:
            print("\n⚠️  警告：预览模式，不会实际更新数据库\n")
            response = input("是否继续？(yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("已取消操作")
                return
        else:
            print("\n⚠️  警告：此操作将更新数据库中的安全扫描信息")
            print("   如果这是您想要的操作，请继续。\n")
            response = input("是否继续？(yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("已取消操作")
                return
    
    scanner = HistoricalDocumentRescanner()
    try:
        scanner.rescan_historical_documents(limit=args.limit, dry_run=args.dry_run)
    except KeyboardInterrupt:
        print("\n\n⚠️  操作已中断")
        scanner._close_db_connection()
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        scanner._close_db_connection()

if __name__ == "__main__":
    main()
