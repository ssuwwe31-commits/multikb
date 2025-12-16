<template>
  <el-card class="performance-monitor">
    <template #header>
      <div class="monitor-header">
        <span>性能监控</span>
        <el-button size="small" @click="refresh">刷新</el-button>
      </div>
    </template>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="实时统计" name="realtime">
        <div class="stats-grid">
          <el-card class="stat-card">
            <div class="stat-title">总修改次数</div>
            <div class="stat-value">{{ stats.total_modifications }}</div>
          </el-card>
          
          <el-card class="stat-card">
            <div class="stat-title">成功率</div>
            <div class="stat-value">{{ stats.success_rate }}%</div>
          </el-card>
          
          <el-card class="stat-card">
            <div class="stat-title">平均耗时</div>
            <div class="stat-value">{{ stats.avg_duration }}ms</div>
          </el-card>
          
          <el-card class="stat-card">
            <div class="stat-title">错误率</div>
            <div class="stat-value">{{ stats.error_rate }}%</div>
          </el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane label="错误统计" name="errors">
        <el-table :data="errorStats" border>
          <el-table-column prop="error_type" label="错误类型" />
          <el-table-column prop="count" label="数量" />
          <el-table-column prop="percentage" label="占比" />
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="性能趋势" name="trends">
        <div class="chart-container">
          <div id="performanceChart" ref="chartRef" style="width: 100%; height: 300px;"></div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
// import * as echarts from 'echarts'

const activeTab = ref('realtime')
const stats = ref({
  total_modifications: 0,
  success_rate: 0,
  avg_duration: 0,
  error_rate: 0
})
const errorStats = ref<Array<{
  error_type: string
  count: number
  percentage: string
}>>([])
const chartRef = ref<HTMLElement>()

const refresh = async () => {
  try {
    // TODO: 从API获取性能统计数据
    // 这里先使用模拟数据
    stats.value = {
      total_modifications: 123,
      success_rate: 95.5,
      avg_duration: 1250,
      error_rate: 4.5
    }
    
    errorStats.value = [
      { error_type: '向量化失败', count: 5, percentage: '50%' },
      { error_type: '索引更新失败', count: 3, percentage: '30%' },
      { error_type: '网络错误', count: 2, percentage: '20%' }
    ]
  } catch (error) {
    ElMessage.error('获取性能统计失败')
  }
}

const initChart = () => {
  if (!chartRef.value) return
  
  // TODO: 使用echarts初始化图表
  // const chart = echarts.init(chartRef.value)
  // const option = { ... }
  // chart.setOption(option)
}

onMounted(() => {
  refresh()
  initChart()
})
</script>

<style lang="scss" scoped>
.performance-monitor {
  .monitor-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;

    .stat-card {
      .stat-title {
        font-size: 14px;
        color: #666;
        margin-bottom: 10px;
      }

      .stat-value {
        font-size: 28px;
        font-weight: bold;
        color: #409eff;
      }
    }
  }

  .chart-container {
    width: 100%;
  }
}
</style>
