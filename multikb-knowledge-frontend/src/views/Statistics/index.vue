<template>
  <div class="statistics-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>个人数据统计</span>
          <el-select v-model="period" @change="loadStatistics" style="width: 150px">
            <el-option label="全部" value="all" />
            <el-option label="本周" value="week" />
            <el-option label="本月" value="month" />
            <el-option label="本年" value="year" />
          </el-select>
        </div>
      </template>

      <div v-loading="loading">
        <!-- 知识库统计 -->
        <el-card class="stat-card" shadow="hover">
          <template #header>
            <span>知识库统计</span>
          </template>
          <div class="stat-grid">
            <div class="stat-item">
              <div class="stat-value">{{ statistics.knowledge_bases?.total || 0 }}</div>
              <div class="stat-label">知识库总数</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ statistics.knowledge_bases?.active || 0 }}</div>
              <div class="stat-label">活跃知识库</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ statistics.knowledge_bases?.total_documents || 0 }}</div>
              <div class="stat-label">文档总数</div>
            </div>
          </div>
        </el-card>

        <!-- 文档统计 -->
        <el-card class="stat-card" shadow="hover">
          <template #header>
            <span>文档统计</span>
          </template>
          <div class="stat-grid">
            <div class="stat-item">
              <div class="stat-value">{{ statistics.documents?.total || 0 }}</div>
              <div class="stat-label">文档总数</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ formatFileSize(statistics.documents?.total_size || 0) }}</div>
              <div class="stat-label">总大小</div>
            </div>
          </div>

          <!-- 文档类型分布 -->
          <el-divider>文档类型分布</el-divider>
          <div class="chart-container">
            <v-chart
              v-if="documentTypeChartOption"
              class="stat-chart"
              :option="documentTypeChartOption"
              autoresize
            />
            <el-empty v-else description="暂无文档" :image-size="60" />
          </div>

          <!-- 文档状态分布 -->
          <el-divider>文档状态分布</el-divider>
          <div class="chart-container">
            <v-chart
              v-if="documentStatusChartOption"
              class="stat-chart"
              :option="documentStatusChartOption"
              autoresize
            />
            <div v-else class="empty-chart-hint">
              <el-empty description="暂无状态数据" :image-size="60" />
            </div>
          </div>
          <div v-if="documentStatusChartOption" class="chart-summary">
            <div class="summary-text">
              共 <strong>{{ statistics.documents?.total || 0 }}</strong> 个文档，其中
              <template v-for="(count, status) in statistics.documents?.by_status" :key="status">
                <el-tag :type="getStatusTagType(status)" size="small" style="margin: 0 4px;">
                  {{ getStatusText(status) }}: {{ count }}
                </el-tag>
              </template>
            </div>
          </div>
        </el-card>

        <!-- 图片统计 -->
        <el-card class="stat-card" shadow="hover">
          <template #header>
            <span>图片统计</span>
          </template>
          <div class="stat-grid">
            <div class="stat-item">
              <div class="stat-value">{{ statistics.images?.total || 0 }}</div>
              <div class="stat-label">图片总数</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ formatFileSize(statistics.images?.total_size || 0) }}</div>
              <div class="stat-label">总大小</div>
            </div>
          </div>

          <el-divider>图片类型分布</el-divider>
          <div class="type-distribution">
            <template v-if="statistics.images?.by_type && Object.keys(statistics.images.by_type).length">
              <div
                v-for="(count, type) in statistics.images.by_type"
                :key="type"
                class="type-item"
                :style="{ '--type-color': getTypeColor(type) }"
              >
                <div class="type-header">
                  <div class="type-icon">
                    {{ type.slice(0, 1).toUpperCase() }}
                  </div>
                  <div class="type-info">
                    <span class="type-name">{{ type.toUpperCase() }}</span>
                    <span class="type-desc">智能图片类型</span>
                  </div>
                  <span class="type-percent-chip">{{ getImageTypePercentage(type) }}%</span>
                </div>
                <el-progress
                  class="type-progress"
                  :percentage="getImageTypePercentage(type)"
                  :color="getTypeColor(type)"
                  :stroke-width="12"
                  :show-text="false"
                />
                <div class="type-footer">
                  <span class="type-count-label">数量</span>
                  <span class="type-count">{{ count }}</span>
                </div>
              </div>
            </template>
            <el-empty
              v-else
              description="暂无图片"
              :image-size="60"
            />
          </div>

          <el-divider>图片状态分布</el-divider>
          <div class="status-distribution">
            <template v-if="statistics.images?.by_status && Object.keys(statistics.images?.by_status).length">
              <el-tag
                v-for="(count, status) in statistics.images?.by_status"
                :key="status"
                :type="getStatusTagType(status)"
                size="large"
                class="status-tag"
              >
                {{ getStatusText(status) }}: {{ count }}
              </el-tag>
            </template>
            <el-empty
              v-else
              description="暂无状态数据"
              :image-size="60"
            />
          </div>
        </el-card>

        <!-- 使用情况 -->
        <el-card class="stat-card" shadow="hover">
          <template #header>
            <span>使用情况</span>
          </template>
          <div class="stat-grid">
            <div class="stat-item">
              <div class="stat-value">{{ statistics.usage?.total_searches || 0 }}</div>
              <div class="stat-label">搜索次数</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ statistics.usage?.total_qa_sessions || 0 }}</div>
              <div class="stat-label">问答次数</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ statistics.usage?.total_uploads || 0 }}</div>
              <div class="stat-label">上传次数</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ statistics.usage?.last_active_date || '—' }}</div>
              <div class="stat-label">最后活跃</div>
            </div>
          </div>
        </el-card>

        <!-- 存储统计 -->
        <el-card class="stat-card" shadow="hover">
          <template #header>
            <span>存储统计</span>
          </template>
          <div class="storage-info">
            <div class="storage-header">
              <div class="storage-item">
                <div class="storage-icon used">
                  <el-icon><FolderOpened /></el-icon>
                </div>
                <div class="storage-content">
                  <span class="storage-label">已用存储</span>
                  <span class="storage-value">{{ formatFileSize(statistics.storage?.used || 0) }}</span>
                </div>
              </div>
              <div class="storage-item">
                <div class="storage-icon limit">
                  <el-icon><Box /></el-icon>
                </div>
                <div class="storage-content">
                  <span class="storage-label">存储限制</span>
                  <span class="storage-value">{{ formatFileSize(statistics.storage?.limit || 0) }}</span>
                </div>
              </div>
            </div>
            <div class="storage-progress-wrapper">
              <el-progress
                :percentage="statistics.storage?.percentage || 0"
                :color="getStorageColor(statistics.storage?.percentage || 0)"
                :stroke-width="24"
                :show-text="false"
                class="storage-progress"
              />
              <div class="progress-info">
                <span class="progress-text">存储使用率</span>
                <span class="progress-percentage">{{ (statistics.storage?.percentage || 0).toFixed(2) }}%</span>
              </div>
            </div>
          </div>
        </el-card>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { FolderOpened, Box } from '@element-plus/icons-vue'
