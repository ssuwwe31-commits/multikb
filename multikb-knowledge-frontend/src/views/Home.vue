<template>
  <div class="home">
    <!-- 动态背景 -->
    <div class="animated-background">
      <div class="gradient-orb orb-1"></div>
      <div class="gradient-orb orb-2"></div>
      <div class="gradient-orb orb-3"></div>
      <div class="grid-overlay"></div>
      <div class="scanlines"></div>
    </div>

    <!-- 主要内容 -->
    <div class="home-container">
      <!-- 标题区域 -->
      <div class="hero-section">
        <div class="title-wrapper">
          <h1 class="main-title">
            <span class="title-word">SPX</span>
            <span class="title-word gradient-text">Knowledge</span>
            <span class="title-word">Base</span>
          </h1>
          <p class="subtitle">AI驱动的企业级知识运营中枢，覆盖采集、治理、问答、观测与合规</p>
        </div>

        <div class="hero-badges">
          <div class="badge" v-for="badge in heroBadges" :key="badge.text" :class="badge.gradient">
            <span class="badge-icon">
              <el-icon>
                <component :is="badge.icon" />
              </el-icon>
            </span>
            <span>{{ badge.text }}</span>
          </div>
        </div>

        <!-- 快速操作 -->
        <div class="quick-actions">
          <el-button 
            type="primary" 
            size="large" 
            @click="$router.push('/qa/chat')"
            class="action-btn"
          >
            <el-icon><ChatDotRound /></el-icon>
            <span>开始对话</span>
          </el-button>
          <el-button 
            size="large" 
            @click="$router.push('/knowledge-bases/create')"
            class="action-btn"
          >
            <el-icon><Plus /></el-icon>
            <span>创建知识库</span>
          </el-button>
        </div>
      </div>

      <!-- 特性展示 -->
      <div class="features-section">
        <h2 class="section-title">核心能力</h2>
        <div class="features-grid">
          <div class="feature-card" v-for="(feature, index) in features" :key="index">
            <div class="feature-icon" :class="`icon-${index + 1}`">
              <el-icon :size="48">
                <component :is="feature.icon" />
              </el-icon>
            </div>
            <h3>{{ feature.title }}</h3>
            <p>{{ feature.description }}</p>
          </div>
        </div>
      </div>

      <div class="tech-divider"></div>

      <!-- 最新能力 -->
      <div class="latest-section">
        <h2 class="section-title">近期更新</h2>
        <div class="latest-grid">
          <div class="latest-card" v-for="(item, index) in highlights" :key="index">
            <div class="latest-icon">
              <el-icon :size="32">
                <component :is="item.icon" />
              </el-icon>
            </div>
            <div class="latest-content">
              <div class="latest-title">{{ item.title }}</div>
              <p>{{ item.description }}</p>
            </div>
            <span class="latest-tag">{{ item.tag }}</span>
          </div>
        </div>
      </div>

      <div class="tech-divider subtle"></div>

      <!-- 统计数据 -->
      <div class="stats-section">
        <div class="stat-item" v-for="(stat, index) in stats" :key="index">
          <div class="stat-value">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
          <div class="stat-desc">{{ stat.desc }}</div>
        </div>
      </div>

      <!-- 最近活动 -->
      <div class="recent-section">
        <h2 class="section-title">最近操作</h2>
        <div class="recent-list">
          <div class="recent-item" v-for="(item, index) in recentActivities" :key="index">
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ item.text }}</span>
            <span class="time">{{ item.time }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, markRaw } from 'vue'
import { 
  ChatDotRound, 
  Plus, 
  Document, 
  Search, 
  CollectionTag,
  Lightning,
  DataAnalysis,
  UploadFilled,
  Picture,
  Monitor,
  Histogram,
  Cpu,
  MagicStick,
  Connection,
  Lock
} from '@element-plus/icons-vue'

