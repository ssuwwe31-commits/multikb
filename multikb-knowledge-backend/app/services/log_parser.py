"""
日志解析器
从日志消息中提取代码标识符（函数名、类名、文件名、行号等）
"""

import re
import os
from typing import Dict, List, Optional, Any
from app.core.logging import logger


class LogParser:
    """日志解析器"""
    
    # Python 日志格式模式
    PYTHON_LOGGING_PATTERNS = [
        # 标准格式: 2026-01-19 10:30:45,123 - module.name - LEVEL - message
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[,\d]*)\s+-\s+([\w.]+)\s+-\s+(\w+)\s+-\s+(.+)',
        # 文件路径和行号: File "/path/to/file.py", line 42
        r'File\s+"([^"]+)",\s+line\s+(\d+)',
    ]
    
    # Python 异常堆栈模式
    PYTHON_TRACEBACK_PATTERNS = [
        # Traceback 中的文件路径和行号
        r'File\s+"([^"]+)",\s+line\s+(\d+),\s+in\s+(\w+)',
        # 异常类型和消息
        r'(\w+Error|\w+Exception):\s+(.+)',
    ]
    
    # Java 日志格式模式
    JAVA_LOGGING_PATTERNS = [
        # log4j 格式: 2026-01-19 10:30:45.123 LEVEL [thread] package.Class - message
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+(\w+)\s+\[([^\]]+)\]\s+([\w.]+)\s+-\s+(.+)',
        # 堆栈跟踪: at package.Class.method(Class.java:42)
        r'at\s+([\w.]+)\.(\w+)\(([\w.]+\.java):(\d+)\)',
    ]
    
    # Node.js 日志格式模式
    NODEJS_LOGGING_PATTERNS = [
        # winston 格式: 2026-01-19T10:30:45.123Z level Service: message
        r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\s+(\w+)\s+(\w+):\s+(.+)',
        # 堆栈跟踪: at Service.method (/path/to/file.js:42:15)
        r'at\s+(\w+)\.(\w+)\s+\(([^:]+):(\d+):(\d+)\)',
    ]
    
    def parse_log_message(self, log_message: str) -> Dict[str, Any]:
        """
        解析日志消息，提取代码标识符
        
        Args:
            log_message: 日志消息文本
            
        Returns:
            解析结果:
            {
                'file_paths': ['app/services/user_service.py'],
                'line_numbers': [42],
                'function_names': ['get_user'],
                'class_names': ['UserService'],
                'module_names': ['app.services.user_service'],
                'error_types': ['UserNotFoundError'],
                'log_level': 'ERROR',
                'message': 'User not found: user_id=123'
            }
        """
        result = {
            'file_paths': [],
            'line_numbers': [],
            'column_numbers': [],  # 新增：列号
            'function_names': [],
            'class_names': [],
            'module_names': [],
            'error_types': [],
            'log_level': None,
            'message': log_message
        }
        
        if not log_message or not log_message.strip():
            return result
        
        # 尝试识别日志格式
        if self._is_python_logging(log_message):
            parsed = self._parse_python_logging(log_message)
            result.update(parsed)
        elif self._is_java_logging(log_message):
            parsed = self._parse_java_logging(log_message)
            result.update(parsed)
        elif self._is_nodejs_logging(log_message):
            parsed = self._parse_nodejs_logging(log_message)
            result.update(parsed)
        else:
            # 通用解析：尝试提取文件名、函数名等
            parsed = self._parse_generic(log_message)
            result.update(parsed)
        
        # 去重
        result['file_paths'] = list(set(result['file_paths']))
        result['line_numbers'] = list(set(result['line_numbers']))
        result['column_numbers'] = list(set(result['column_numbers']))
        result['function_names'] = list(set(result['function_names']))
        result['class_names'] = list(set(result['class_names']))
        result['module_names'] = list(set(result['module_names']))
        result['error_types'] = list(set(result['error_types']))
        
        logger.debug(f"日志解析结果: {result}")
        return result
    
    def _is_python_logging(self, log_message: str) -> bool:
        """判断是否为 Python logging 格式"""
        return bool(re.search(r'File\s+"[^"]+",\s+line\s+\d+', log_message)) or \
               bool(re.search(r'Traceback\s+\(most recent call last\)', log_message, re.IGNORECASE))
    
    def _is_java_logging(self, log_message: str) -> bool:
        """判断是否为 Java logging 格式"""
        return bool(re.search(r'at\s+[\w.]+\.[\w.]+\([\w.]+\.java:\d+\)', log_message))
    
    def _is_nodejs_logging(self, log_message: str) -> bool:
        """判断是否为 Node.js logging 格式"""
        return bool(re.search(r'at\s+\w+\.\w+\s+\([^:]+:\d+:\d+\)', log_message))
    
    def _parse_python_logging(self, log_message: str) -> Dict:
        """解析 Python logging 格式"""
        result = {
            'file_paths': [],
            'line_numbers': [],
            'function_names': [],
            'class_names': [],
            'module_names': [],
            'error_types': [],
            'log_level': None
        }
        
        # 提取文件路径和行号（支持列号）
        # 模式1: File "...", line 42, in function
        file_pattern1 = r'File\s+"([^"]+)",\s+line\s+(\d+)(?:,\s+in\s+(\w+))?'
        for match in re.finditer(file_pattern1, log_message):
            file_path = match.group(1)
            line_num = int(match.group(2))
            func_name = match.group(3)
            
            result['file_paths'].append(file_path)
            result['line_numbers'].append(line_num)
            if func_name:
                result['function_names'].append(func_name)
        
        # 模式2: File "...", line 42, column 50
        file_pattern2 = r'File\s+"([^"]+)",\s+line\s+(\d+)(?:,\s+column\s+(\d+))?'
        for match in re.finditer(file_pattern2, log_message):
            file_path = match.group(1)
            line_num = int(match.group(2))
            column_num = match.group(3)
            
            if file_path not in result['file_paths']:
                result['file_paths'].append(file_path)
            if line_num not in result['line_numbers']:
                result['line_numbers'].append(line_num)
            if column_num:
                result['column_numbers'].append(int(column_num))
        
        # 模式3: 从错误消息中提取列号（如 "NameError at line 42, column 50"）
        column_pattern = r'(?:at|line)\s+(\d+)(?:,\s+column\s+(\d+))?'
        for match in re.finditer(column_pattern, log_message, re.IGNORECASE):
            column_num = match.group(2)
            if column_num:
                result['column_numbers'].append(int(column_num))
        
        # 从文件路径提取模块名
        for file_path in result['file_paths']:
            if file_path.endswith('.py'):
                # 移除绝对路径前缀，转换为模块路径
                module_name = file_path.replace('/', '.').replace('\\', '.').replace('.py', '')
                # 移除常见的路径前缀
                if 'site-packages' in module_name:
                    continue  # 跳过第三方库
                result['module_names'].append(module_name)
        
        # 提取异常类型
        error_pattern = r'(\w+Error|\w+Exception):'
        for match in re.finditer(error_pattern, log_message):
            result['error_types'].append(match.group(1))
        
        # 提取日志级别
        level_pattern = r'-\s+(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s+-'
        match = re.search(level_pattern, log_message)
        if match:
            result['log_level'] = match.group(1)
        
        # 从模块名提取类名（假设格式为 module.ClassName）
        for module_name in result['module_names']:
            parts = module_name.split('.')
            if len(parts) > 0:
                # 最后一个部分可能是类名
                potential_class = parts[-1]
                if potential_class and potential_class[0].isupper():
                    result['class_names'].append(potential_class)
        
        return result
    
    def _parse_java_logging(self, log_message: str) -> Dict:
        """解析 Java logging 格式"""
        result = {
            'file_paths': [],
            'line_numbers': [],
            'column_numbers': [],
            'function_names': [],
            'class_names': [],
            'module_names': [],
            'error_types': [],
            'log_level': None
        }
        
        # 提取类名和方法名
        stack_pattern = r'at\s+([\w.]+)\.(\w+)\(([\w.]+\.java):(\d+)\)'
        for match in re.finditer(stack_pattern, log_message):
            full_class = match.group(1)
            method_name = match.group(2)
            file_name = match.group(3)
            line_num = int(match.group(4))
            
            result['function_names'].append(method_name)
            result['file_paths'].append(file_name)
            result['line_numbers'].append(line_num)
            
            # 提取类名
            class_name = full_class.split('.')[-1]
            result['class_names'].append(class_name)
            result['module_names'].append(full_class)
        
        # 提取日志级别
        level_pattern = r'(\w+)\s+\[[^\]]+\]\s+[\w.]+\s+-'
        match = re.search(level_pattern, log_message)
        if match:
            level = match.group(1).upper()
            if level in ['DEBUG', 'INFO', 'WARN', 'WARNING', 'ERROR', 'FATAL']:
                result['log_level'] = level
        
        return result
    
    def _parse_nodejs_logging(self, log_message: str) -> Dict:
        """解析 Node.js logging 格式"""
        result = {
            'file_paths': [],
            'line_numbers': [],
            'column_numbers': [],
            'function_names': [],
            'class_names': [],
            'module_names': [],
            'error_types': [],
            'log_level': None
        }
        
        # 提取服务名和方法名
        stack_pattern = r'at\s+(\w+)\.(\w+)\s+\(([^:]+):(\d+):(\d+)\)'
        for match in re.finditer(stack_pattern, log_message):
            service_name = match.group(1)
            method_name = match.group(2)
            file_path = match.group(3)
            line_num = int(match.group(4))
            
            result['function_names'].append(method_name)
            result['file_paths'].append(file_path)
            result['line_numbers'].append(line_num)
            result['class_names'].append(service_name)
        
        # 提取日志级别
        level_pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\s+(\w+)\s+'
        match = re.search(level_pattern, log_message)
        if match:
            level = match.group(2).upper()
            if level in ['DEBUG', 'INFO', 'WARN', 'WARNING', 'ERROR', 'FATAL']:
                result['log_level'] = level
        
        return result
    
    def _parse_generic(self, log_message: str) -> Dict:
        """通用解析：尝试提取可能的代码标识符"""
        result = {
            'file_paths': [],
            'line_numbers': [],
            'column_numbers': [],
            'function_names': [],
            'class_names': [],
            'module_names': [],
            'error_types': [],
            'log_level': None
        }
        
        # 提取可能的文件路径（.py, .java, .js, .ts, .go, .rs, .cpp, .h 等）
        file_pattern = r'([\w/\\]+\.(py|java|js|ts|go|rs|cpp|h|hpp|cc|cxx))'
        for match in re.finditer(file_pattern, log_message):
            file_path = match.group(1)
            # 过滤掉明显的非代码文件路径
            if not any(skip in file_path.lower() for skip in ['node_modules', '__pycache__', '.git']):
                result['file_paths'].append(file_path)
        
        # 提取可能的行号（:42 或 line 42）
        line_pattern = r'(?:line\s+|:)(\d+)'
        for match in re.finditer(line_pattern, log_message):
            line_num = int(match.group(1))
            # 过滤掉明显不是行号的数字（如端口号、年份等）
            if 1 <= line_num <= 100000:  # 合理的行号范围
                result['line_numbers'].append(line_num)
        
        # 提取可能的函数名（驼峰命名或下划线命名）
        func_pattern = r'\b([a-z][a-z0-9_]*|_[a-z][a-z0-9_]*)\s*\(|def\s+([a-z][a-z0-9_]*)'
        for match in re.finditer(func_pattern, log_message):
            func_name = match.group(1) or match.group(2)
            if func_name and len(func_name) > 1:
                result['function_names'].append(func_name)
        
        # 提取可能的类名（首字母大写）
        class_pattern = r'\b([A-Z][a-zA-Z0-9_]*)\b'
        for match in re.finditer(class_pattern, log_message):
            class_name = match.group(1)
            # 排除常见的非类名（如 ERROR, INFO 等）
            if class_name not in ['ERROR', 'INFO', 'WARNING', 'DEBUG', 'CRITICAL', 'FATAL', 
                                  'WARN', 'TRACE', 'ALL', 'OFF', 'True', 'False', 'None']:
                result['class_names'].append(class_name)
        
        # 提取可能的异常类型
        error_pattern = r'\b(\w+Error|\w+Exception|\w+Warning)\b'
        for match in re.finditer(error_pattern, log_message):
            error_type = match.group(1)
            if error_type not in result['error_types']:
                result['error_types'].append(error_type)
        
        return result