import { getPersonalStatistics } from '@/api/modules/statistics'
import { formatFileSize } from '@/utils/format'

const loading = ref(false)
const period = ref('all')
const statistics = ref<any>({
  knowledge_bases: {},
  documents: {},
  images: {},
  usage: {},
  storage: {}
})

const loadStatistics = async () => {
  loading.value = true
  try {
    const res = await getPersonalStatistics(period.value)
    const data = res?.data || res
    statistics.value = data || {
      knowledge_bases: {},
      documents: {},
      images: {},
      usage: {},
      storage: {}
    }
    // 确保 documents 结构完整
    if (!statistics.value.documents) {
      statistics.value.documents = {
        total: 0,
        by_type: {},
        by_status: {},
        total_size: 0
      }
    }
    // 确保 by_type 和 by_status 存在
    if (!statistics.value.documents.by_type) {
      statistics.value.documents.by_type = {}
    }
    if (!statistics.value.documents.by_status) {
      statistics.value.documents.by_status = {}
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || error.message || '加载统计数据失败')
  } finally {
    loading.value = false
  }
}

const colorPalette: Record<string, string> = {
  pdf: '#5ad8a6',
  docx: '#5b8ff9',
  txt: '#ff9f7f',
  xlsx: '#f6bd16',
  pptx: '#e8684a'
}