const features = ref([
  {
    icon: markRaw(ChatDotRound),
    title: '多模态问答',
    description: 'RAG 检索 + LLM 兜底，结果可追溯，文本 / 图片 / 表格多模态实时响应'
  },
  {
    icon: markRaw(Document),
    title: '统一文档管道',
    description: 'DOCX / PDF / TXT / 图片一键解析，行号标注、结构分块、TXT 元数据补齐'
  },
  {
    icon: markRaw(Search),
    title: '混合搜索',
    description: '向量搜索 + 关键词 + 搜索历史分页 + LLM 兜底标注，体验与精准度兼顾'
  },
  {
    icon: markRaw(Lightning),
    title: '任务优先级调度',
    description: 'Celery 多队列 + 优先级 + 分布式锁 + 快速失败，保障解析链路不堆积'
  },
  {
    icon: markRaw(Monitor),
    title: '观测诊断',
    description: 'K8s 增量同步窗口、诊断记录软硬删除、集群健康巡检，问题秒级定位'
  },
  {
    icon: markRaw(DataAnalysis),
    title: '运行洞察',
    description: '统计页、图片分布、指标面板和任务监控，系统状态一目了然'
  },
  {
    icon: markRaw(Picture),
    title: '图片与素材治理',
    description: '图片总量 / 类型 / 状态可视，MinIO 类型回填脚本保证历史一致性'
  },
  {
    icon: markRaw(CollectionTag),
    title: '导出与合规',
    description: '导出任务软硬删除、MinIO 对象回收、审计日志全链路记录，满足治理诉求'
  }
])

const heroBadges = ref([
  { icon: markRaw(Cpu), text: 'LLM Ready', gradient: 'badge-gradient-1' },
  { icon: markRaw(MagicStick), text: '多模态输入', gradient: 'badge-gradient-2' },
  { icon: markRaw(Connection), text: 'K8s 观测', gradient: 'badge-gradient-3' },
  { icon: markRaw(Lock), text: '合规可溯', gradient: 'badge-gradient-4' }
])

const highlights = ref([
  {
    icon: markRaw(UploadFilled),
    title: 'TXT 上传 & 编排',
    description: '自动编码检测、段落/行号定位与结构化切分，纯文本同样可视可控',
    tag: '文档能力'
  },
  {
    icon: markRaw(Picture),
    title: '图片统计与类型回填',
    description: '图片总量、类型/状态分布与历史回填脚本，全量掌握素材资产',
    tag: '数据统计'
  },
  {
    icon: markRaw(Monitor),
    title: 'K8s 同步与诊断',
    description: '增量同步窗口、快速失败、诊断记录软硬删除，运维场景更安全',
    tag: '可观测'
  },
  {
    icon: markRaw(Histogram),
    title: '检索历史与兜底标注',
    description: 'LLM 回答自动标注来源，搜索历史分页展示，使用体验更透明',
    tag: '搜索体验'
  }
])

const stats = ref([
  { value: '12+', label: '活跃知识库', desc: '实时同步 / 自动治理' },
  { value: '3.5w+', label: '已解析文档', desc: 'DOCX / PDF / TXT / 图片' },
  { value: '18w+', label: '累计问答', desc: 'RAG 检索 + LLM 兜底' },
  { value: '99.9%', label: '系统可用性', desc: '任务优先级 + 快速失败' }
])

const recentActivities = ref([
  { icon: markRaw(Document), text: '完成 TXT 文档批量解析', time: '15 分钟前' },
  { icon: markRaw(Monitor), text: '诊断记录已软硬删除并归档', time: '2 小时前' },
  { icon: markRaw(CollectionTag), text: '导出任务自动清理 MinIO 文件', time: '昨天' }
])

onMounted(() => {
  // 加载统计数据
  loadStats()
})

const loadStats = async () => {
  // TODO: 从API加载实际统计数据
  // const res = await getStats()
  // stats.value = res.data
}
</script>

