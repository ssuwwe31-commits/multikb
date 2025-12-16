"""
ClamAV Service
反病毒扫描服务 - 根据设计文档实现
"""

import warnings
# 抑制 clamd 的 pkg_resources 弃用警告
warnings.filterwarnings("ignore", message="pkg_resources is deprecated")

import clamd
import subprocess
import platform
from pathlib import Path
from app.core.logging import logger
from app.core.exceptions import CustomException, ErrorCode


class ClamAVService:
    """
    ClamAV反病毒扫描服务
    
    支持方式:
    - Ubuntu/Linux: Unix Socket (/var/run/clamav/clamd.ctl)
    - Windows: Named Pipe (\\.\pipe\clamd)
    - 远程TCP: TCP Socket (host:port)
    - 本地TCP: localhost:3310
    """
    
    def __init__(self, socket_path=None, tcp_host=None, tcp_port=None):
        """
        初始化ClamAV服务
        
        参数:
        - socket_path: Socket路径（Unix Socket或Named Pipe）
        - tcp_host: TCP主机地址（如果使用远程ClamAV）
        - tcp_port: TCP端口（默认3310）
        """
        from app.config.settings import settings
        
        # 如果明确配置使用TCP，强制使用TCP方式，忽略socket_path
        if settings.CLAMAV_USE_TCP:
            self.socket_path = None
        else:
            self.socket_path = socket_path or settings.CLAMAV_SOCKET_PATH or self._get_socket_path()
        
        self.tcp_host = tcp_host or settings.CLAMAV_TCP_HOST
        self.tcp_port = tcp_port or settings.CLAMAV_TCP_PORT
        self.client = None
        self._connect()
    
    def _get_socket_path(self):
        """根据操作系统获取默认Socket路径"""
        system = platform.system()
        
        if system == "Linux":
            # Ubuntu/Unix - Unix Socket
            return "/var/run/clamav/clamd.ctl"
        elif system == "Windows":
            # Windows 不支持 AF_UNIX，优先使用 TCP 方式连接 clamd（默认 localhost:3310）
            return None
        else:
            # macOS或其他系统，使用默认路径
            return None
    
    def _connect(self):
        """连接到ClamAV守护进程"""
        try:
            from app.config.settings import settings
            
            # 如果ClamAV被禁用，跳过连接
            if not settings.CLAMAV_ENABLED:
                logger.info("ClamAV已禁用，跳过连接")
                self.client = None
                return
            
            # 连接优先级：
            # 1. 如果 CLAMAV_USE_TCP=true，强制使用TCP
            # 2. 如果 socket_path 不为空，使用Unix Socket或Named Pipe
            # 3. 否则使用TCP Socket（可以是远程）
            
            if settings.CLAMAV_USE_TCP or not self.socket_path:
                # 使用TCP Socket（可以是远程）
                self.client = clamd.ClamdNetworkSocket(self.tcp_host, self.tcp_port)
                logger.info(f"尝试连接ClamAV TCP: {self.tcp_host}:{self.tcp_port}")
            else:
                # 使用Unix Socket或Named Pipe
                self.client = clamd.ClamdUnixSocket(self.socket_path)
                logger.info(f"尝试连接ClamAV Socket: {self.socket_path}")
            
            # 测试连接
            response = self.client.ping()
            if response != 'PONG':
                raise Exception("ClamAV连接失败")
            
            logger.info("✅ ClamAV服务连接成功")
            
        except Exception as e:
            logger.warning(f"⚠️ ClamAV服务连接失败: {e}")
            logger.info("系统将在不进行病毒扫描的情况下继续运行")
            self.client = None
    
    def scan_file(self, file_path: str) -> dict:
        """
        扫描文件 - 使用clamd守护进程
        
        参数:
        - file_path: 文件路径
        
        返回:
        {
            'status': 'safe' | 'infected' | 'error' | 'warning',
            'message': str,
            'threats': list,
            'skip_scan': bool
        }
        """
        try:
            if not self.client:
                logger.warning("ClamAV未连接，跳过病毒扫描")
                return {
                    'status': 'warning',
                    'message': 'ClamAV服务未连接，跳过病毒扫描',
                    'threats': [],
                    'skip_scan': True
                }
            
            logger.info(f"开始病毒扫描: {file_path}")
            
            # 使用clamd扫描
            result = self.client.scan(file_path)
            
            # 解析结果
            # result格式: {'/path/to/file': ('OK', '')} 或 {'/path/to/file': ('FOUND', 'Trojan.Foo')}
            status = result.get(file_path)
            
            if status is None:
                logger.error(f"无法获取扫描结果: {file_path}")
                return {
                    'status': 'error',
                    'message': '无法获取扫描结果',
                    'threats': []
                }
            
            scan_status, threat_name = status
            
            if scan_status == 'OK':
                logger.info(f"✅ 文件安全: {file_path}")
                return {
                    'status': 'safe',
                    'message': '文件安全，未发现威胁',
                    'threats': []
                }
            elif scan_status == 'FOUND':
                logger.warning(f"⚠️ 发现威胁: {file_path}, 威胁类型: {threat_name}")
                return {
                    'status': 'infected',
                    'message': f'发现威胁: {threat_name}',
                    'threats': [threat_name]
                }
            else:
                logger.error(f"❌ 扫描异常: {file_path}, 状态: {scan_status}")
                return {
                    'status': 'error',
                    'message': f'扫描异常: {scan_status}',
                    'threats': []
                }
                
        except Exception as e:
            logger.error(f"病毒扫描错误: {e}", exc_info=True)
            # 不抛出异常，允许服务继续运行
            return {
                'status': 'error',
                'message': f'扫描错误: {str(e)}',
                'threats': []
            }
    
    def scan_stream(self, file_data: bytes) -> dict:
        """
        扫描文件流（内存扫描）
        
        参数:
        - file_data: 文件字节数据
        
        返回:
        {
            'status': 'safe' | 'infected' | 'error' | 'warning',
            'message': str,
            'threats': list
        }
        """
        try:
            if not self.client:
                return {
                    'status': 'warning',
                    'message': 'ClamAV服务未连接，跳过病毒扫描',
                    'threats': [],
                    'skip_scan': True
                }
            
            logger.info(f"开始流式病毒扫描，数据大小: {len(file_data)} bytes")
            
            # 使用clamd进行流式扫描
            # 注意：instream通常有限制（如25MB），超出限制可能返回错误
            if len(file_data) > 25 * 1024 * 1024:  # 25MB限制
                logger.warning("文件超过流式扫描限制，改用文件扫描")
                return self._scan_large_file(file_data)
            
            # clamd.instream 需要一个带 read() 的类文件对象
            import io
            buffer = io.BytesIO(file_data)
            result = self.client.instream(buffer)
            
            # result格式: {'stream': ('OK', '')} 或 {'stream': ('FOUND', 'Trojan.Foo')}
            stream_status = result.get('stream')
            
            if stream_status is None:
                logger.error("无法获取流式扫描结果")
                return {
                    'status': 'error',
                    'message': '无法获取流式扫描结果',
                    'threats': []
                }
            
            scan_status, threat_name = stream_status
            
            if scan_status == 'OK':
                logger.info("✅ 流式扫描通过")
                return {
                    'status': 'safe',
                    'message': '文件安全，未发现威胁',
                    'threats': []
                }
            elif scan_status == 'FOUND':
                logger.warning(f"⚠️ 发现威胁: {threat_name}")
                return {
                    'status': 'infected',
                    'message': f'发现威胁: {threat_name}',
                    'threats': [threat_name]
                }
            else:
                logger.error(f"❌ 流式扫描异常: {scan_status}")
                return {
                    'status': 'error',
                    'message': f'扫描异常: {scan_status}',
                    'threats': []
                }
                
        except Exception as e:
            logger.error(f"流式扫描错误: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e),
                'threats': []
            }
    
    def _scan_large_file(self, file_data: bytes) -> dict:
        """
        扫描大文件（超过流式扫描限制）
        临时保存到文件后扫描
        """
        import tempfile
        import os
        
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_path = tmp_file.name
                tmp_file.write(file_data)
            
            result = self.scan_file(tmp_path)
            
            # 清理临时文件
            os.unlink(tmp_path)
            
            return result
            
        except Exception as e:
            logger.error(f"大文件扫描错误: {e}")
            return {
                'status': 'error',
                'message': f'大文件扫描失败: {str(e)}',
                'threats': []
            }
    
    def update_database(self):
        """更新病毒库"""
        try:
            logger.info("开始更新ClamAV病毒库")
            
            if platform.system() == "Windows":
                # Windows使用freshclam.exe
                result = subprocess.run(
                    ['freshclam.exe'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
            else:
                # Linux使用freshclam
                result = subprocess.run(
                    ['sudo', 'freshclam'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
            
            if result.returncode == 0:
                logger.info("✅ 病毒库更新完成")
            else:
                logger.warning(f"病毒库更新警告: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error("病毒库更新超时")
        except subprocess.CalledProcessError as e:
            logger.error(f"病毒库更新失败: {e}")
        except Exception as e:
            logger.error(f"病毒库更新错误: {e}")
    
    def is_available(self) -> bool:
        """检查ClamAV服务是否可用"""
        return self.client is not None
    
    def get_service_info(self) -> dict:
        """获取服务信息"""
        try:
            if not self.client:
                return {
                    'available': False,
                    'message': 'ClamAV服务未连接'
                }
            
            # 获取版本信息
            version_info = self.client.version()
            
            return {
                'available': True,
                'version': version_info,
                'socket': self.socket_path,
                'platform': platform.system()
            }
        except Exception as e:
            logger.error(f"获取服务信息错误: {e}")
            return {
                'available': False,
                'message': str(e)
            }