const getTypeColor = (type: string) => colorPalette[type.toLowerCase()] || '#73c0de'

const documentTypeChartOption = computed(() => {
  const byType = statistics.value.documents?.by_type || {}
  const entries = Object.entries(byType)
  if (!entries.length) return null
  
  const data = entries.map(([type, value]) => ({
    value,
    name: type.toUpperCase(),
    itemStyle: { color: getTypeColor(type) }
  }))
  
  return {
    backgroundColor: 'transparent',
    tooltip: { 
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      right: 20,
      top: 'center',
      textStyle: { color: '#dbe0ff' }
    },
    series: [
      {
        name: '文档类型',
        type: 'pie',
        radius: ['40%', '65%'],
        center: ['35%', '50%'],
        itemStyle: {
          borderRadius: 10,
          borderColor: '#0f1525',
          borderWidth: 2
        },
        label: { 
          color: '#dbe0ff',
          show: true,
          formatter: '{b}\n{d}%'
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        },
        data: data
      }
    ]
  }
})

const documentStatusChartOption = computed(() => {
  const entries = Object.entries(statistics.value.documents?.by_status || {})
  if (!entries.length) return null
  
  const total = statistics.value.documents?.total || 0
  
  return {
    backgroundColor: 'transparent',
    title: {
      text: '文档状态统计',
      left: 'center',
      top: 10,
      textStyle: {
        color: '#dbe0ff',
        fontSize: 14,
        fontWeight: 'normal'
      }
    },
    tooltip: { 
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const param = params[0]
        const percentage = total > 0 ? ((param.value / total) * 100).toFixed(1) : 0
        return `${param.name}<br/>数量: ${param.value} (${percentage}%)`
      }
    },
    grid: { left: '15%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
    xAxis: {
      type: 'value',
      axisLabel: { 
        color: '#dbe0ff',
        formatter: '{value}'
      },
      splitLine: { 
        lineStyle: { color: 'rgba(255,255,255,0.1)' },
        show: true
      }
    },
    yAxis: {
      type: 'category',
      data: entries.map(([status]) => getStatusText(status)),
      axisLabel: { 
        color: '#dbe0ff',
        fontSize: 12
      }
    },
    series: [
      {
        name: '文档数量',
        type: 'bar',
        barWidth: 24,
        data: entries.map(([status, count]) => ({
          value: count,
          itemStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 1,
              y2: 0,
              colorStops: [
                { offset: 0, color: getStatusColor(status, 0) },
                { offset: 1, color: getStatusColor(status, 1) }
              ]
            },
            borderRadius: [0, 6, 6, 0]
          }
        })),
        label: { 
          show: true, 
          position: 'right', 
          color: '#fff',
          formatter: (params: any) => {
            const percentage = total > 0 ? ((params.value / total) * 100).toFixed(0) : 0
            return `${params.value} (${percentage}%)`
          }
        }
      }
    ]
  }
})

const getStatusColor = (status: string, index: number) => {
  const colors: Record<string, string[]> = {
    completed: ['#5ad8a6', '#67c23a'],
    processed: ['#5ad8a6', '#67c23a'],
    processing: ['#5b8ff9', '#409eff'],
    pending: ['#e6a23c', '#f6bd16'],
    failed: ['#f56c6c', '#e8684a']
  }
  const statusColors = colors[status] || ['#5b8ff9', '#5ad8a6']
  return statusColors[index] || statusColors[0]
}

const getImageTypePercentage = (type: string) => {
  const total = statistics.value.images?.total || 0
  const count = statistics.value.images?.by_type?.[type] || 0
  return total > 0 ? Math.round((count / total) * 100) : 0
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    completed: '已完成',
    processing: '处理中',
    failed: '失败',
    pending: '待处理',
    processed: '已处理'
  }
  return texts[status] || status
}