<style lang="scss" scoped>
.home {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  background: radial-gradient(circle at top, rgba(39, 112, 255, 0.25), transparent 45%),
    radial-gradient(circle at 20% 20%, rgba(103, 194, 58, 0.2), transparent 40%),
    #05060d;
  color: #ffffff;

  .animated-background {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    overflow: hidden;
    opacity: 0.85;

    .gradient-orb {
      position: absolute;
      border-radius: 50%;
      filter: blur(80px);
      animation: float 20s infinite ease-in-out;
    }

    .orb-1 {
      width: 400px;
      height: 400px;
      background: radial-gradient(circle, #409eff 0%, transparent 70%);
      top: -200px;
      left: -200px;
      animation-delay: 0s;
    }

    .orb-2 {
      width: 500px;
      height: 500px;
      background: radial-gradient(circle, #67c23a 0%, transparent 70%);
      bottom: -250px;
      right: -250px;
      animation-delay: 5s;
    }

    .orb-3 {
      width: 300px;
      height: 300px;
      background: radial-gradient(circle, #e6a23c 0%, transparent 70%);
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      animation-delay: 10s;
    }

    .grid-overlay {
      position: absolute;
      inset: 0;
      background-image: linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px);
      background-size: 80px 80px;
      animation: gridMove 40s linear infinite;
      mix-blend-mode: screen;
      opacity: 0.35;
    }

    .scanlines {
      position: absolute;
      inset: 0;
      background-image: linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px);
      background-size: 100% 4px;
      opacity: 0.25;
      animation: scan 12s linear infinite;
    }
  }

  .home-container {
    position: relative;
    z-index: 1;
    padding: 40px;
    max-width: 1400px;
    margin: 0 auto;
  }

  .hero-section {
    text-align: center;
    padding: 60px 0;
    margin-bottom: 80px;

    .title-wrapper {
      margin-bottom: 40px;
    }

    .main-title {
      font-size: 64px;
      font-weight: 700;
      margin: 0;
      line-height: 1.2;
      display: flex;
      justify-content: center;
      gap: 16px;
      flex-wrap: wrap;

      .title-word {
        display: inline-block;
        animation: fadeInUp 0.6s ease-out backwards;
        
        &:nth-child(1) {
          animation-delay: 0.1s;
        }
        &:nth-child(2) {
          animation-delay: 0.2s;
        }
        &:nth-child(3) {
          animation-delay: 0.3s;
        }
      }

      .gradient-text {
        background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }
    }

    .subtitle {
      font-size: 20px;
      color: rgba(255, 255, 255, 0.7);
      margin-top: 20px;
      animation: fadeInUp 0.6s ease-out 0.4s backwards;
    }

    .hero-badges {
      margin-top: 28px;
      display: flex;
      justify-content: center;
      flex-wrap: wrap;
      gap: 14px;

      .badge {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 8px 16px;
        border-radius: 999px;
        background: rgba(13, 17, 32, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.1);
        font-size: 14px;
        letter-spacing: 0.2px;
        box-shadow: 0 0 25px rgba(64, 158, 255, 0.25);
        backdrop-filter: blur(6px);
        color: #e5f4ff;
        text-transform: uppercase;

        .badge-icon {
          width: 24px;
          height: 24px;
          border-radius: 50%;
          background: rgba(0,0,0,0.25);
          display: inline-flex;
          align-items: center;
          justify-content: center;

          :deep(svg) {
            width: 16px;
            height: 16px;
          }
        }

        &.badge-gradient-1 {
          background: linear-gradient(135deg, rgba(255, 147, 39, 0.25), rgba(255, 96, 54, 0.18));
          border-color: rgba(255, 147, 39, 0.5);
        }

        &.badge-gradient-2 {
          background: linear-gradient(135deg, rgba(176, 106, 255, 0.25), rgba(99, 102, 241, 0.2));
          border-color: rgba(176, 106, 255, 0.45);
        }

        &.badge-gradient-3 {
          background: linear-gradient(135deg, rgba(82, 183, 255, 0.25), rgba(59, 130, 246, 0.2));
          border-color: rgba(82, 183, 255, 0.45);
        }

        &.badge-gradient-4 {
          background: linear-gradient(135deg, rgba(125, 249, 207, 0.25), rgba(34, 211, 238, 0.2));
          border-color: rgba(125, 249, 207, 0.45);
        }
      }
    }

    .quick-actions {
      display: flex;
      justify-content: center;
      gap: 20px;
      margin-top: 40px;
      animation: fadeInUp 0.6s ease-out 0.5s backwards;

      .action-btn {
        padding: 12px 32px;
        font-size: 16px;
        border-radius: 8px;
        transition: all 0.3s ease;

        &:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 24px rgba(64, 158, 255, 0.3);
        }
      }
    }
  }

  .features-section {
    margin-bottom: 80px;

    .section-title {
      font-size: 32px;
      font-weight: 600;
      margin-bottom: 40px;
      text-align: center;
    }

    .features-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 30px;
    }

    .feature-card {
      background: rgba(8, 12, 26, 0.85);
      backdrop-filter: blur(14px);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 18px;
      padding: 32px;
      transition: all 0.35s ease;
      position: relative;
      overflow: hidden;
      box-shadow: 0 20px 50px rgba(5, 6, 13, 0.7);

      &::before {
        content: '';
        position: absolute;
        inset: -1px;
        border-radius: inherit;
        padding: 1px;
        background: linear-gradient(135deg, rgba(64,158,255,0.45), rgba(103,194,58,0.45));
        -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        -webkit-mask-composite: xor;
        mask-composite: exclude;
        opacity: 0;
        transition: opacity 0.35s ease;
      }

      &:hover {
        transform: translateY(-10px);
        background: rgba(15, 19, 36, 0.95);
        box-shadow: 0 25px 60px rgba(64, 158, 255, 0.25);

        &::before {
          opacity: 1;
        }
      }

      .feature-icon {
        margin-bottom: 20px;
        width: 80px;
        height: 80px;
        border-radius: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(64, 158, 255, 0.12);
        color: #6cb7ff;
      }

      h3 {
        font-size: 20px;
        font-weight: 600;
        margin-bottom: 12px;
      }

      p {
        color: rgba(255, 255, 255, 0.7);
        line-height: 1.6;
        margin: 0;
      }
    }
  }

  .latest-section {
    margin-bottom: 80px;

    .section-title {
      font-size: 28px;
      font-weight: 600;
      margin-bottom: 32px;
      text-align: center;
    }

    .latest-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 24px;
    }

    .latest-card {
      display: flex;
      align-items: flex-start;
      gap: 16px;
      padding: 24px;
      border-radius: 16px;
      background: rgba(17, 24, 39, 0.7);
      border: 1px solid rgba(255, 255, 255, 0.08);
      position: relative;
      overflow: hidden;
      transition: all 0.3s ease;

      &:hover {
        border-color: rgba(64, 158, 255, 0.5);
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35);
      }

      .latest-icon {
        width: 56px;
        height: 56px;
        border-radius: 14px;
        background: rgba(64, 158, 255, 0.12);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #66b1ff;
      }

      .latest-content {
        flex: 1;

        .latest-title {
          font-size: 18px;
          font-weight: 600;
          margin-bottom: 8px;
        }

        p {
          margin: 0;
          color: rgba(255, 255, 255, 0.7);
          line-height: 1.6;
        }
      }

      .latest-tag {
        position: absolute;
        top: 16px;
        right: 16px;
        padding: 4px 10px;
        border-radius: 999px;
        background: rgba(103, 194, 58, 0.15);
        color: #8be28f;
        font-size: 12px;
      }
    }
  }

  .stats-section {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 24px;
    background: rgba(6, 10, 24, 0.8);
    backdrop-filter: blur(18px);
    border: 1px solid rgba(64, 158, 255, 0.18);
    border-radius: 24px;
    padding: 40px 48px;
    margin-bottom: 80px;
    box-shadow: 0 24px 70px rgba(3, 7, 18, 0.85);

    .stat-item {
      text-align: center;
      position: relative;
      padding: 12px 0;

      .stat-value {
        font-size: 52px;
        font-weight: 700;
        background: linear-gradient(135deg, #67c23a 0%, #409eff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 8px;
      }

      .stat-label {
        color: rgba(255, 255, 255, 0.8);
        font-size: 15px;
        letter-spacing: 0.3px;
      }

      .stat-desc {
        margin-top: 6px;
        font-size: 13px;
        color: rgba(255, 255, 255, 0.5);
      }

      &::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 60%;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
        opacity: 0.5;
      }

      &:last-child::after {
        display: none;
      }
    }
  }

  .recent-section {
    .section-title {
      font-size: 24px;
      font-weight: 600;
      margin-bottom: 24px;
    }

    .recent-list {
      background: rgba(255, 255, 255, 0.05);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 16px;
      padding: 20px;

      .recent-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 16px;
        margin-bottom: 8px;
        border-radius: 8px;
        transition: all 0.3s ease;

        &:hover {
          background: rgba(255, 255, 255, 0.05);
        }

        .time {
          margin-left: auto;
          color: rgba(255, 255, 255, 0.5);
          font-size: 12px;
        }
      }
    }
  }

  .tech-divider {
    width: 100%;
    height: 1px;
    margin: 40px 0;
    background: linear-gradient(90deg, transparent, rgba(64, 158, 255, 0.7), transparent);
    position: relative;

    &::after {
      content: '';
      position: absolute;
      top: -3px;
      left: 50%;
      transform: translateX(-50%);
      width: 60px;
      height: 6px;
      border-radius: 999px;
      background: linear-gradient(90deg, rgba(64,158,255,0.8), rgba(103,194,58,0.8));
      box-shadow: 0 0 16px rgba(64,158,255,0.6);
    }

    &.subtle {
      opacity: 0.5;
    }
  }
}

@keyframes gridMove {
  from { background-position: 0 0, 0 0; }
  to { background-position: 80px 80px, 80px 80px; }
}

@keyframes scan {
  0% { background-position: 0 0; }
  100% { background-position: 0 100%; }
}

@keyframes float {
  0%, 100% {
    transform: translate(0, 0);
  }
  25% {
    transform: translate(20px, -20px);
  }
  50% {
    transform: translate(-20px, 20px);
  }
  75% {
    transform: translate(20px, 20px);
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
