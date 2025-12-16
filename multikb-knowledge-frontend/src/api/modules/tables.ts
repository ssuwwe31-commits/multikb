import request from '../utils/request'

// 获取整表 JSON（用于懒加载表格内容）
export const getTableByUid = (tableUid: string) => {
  return request<{ data: any }>({
    url: `/tables/${tableUid}`,
    method: 'get'
  })
}

// 获取整表聚合 JSON（按分片组装）
export const getTableGroupByUid = (tableGroupUid: string) => {
  return request<{ data: any }>({
    url: `/tables/group/${tableGroupUid}`,
    method: 'get'
  })
}

// 获取命中块上下文（父子聚合 + 邻接窗口）
export const getChunkContext = (
  documentId: number,
  chunkId: number,
  params?: { neighbor_pre?: number; neighbor_next?: number; parent_group_max_chars?: number }
) => {
  return request<{ data: any }>({
    url: `/query/documents/${documentId}/chunks/${chunkId}/context`,
    method: 'get',
    params
  })
}
