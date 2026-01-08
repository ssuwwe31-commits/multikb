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
            <span class="title-word">multikb</span>
            <span class="title-word gradient-text">Knowledge</span>
            <span class="title-word">Base</span>
          </h1>
          <p class="subtitle">企业级知识库管理平台 · 支持9种文档格式 · 多模态检索 · 知识图谱 · ClamAV安全防护 · 完全开源</p>
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
            @click="$router.push('/qa')"
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
        <h2 class="section-title">核心亮点</h2>
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
  Lock,
  CircleCheck,
  Link,
  Setting,
  Clock,
  DocumentCopy
} from '@element-plus/icons-vue'

const features = ref([
  {
    icon: markRaw(Lock),
    title: '企业级安全',
    description: 'ClamAV 病毒扫描 + 恶意脚本检测，多级数据隔离，完整审计日志，行业唯一'
  },
  {
    icon: markRaw(Document),
    title: '9种文档格式',
    description: 'PDF / Word / Excel / PPT / HTML / Markdown / TXT / JSON / XML 完整支持'
  },
  {
    icon: markRaw(Search),
    title: '多模态检索',
    description: '文本 + 图片 + 混合检索，CLIP 图文对齐，OCR 提取，准确率提升 20%+'
  },
  {
    icon: markRaw(DocumentCopy),
    title: '双层版本管理',
    description: '文档级 + 块级版本控制，版本对比、一键回滚、修改者追踪'
  },
  {
    icon: markRaw(Connection),
    title: '知识图谱',
    description: 'NebulaGraph 分布式图数据库，三种实体提取模式，10+ 种关系识别'
  },
  {
    icon: markRaw(ChatDotRound),
    title: '智能问答',
    description: '6 种检索策略，WebSocket 流式输出，引用溯源，首 Token < 1s'
  },
  {
    icon: markRaw(Lightning),
    title: '任务调度',
    description: 'Celery 多队列 + 优先级 + 分布式锁 + 快速失败，保障解析链路不堆积'
  },
  {
    icon: markRaw(Monitor),
    title: '运维监控',
    description: 'K8s 集群观测、任务监控、指标面板、诊断记录，系统状态一目了然'
  },
  {
    icon: markRaw(Picture),
    title: '图片治理',
    description: '图片向量化、相似度搜索、OCR 识别、MinIO 统一存储管理'
  },
  {
    icon: markRaw(DataAnalysis),
    title: '数据统计',
    description: '文档分析、问答统计、图片分布、任务追踪，数据驱动决策'
  },
  {
    icon: markRaw(CollectionTag),
    title: '导出合规',
    description: '导出任务管理、软硬删除、对象回收、审计日志，满足治理要求'
  },
  {
    icon: markRaw(Setting),
    title: '高度可扩展',
    description: '100+ API 接口、模块化架构、Docker 部署、支持私有化与二次开发'
  }
])

const heroBadges = ref([
  { icon: markRaw(Lock), text: 'ClamAV 安全', gradient: 'badge-gradient-1' },
  { icon: markRaw(MagicStick), text: '多模态检索', gradient: 'badge-gradient-2' },
  { icon: markRaw(Connection), text: '知识图谱', gradient: 'badge-gradient-3' },
  { icon: markRaw(DocumentCopy), text: '双层版本', gradient: 'badge-gradient-4' },
  { icon: markRaw(Cpu), text: 'LLM Ready', gradient: 'badge-gradient-1' },
  { icon: markRaw(CircleCheck), text: '合规可溯', gradient: 'badge-gradient-2' }
])

const highlights = ref([
  {
    icon: markRaw(Connection),
    title: '知识图谱自动构建',
    description: 'NebulaGraph 分布式存储，三种实体提取模式，自动关系识别，ECharts 可视化展示',
    tag: '核心亮点'
  },
  {
    icon: markRaw(Picture),
    title: '多模态检索引擎',
    description: 'CLIP 模型图文对齐，OCR 文字提取，图文混合检索，准确率提升 20%+',
    tag: '核心亮点'
  },
  {
    icon: markRaw(Lock),
    title: 'ClamAV 安全防护',
    description: '实时病毒扫描，恶意脚本检测，行业唯一集成 ClamAV 的开源知识库系统',
    tag: '企业级'
  },
  {
    icon: markRaw(DocumentCopy),
    title: '双层版本管理',
    description: '文档级 + 块级版本控制，版本对比、一键回滚、完整修改记录',
    tag: '企业级'
  },
  {
    icon: markRaw(Clock),
    title: 'WebSocket 流式问答',
    description: '实时流式输出，首 Token < 1s，6 种检索策略，引用溯源标注',
    tag: '用户体验'
  },
  {
    icon: markRaw(Monitor),
    title: 'K8s 集群观测',
    description: '增量同步、健康巡检、诊断记录、任务监控，运维场景更安全',
    tag: '可观测'
  }
])

const stats = ref([
  { value: '9种', label: '文档格式', desc: 'PDF / Word / Excel / PPT 等' },
  { value: '100+', label: 'API接口', desc: '完整的功能覆盖' },
  { value: '6种', label: '检索策略', desc: '向量 / 文本 / 混合 / 图片等' },
  { value: '<1s', label: '问答响应', desc: 'WebSocket 流式输出' },
  { value: '3种', label: '提取模式', desc: '知识图谱实体提取' },
  { value: '20%+', label: '准确率提升', desc: '多模态混合检索' }
])

const recentActivities = ref([
  { icon: markRaw(Connection), text: '知识图谱自动构建完成，已提取 1000+ 个实体', time: '10 分钟前' },
  { icon: markRaw(Lock), text: 'ClamAV 扫描完成，检测到 0 个安全威胁', time: '30 分钟前' },
  { icon: markRaw(Document), text: '完成 50 个文档的批量解析和向量化', time: '1 小时前' },
  { icon: markRaw(ChatDotRound), text: '今日已完成 200+ 次智能问答', time: '2 小时前' }
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
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 24px;
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
      grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
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
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 20px;
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
        font-size: 42px;
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
