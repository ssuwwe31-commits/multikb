"""
Content Validation Service
根据文档修改功能设计实现内容验证服务
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import re
import json
from app.core.logging import logger
from app.config.settings import settings
from app.core.exceptions import CustomException, ErrorCode

class ContentValidationService:
    """内容验证服务 - 严格按照文档修改功能设计实现"""
    
    def __init__(self, db: Session):
        self.db = db
        # 设计文档要求的验证规则
        self.MAX_CONTENT_LENGTH = 10000  # 最大内容长度
        self.MIN_CONTENT_LENGTH = 1      # 最小内容长度
        self.SUPPORTED_LANGUAGES = ['zh', 'en', 'zh-cn', 'en-us']  # 支持的语言
    
    def validate_content_format(self, content: str) -> Dict[str, Any]:
        """内容格式验证 - 根据设计文档实现"""
        try:
            logger.debug(f"开始内容格式验证，内容长度: {len(content)}")
            
            # 长度验证
            if len(content) < self.MIN_CONTENT_LENGTH:
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"内容长度不能少于 {self.MIN_CONTENT_LENGTH} 个字符"
                )
            
            if len(content) > self.MAX_CONTENT_LENGTH:
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"内容长度不能超过 {self.MAX_CONTENT_LENGTH} 个字符"
                )
            
            # 编码验证
            try:
                content.encode('utf-8')
            except UnicodeEncodeError:
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="内容包含无效的字符编码"
                )
            
            # 格式检查
            format_issues = []
            
            # 检查是否包含过多的空白字符
            if len(content.strip()) == 0:
                format_issues.append("内容不能只包含空白字符")
            
            # 检查是否包含过多的换行符
            if content.count('\n') > len(content) * settings.MAX_NEWLINE_RATIO:
                format_issues.append("内容包含过多的换行符")
            
            # 检查是否包含特殊字符
            special_chars = re.findall(r'[^\w\s\u4e00-\u9fff.,!?;:()\[\]{}"\'-]', content)
            if len(special_chars) > len(content) * settings.MAX_SPECIAL_CHAR_RATIO:
                format_issues.append("内容包含过多的特殊字符")
            
            return {
                "valid": len(format_issues) == 0,
                "message": "格式验证通过" if len(format_issues) == 0 else f"格式问题: {', '.join(format_issues)}",
                "content_length": len(content),
                "format_issues": format_issues
            }
            
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"内容格式验证错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"内容格式验证失败: {str(e)}"
            )
    
    def detect_content_language(self, content: str) -> str:
        """语言检测 - 根据设计文档实现"""
        try:
            logger.debug("开始语言检测")
            
            # 简单的语言检测逻辑
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
            english_chars = len(re.findall(r'[a-zA-Z]', content))
            total_chars = len(re.sub(r'[^\w\u4e00-\u9fff]', '', content))
            
            if total_chars == 0:
                return 'unknown'
            
            chinese_ratio = chinese_chars / total_chars
            english_ratio = english_chars / total_chars
            
            if chinese_ratio > settings.MIN_CHINESE_RATIO:
                return 'zh'
            elif english_ratio > settings.MIN_ENGLISH_RATIO:
                return 'en'
            else:
                return 'mixed'
                
        except Exception as e:
            logger.error(f"语言检测错误: {e}", exc_info=True)
            return 'unknown'
    
    def extract_keywords(self, content: str, language: str = 'zh') -> List[str]:
        """关键词提取 - 根据设计文档实现"""
        try:
            logger.debug(f"开始关键词提取，语言: {language}")
            
            # 简单的关键词提取逻辑
            keywords = []
            
            if language == 'zh':
                # 中文关键词提取
                # 提取2-4字的中文词汇
                chinese_words = re.findall(r'[\u4e00-\u9fff]{2,4}', content)
                # 统计词频
                word_freq = {}
                for word in chinese_words:
                    word_freq[word] = word_freq.get(word, 0) + 1
                
                # 取出现频率最高的前10个词
                keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
                keywords = [word for word, freq in keywords if freq > 1]
                
            elif language == 'en':
                # 英文关键词提取
                # 提取2-10个字母的英文单词
                english_words = re.findall(r'\b[a-zA-Z]{2,10}\b', content.lower())
                # 过滤常见停用词
                stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
                english_words = [word for word in english_words if word not in stop_words]
                
                # 统计词频
                word_freq = {}
                for word in english_words:
                    word_freq[word] = word_freq.get(word, 0) + 1
                
                # 取出现频率最高的前10个词
                keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
                keywords = [word for word, freq in keywords if freq > 1]
            
            logger.debug(f"关键词提取完成，提取到 {len(keywords)} 个关键词")
            return keywords
            
        except Exception as e:
            logger.error(f"关键词提取错误: {e}", exc_info=True)
            return []
    
    def extract_entities(self, content: str, language: str = 'zh') -> Dict[str, List[str]]:
        """实体识别 - 根据设计文档实现"""
        try:
            logger.debug(f"开始实体识别，语言: {language}")
            
            entities = {
                'persons': [],
                'locations': [],
                'organizations': [],
                'dates': [],
                'numbers': []
            }
            
            if language == 'zh':
                # 中文实体识别
                # 人名识别（简单规则）
                person_patterns = [
                    r'[\u4e00-\u9fff]{2,4}(?:先生|女士|老师|教授|博士|主任|经理|总监)',
                    r'(?:王|李|张|刘|陈|杨|赵|黄|周|吴|徐|孙|胡|朱|高|林|何|郭|马|罗|梁|宋|郑|谢|韩|唐|冯|于|董|萧|程|曹|袁|邓|许|傅|沈|曾|彭|吕|苏|卢|蒋|蔡|贾|丁|魏|薛|叶|阎|余|潘|杜|戴|夏|钟|汪|田|任|姜|范|方|石|姚|谭|廖|邹|熊|金|陆|郝|孔|白|崔|康|毛|邱|秦|江|史|顾|侯|邵|孟|龙|万|段|漕|钱|汤|尹|黎|易|常|武|乔|贺|赖|龚|文)',
                ]
                
                for pattern in person_patterns:
                    matches = re.findall(pattern, content)
                    entities['persons'].extend(matches)
                
                # 地名识别（简单规则）
                location_patterns = [
                    r'[\u4e00-\u9fff]{2,4}(?:市|县|区|省|州|国|城|镇|村|路|街|巷)',
                    r'(?:北京|上海|广州|深圳|杭州|南京|武汉|成都|西安|重庆|天津|青岛|大连|宁波|厦门|苏州|无锡|长沙|郑州|济南|福州|合肥|石家庄|太原|沈阳|长春|哈尔滨|呼和浩特|乌鲁木齐|银川|西宁|兰州|拉萨|昆明|贵阳|南宁|海口|三亚)',
                ]
                
                for pattern in location_patterns:
                    matches = re.findall(pattern, content)
                    entities['locations'].extend(matches)
                
                # 机构名识别（简单规则）
                org_patterns = [
                    r'[\u4e00-\u9fff]{2,8}(?:公司|集团|企业|银行|医院|学校|大学|学院|研究所|中心|局|部|委|办|处|科)',
                ]
                
                for pattern in org_patterns:
                    matches = re.findall(pattern, content)
                    entities['organizations'].extend(matches)
            
            elif language == 'en':
                # 英文实体识别（简单规则）
                # 人名识别
                person_patterns = [
                    r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # First Last
                    r'\b(?:Mr|Mrs|Ms|Dr|Prof)\. [A-Z][a-z]+\b',  # Title Name
                ]
                
                for pattern in person_patterns:
                    matches = re.findall(pattern, content)
                    entities['persons'].extend(matches)
                
                # 地名识别
                location_patterns = [
                    r'\b[A-Z][a-z]+ (?:City|Town|State|Country|Province)\b',
                    r'\b(?:New York|Los Angeles|Chicago|Houston|Phoenix|Philadelphia|San Antonio|San Diego|Dallas|San Jose)\b',
                ]
                
                for pattern in location_patterns:
                    matches = re.findall(pattern, content)
                    entities['locations'].extend(matches)
            
            # 日期识别（通用）
            date_patterns = [
                r'\d{4}年\d{1,2}月\d{1,2}日',  # 中文日期
                r'\d{1,2}/\d{1,2}/\d{4}',      # 英文日期
                r'\d{4}-\d{1,2}-\d{1,2}',      # ISO日期
            ]
            
            for pattern in date_patterns:
                matches = re.findall(pattern, content)
                entities['dates'].extend(matches)
            
            # 数字识别
            number_patterns = [
                r'\d+\.?\d*',  # 整数和小数
                r'\d{1,3}(?:,\d{3})*',  # 千分位数字
            ]
            
            for pattern in number_patterns:
                matches = re.findall(pattern, content)
                entities['numbers'].extend(matches)
            
            # 去重
            for key in entities:
                entities[key] = list(set(entities[key]))
            
            logger.debug(f"实体识别完成，识别到 {sum(len(v) for v in entities.values())} 个实体")
            return entities
            
        except Exception as e:
            logger.error(f"实体识别错误: {e}", exc_info=True)
            return {'persons': [], 'locations': [], 'organizations': [], 'dates': [], 'numbers': []}
    
    def validate_content(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """完整内容验证 - 根据设计文档实现所有验证步骤"""
        try:
            logger.info(f"开始完整内容验证，内容长度: {len(content)}")
            
            # 1. 格式验证
            format_result = self.validate_content_format(content)
            
            if not format_result["valid"]:
                return {
                    "valid": False,
                    "message": format_result["message"],
                    "validation_results": {
                        "format_validation": format_result,
                        "language_detection": {"language": "unknown"},
                        "keyword_extraction": {"keywords": []},
                        "entity_recognition": {"entities": {}}
                    }
                }
            
            # 2. 语言检测
            detected_language = self.detect_content_language(content)
            
            # 3. 关键词提取
            keywords = self.extract_keywords(content, detected_language)
            
            # 4. 实体识别
            entities = self.extract_entities(content, detected_language)
            
            # 综合结果
            result = {
                "valid": True,
                "message": "内容验证通过",
                "validation_results": {
                    "format_validation": format_result,
                    "language_detection": {
                        "language": detected_language,
                        "confidence": 0.8  # 简单的置信度
                    },
                    "keyword_extraction": {
                        "keywords": keywords,
                        "keyword_count": len(keywords)
                    },
                    "entity_recognition": {
                        "entities": entities,
                        "total_entities": sum(len(v) for v in entities.values())
                    }
                },
                "validation_timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            logger.info(f"内容验证完成: {content[:50]}...")
            return result
            
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"内容验证错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"内容验证失败: {str(e)}"
            )
