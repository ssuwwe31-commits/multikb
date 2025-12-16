/**
 * 内容验证工具
 */

interface ValidationResult {
  valid: boolean
  errors: string[]
  warnings: string[]
}

/**
 * 验证块内容
 */
export const validateChunkContent = (content: string): ValidationResult => {
  const errors: string[] = []
  const warnings: string[] = []

  // 1. 长度验证
  const maxLength = 100000 // 100KB
  if (content.length > maxLength) {
    errors.push(`内容长度超过限制（${maxLength}字符）`)
  }

  // 2. 空内容验证
  if (!content || content.trim().length === 0) {
    errors.push('内容不能为空')
    return { valid: false, errors, warnings }
  }

  // 3. 格式验证
  // 检查换行符比例
  const newlineRatio = content.split('\n').length / content.length
  if (newlineRatio > 0.5) {
    warnings.push('换行符过多，可能影响阅读体验')
  }

  // 4. 特殊字符验证
  const specialCharRegex = /[^\w\s\u4e00-\u9fa5，。！？；：""''（）【】、]/g
  const specialChars = content.match(specialCharRegex)
  if (specialChars && specialChars.length > content.length * 0.1) {
    warnings.push('特殊字符过多')
  }

  // 5. 语言检测
  const chineseRegex = /[\u4e00-\u9fa5]/g
  const chineseChars = content.match(chineseRegex)?.length || 0
  const chineseRatio = chineseChars / content.length

  const englishRegex = /[a-zA-Z]/g
  const englishChars = content.match(englishRegex)?.length || 0
  const englishRatio = englishChars / content.length

  if (chineseRatio < 0.3 && englishRatio < 0.3) {
    warnings.push('内容可能包含过多非语言文字')
  }

  // 6. 敏感词检测（简单版本）
  const sensitiveWords = ['敏感词1', '敏感词2']
  const hasSensitiveWord = sensitiveWords.some(word => content.includes(word))
  if (hasSensitiveWord) {
    warnings.push('内容可能包含敏感词')
  }

  // 7. HTML标签验证（如果使用富文本编辑器）
  const htmlTagRegex = /<[^>]*>/g
  const htmlTags = content.match(htmlTagRegex)
  if (htmlTags) {
    // 验证HTML标签的嵌套是否正确
    const openTags: string[] = []
    let isValidHTML = true

    htmlTags.forEach(tag => {
      const tagName = tag.match(/<\/?(\w+)/)?.[1]
      if (tag.startsWith('</')) {
        // 闭合标签
        const lastTag = openTags.pop()
        if (lastTag !== tagName) {
          isValidHTML = false
        }
      } else {
        // 开放标签
        openTags.push(tagName || '')
      }
    })

    if (!isValidHTML || openTags.length > 0) {
      warnings.push('HTML标签可能不完整')
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings
  }
}

/**
 * 验证内容长度
 */
export const validateLength = (content: string, min: number = 10, max: number = 100000) => {
  if (content.length < min) {
    return { valid: false, error: `内容长度不能少于${min}字符` }
  }
  if (content.length > max) {
    return { valid: false, error: `内容长度不能超过${max}字符` }
  }
  return { valid: true }
}

/**
 * 验证内容格式
 */
export const validateFormat = (content: string) => {
  // 检查是否为纯空白字符
  if (!content.trim()) {
    return { valid: false, error: '内容不能只包含空白字符' }
  }

  // 检查是否包含有效字符
  const hasValidChar = /[\w\u4e00-\u9fa5]/.test(content)
  if (!hasValidChar) {
    return { valid: false, error: '内容不包含有效字符' }
  }

  return { valid: true }
}

/**
 * 检测内容语言
 */
export const detectLanguage = (content: string): { language: string; confidence: number } => {
  const chineseRegex = /[\u4e00-\u9fa5]/g
  const englishRegex = /[a-zA-Z]/g

  const chineseChars = content.match(chineseRegex)?.length || 0
  const englishChars = content.match(englishRegex)?.length || 0
  const totalChars = chineseChars + englishChars

  if (totalChars === 0) {
    return { language: 'unknown', confidence: 0 }
  }

  const chineseRatio = chineseChars / totalChars
  const englishRatio = englishChars / totalChars

  if (chineseRatio > 0.5) {
    return { language: 'chinese', confidence: chineseRatio }
  } else if (englishRatio > 0.5) {
    return { language: 'english', confidence: englishRatio }
  } else {
    return { language: 'mixed', confidence: Math.max(chineseRatio, englishRatio) }
  }
}

/**
 * 提取内容关键词
 */
export const extractKeywords = (content: string, limit: number = 10): string[] => {
  // 简单关键词提取
  // 去掉HTML标签
  const text = content.replace(/<[^>]*>/g, '')
  
  // 中文分词（简单实现）
  const chineseWords = text.match(/[\u4e00-\u9fa5]{2,}/g) || []
  
  // 英文单词
  const englishWords = text.match(/[a-zA-Z]{3,}/g) || []
  
  // 合并并统计频率
  const wordMap = new Map<string, number>()
  
  chineseWords.forEach(word => {
    wordMap.set(word, (wordMap.get(word) || 0) + 1)
  })
  
  englishWords.forEach(word => {
    wordMap.set(word.toLowerCase(), (wordMap.get(word.toLowerCase()) || 0) + 1)
  })
  
  // 排序并返回top关键词
  return Array.from(wordMap.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([word]) => word)
}

/**
 * 验证完整性
 */
export const validateIntegrity = (content: string) => {
  const issues: string[] = []

  // 检查是否有未闭合的HTML标签
  const openTags = content.match(/<(\w+)[^>]*>/g) || []
  const closeTags = content.match(/<\/(\w+)>/g) || []
  
  if (openTags.length !== closeTags.length) {
    issues.push('HTML标签未正确闭合')
  }

  // 检查是否有特殊字符可能导致解析问题
  const problematicChars = ['\x00', '\x08', '\x0B', '\x0C', '\x1F']
  if (problematicChars.some(char => content.includes(char))) {
    issues.push('内容包含特殊控制字符')
  }

  return {
    valid: issues.length === 0,
    issues
  }
}