const getStatusTagType = (status: string) => {
  const types: Record<string, string> = {
    completed: 'success',
    processed: 'success',
    processing: 'warning',
    pending: 'info',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStorageColor = (percentage: number) => {
  if (percentage >= 90) return '#f56c6c'
  if (percentage >= 70) return '#e6a23c'
  return '#67c23a'
}

onMounted(() => {
  loadStatistics()
})
</script>

<style lang="scss" scoped>
.statistics-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .stat-card {
    margin-bottom: 20px;

    .stat-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 20px;
      padding: 20px 0;

      .stat-item {
        text-align: center;

        .stat-value {
          font-size: 32px;
          font-weight: 700;
          color: #7cc4ff;
          margin-bottom: 8px;
          text-shadow: 0 0 6px rgba(64, 158, 255, 0.35);
        }

        .stat-label {
          color: #d1dcff;
          font-size: 14px;
          letter-spacing: 0.5px;
        }
      }
    }

    .chart-container {
      height: 280px;
      padding: 10px 0;

      .stat-chart {
        width: 100%;
        height: 100%;
      }
      
      .empty-chart-hint {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
      }
    }
    
    .chart-summary {
      margin-top: 12px;
      padding: 12px 16px;
      background: rgba(255, 255, 255, 0.03);
      border-radius: 8px;
      border: 1px solid rgba(255, 255, 255, 0.08);
      
      .summary-text {
        color: #dbe0ff;
        font-size: 13px;
        line-height: 1.8;
        text-align: center;
        
        strong {
          color: #7cc4ff;
          font-weight: 600;
          font-size: 15px;
        }
        
        .el-tag {
          vertical-align: middle;
        }
      }
    }

    .type-distribution {
      padding: 10px 0 10px;

      .type-item {
        position: relative;
        display: flex;
        flex-direction: column;
        gap: 12px;
        margin-bottom: 16px;
        padding: 18px 22px;
        border-radius: 18px;
        background:
          radial-gradient(circle at 20% 20%, rgba(255, 255, 255, 0.12), transparent 60%),
          linear-gradient(130deg, rgba(33, 150, 243, 0.22), rgba(22, 38, 78, 0.5));
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow:
          inset 0 0 35px rgba(255, 255, 255, 0.04),
          0 15px 25px rgba(15, 22, 41, 0.55);
        overflow: hidden;

        &::after {
          content: '';
          position: absolute;
          inset: 0;
          background: linear-gradient(120deg, transparent 0%, rgba(255, 255, 255, 0.08) 50%, transparent 100%);
          transform: translateX(-100%);
          animation: sweep 6s linear infinite;
          pointer-events: none;
        }

        .type-header {
          display: flex;
          align-items: center;
          gap: 14px;
        }

        .type-icon {
          width: 48px;
          height: 48px;
          border-radius: 14px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 20px;
          font-weight: 700;
          color: #f7fbff;
          border: 1px solid rgba(255, 255, 255, 0.2);
          background: radial-gradient(circle, rgba(255, 255, 255, 0.22), transparent 65%);
          box-shadow: 0 0 20px color-mix(in srgb, var(--type-color, #409eff) 60%, transparent);
        }

        .type-info {
          display: flex;
          flex-direction: column;
          gap: 4px;
          flex: 1;
        }

        .type-name {
          font-size: 18px;
          font-weight: 600;
          color: #f6faff;
          letter-spacing: 0.5px;
        }

        .type-desc {
          font-size: 12px;
          text-transform: uppercase;
          color: #a8b7ff;
          letter-spacing: 3px;
        }

        .type-percent-chip {
          padding: 6px 14px;
          border-radius: 999px;
          font-weight: 600;
          color: #0f1d35;
          background: linear-gradient(90deg, var(--type-color, #409eff), color-mix(in srgb, var(--type-color, #409eff) 60%, #ffffff));
          box-shadow: 0 0 18px color-mix(in srgb, var(--type-color, #409eff) 70%, transparent);
        }

        .type-progress {
          width: 100%;

          :deep(.el-progress-bar) {
            padding-right: 0;
          }

          :deep(.el-progress-bar__outer) {
            background: rgba(255, 255, 255, 0.08);
            border-radius: 999px;
          }

          :deep(.el-progress-bar__inner) {
            border-radius: 999px;
            background-image: linear-gradient(90deg, var(--type-color, #409eff), color-mix(in srgb, var(--type-color, #409eff) 70%, #ffffff));
            box-shadow: 0 0 16px color-mix(in srgb, var(--type-color, #409eff) 70%, transparent);
          }
        }

        .type-footer {
          display: flex;
          justify-content: flex-end;
          align-items: baseline;
          gap: 8px;
        }

        .type-count-label {
          font-size: 12px;
          color: #9eb2ff;
          text-transform: uppercase;
          letter-spacing: 2px;
        }

        .type-count {
          font-size: 24px;
          font-weight: 700;
          color: #ffffff;
          text-shadow: 0 0 12px rgba(255, 255, 255, 0.35);
        }
      }
    }

    @keyframes sweep {
      0% {
        transform: translateX(-100%);
      }
      60% {
        transform: translateX(120%);
      }
      100% {
        transform: translateX(120%);
      }
    }

    .status-distribution {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 12px;
      padding-top: 16px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);

      .status-tag {
        margin: 0;
      }
    }

    .storage-info {
      .storage-header {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 20px;
        margin-bottom: 24px;
      }

      .storage-item {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 18px 20px;
        border-radius: 12px;
        background: linear-gradient(135deg, rgba(64, 158, 255, 0.12), rgba(64, 158, 255, 0.04));
        border: 1px solid rgba(64, 158, 255, 0.2);
        transition: all 0.3s ease;

        &:hover {
          background: linear-gradient(135deg, rgba(64, 158, 255, 0.18), rgba(64, 158, 255, 0.08));
          border-color: rgba(64, 158, 255, 0.35);
          transform: translateY(-2px);
          box-shadow: 0 8px 20px rgba(64, 158, 255, 0.15);
        }

        .storage-icon {
          width: 48px;
          height: 48px;
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 24px;
          flex-shrink: 0;

          &.used {
            background: linear-gradient(135deg, rgba(103, 194, 58, 0.25), rgba(103, 194, 58, 0.1));
            color: #67c23a;
            border: 1px solid rgba(103, 194, 58, 0.3);
          }

          &.limit {
            background: linear-gradient(135deg, rgba(64, 158, 255, 0.25), rgba(64, 158, 255, 0.1));
            color: #409eff;
            border: 1px solid rgba(64, 158, 255, 0.3);
          }
        }

        .storage-content {
          display: flex;
          flex-direction: column;
          gap: 6px;
          flex: 1;
        }

        .storage-label {
          color: #a8b7ff;
          font-size: 13px;
          letter-spacing: 0.5px;
        }

        .storage-value {
          font-weight: 700;
          font-size: 20px;
          color: #f5f7ff;
          text-shadow: 0 0 8px rgba(124, 196, 255, 0.4);
          letter-spacing: 0.3px;
        }
      }

      .storage-progress-wrapper {
        margin-top: 24px;
        padding: 20px;
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);

        .storage-progress {
          margin-bottom: 12px;

          :deep(.el-progress-bar) {
            padding-right: 0;
          }

          :deep(.el-progress-bar__outer) {
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.2);
          }

          :deep(.el-progress-bar__inner) {
            border-radius: 12px;
            position: relative;
            overflow: hidden;
            
            &::after {
              content: '';
              position: absolute;
              top: 0;
              left: -100%;
              width: 100%;
              height: 100%;
              background: linear-gradient(
                90deg,
                transparent,
                rgba(255, 255, 255, 0.3),
                transparent
              );
              animation: shimmer 2s infinite;
            }
          }
        }

        .progress-info {
          display: flex;
          justify-content: space-between;
          align-items: center;

          .progress-text {
            color: #c7d0ff;
            font-size: 13px;
            letter-spacing: 0.5px;
          }

          .progress-percentage {
            font-weight: 700;
            font-size: 18px;
            color: #7cc4ff;
            text-shadow: 0 0 6px rgba(124, 196, 255, 0.5);
          }
        }
      }
    }

    @keyframes shimmer {
      0% {
        left: -100%;
      }
      100% {
        left: 100%;
      }
    }
  }
}
</style>
