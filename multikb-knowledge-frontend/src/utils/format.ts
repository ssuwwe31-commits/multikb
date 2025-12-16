/**
 * 格式化文件大小
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

/**
 * 格式化日期时间
 */
export const formatDateTime = (
  date: string | number | Date | null | undefined,
  format: string = 'YYYY-MM-DD HH:mm:ss'
): string => {
  if (!date) return '-'
  let input: Date

  try {
    // 字符串处理：兼容 "YYYY-MM-DD HH:mm:ss" / ISO / 带毫秒
    if (typeof date === 'string') {
      let s = date.trim()
      if (!s) return '-'
      // 若包含空格而不含 T，则替换为空格为 T，避免 new Date 无法解析
      if (s.includes(' ') && !s.includes('T')) {
        s = s.replace(' ', 'T')
      }
      // 如果没有时区信息，按本地时间处理
      input = new Date(s)
    } else if (typeof date === 'number') {
      input = new Date(date)
    } else {
      input = new Date(date)
    }
  } catch {
    return '-'
  }

  if (isNaN(input.getTime())) return '-'

  const year = input.getFullYear()
  const month = String(input.getMonth() + 1).padStart(2, '0')
  const day = String(input.getDate()).padStart(2, '0')
  const hours = String(input.getHours()).padStart(2, '0')
  const minutes = String(input.getMinutes()).padStart(2, '0')
  const seconds = String(input.getSeconds()).padStart(2, '0')

  return format
    .replace('YYYY', String(year))
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hours)
    .replace('mm', minutes)
    .replace('ss', seconds)
}

/**
 * 格式化数字
 */
export const formatNumber = (num: number): string => {
  return num.toLocaleString()
}

/**
 * 截断文本
 */
export const truncateText = (text: string, length: number, suffix: string = '...'): string => {
  if (text.length <= length) return text
  return text.substring(0, length) + suffix
}
