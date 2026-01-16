<template>
  <div class="code-structure-wiki">
    <div class="wiki-container">
      <!-- 左侧导航栏 -->
      <aside class="wiki-sidebar">
          <div class="sidebar-header">
            <div class="last-indexed">
              <span>最后索引: {{ lastIndexed }}</span>
              <span v-if="repository?.last_commit_hash" class="commit-hash">
                ({{ repository.last_commit_hash.substring(0, 7) }})
              </span>
            </div>
          </div>
        
        <nav class="sidebar-nav">
          <div 
            v-for="item in navigationItems" 
            :key="item.id"
            class="nav-item"
            :class="{ 
              active: activeSection === item.id || (item.children && item.children.some(c => activeSection === c.id)),
              'has-children': item.children && item.children.length > 0
            }"
          >
            <div 
              class="nav-item-main" 
              :style="{ paddingLeft: `${item.level * 16}px` }"
              @click="scrollToSection(item.id)"
            >
              <span>{{ item.label }}</span>
            </div>
            <div v-if="item.children && item.children.length > 0" class="nav-children">
              <div
                v-for="child in item.children"
                :key="child.id"
                class="nav-item nav-item-child"
                :class="{ active: activeSection === child.id }"
                :style="{ paddingLeft: `${child.level * 16}px` }"
                @click.stop="scrollToSection(child.id)"
              >
                {{ child.label }}
              </div>
            </div>
          </div>
        </nav>
      </aside>

      <!-- 中间主内容区 -->
      <main class="wiki-main">
        <div class="wiki-content">
          <!-- 标题 -->
          <h1 class="wiki-title">代码结构</h1>

          <!-- 相关源文件 -->
          <div class="relevant-files-section">
            <div class="expandable-header" @click="showRelevantFiles = !showRelevantFiles">
              <span :class="{ 'expanded': showRelevantFiles }">▶</span>
              <span>相关源文件</span>
            </div>
            <div v-if="showRelevantFiles" class="relevant-files-list">
              <div 
                v-for="file in relevantFiles" 
                :key="file.path"
                class="file-item"
                :class="{ 'high-importance': file.importance && file.importance >= 8 }"
                @click="viewFile(file)"
              >
                <span class="file-path">{{ file.path }}</span>
                <span v-if="file.type" class="file-type-badge">{{ file.type }}</span>
                <span v-if="file.importance" class="importance-badge">重要性: {{ file.importance }}</span>
              </div>
            </div>
          </div>

          <!-- 介绍段落 -->
          <div class="intro-section">
            <p>
              本文档介绍 {{ repository?.repo_name }} 代码库的整体结构、核心组件、架构设计和技术栈。
              详细的功能说明请参考以下章节：
            </p>
            <ul class="internal-links">
              <li v-for="link in internalLinks" :key="link.id">
                <a @click="scrollToSection(link.id)">{{ link.label }}</a>
              </li>
            </ul>
          </div>

          <!-- 项目介绍 -->
          <section id="what-is" class="wiki-section">
            <h2>{{ repository?.repo_name }} 是什么</h2>
            <p>{{ whatIsProject }}</p>
          </section>

          <!-- 核心价值主张 -->
          <section id="core-value" class="wiki-section">
            <h2>核心价值主张</h2>
            <el-table :data="valuePropositions" border style="width: 100%; margin-top: 16px">
              <el-table-column prop="feature" label="特性" width="200" />
              <el-table-column prop="description" label="描述" />
            </el-table>
          </section>

          <!-- 主要特性 -->
          <section id="key-features" class="wiki-section">
            <h2>主要特性</h2>
            <div class="features-content">
              <div v-for="feature in keyFeatures" :key="feature.name" class="feature-item">
                <h3>{{ feature.name }}</h3>
                <p>{{ feature.description }}</p>
              </div>
            </div>
          </section>

          <!-- 项目概述 -->
          <section id="overview" class="wiki-section">
            <h2>项目概述</h2>
            <div v-loading="wikiLoading">
              <div v-if="projectOverview" class="overview-content" v-html="formatMarkdown(projectOverview)"></div>
              <div v-else-if="!wikiLoading" class="overview-placeholder">
                <p>加载中...</p>
              </div>
            </div>
          </section>

          <!-- 核心组件 -->
          <section id="components" class="wiki-section">
            <h2>核心组件</h2>
            <p>项目的主要组件及其职责：</p>
            <el-table :data="componentsTable" border style="width: 100%; margin-top: 16px">
              <el-table-column prop="name" label="组件名称" width="250" />
              <el-table-column prop="purpose" label="职责说明" min-width="300" />
              <el-table-column prop="files" label="文件数" width="100" align="center" />
              <el-table-column prop="lines" label="代码行数" width="120" align="center" />
              <el-table-column prop="symbols" label="符号数" width="100" align="center" />
              <el-table-column prop="languages" label="语言" width="150" align="center" />
            </el-table>
          </section>

          <!-- 技术栈 -->
          <section id="tech-stack" class="wiki-section">
            <h2>技术栈</h2>
            <div class="tech-stack-content">
              <div class="tech-category" v-for="category in techStack" :key="category.name">
                <h3>{{ category.name }}</h3>
                <ul>
                  <li v-for="tech in category.items" :key="tech">
                    <strong>{{ tech.split(':')[0] }}</strong>
                    <span v-if="tech.includes(':')">: {{ tech.split(':')[1] }}</span>
                  </li>
                </ul>
              </div>
            </div>
          </section>

          <!-- 目录结构 -->
          <section id="directory-structure" class="wiki-section">
            <h2>目录结构</h2>
            <p>项目的主要目录及其用途：</p>
            <el-table :data="directoryTable" border style="width: 100%; margin-top: 16px">
              <el-table-column prop="path" label="目录路径" width="300" />
              <el-table-column prop="purpose" label="用途说明" />
              <el-table-column prop="files" label="文件数" width="100" align="center" />
            </el-table>
          </section>

          <!-- 系统架构 -->
          <section id="system-architecture" class="wiki-section">
            <h2>系统架构</h2>
            <p>项目的整体架构设计和组件组织方式：</p>
            
            <h3>架构概览</h3>
            <div v-if="systemArchitecture?.three_tier_architecture" class="architecture-content" v-html="formatMarkdown(systemArchitecture.three_tier_architecture)"></div>
            
            <!-- Mermaid 架构图 -->
            <div v-if="systemArchitecture?.mermaid_architecture_diagram" class="mermaid-diagram">
              <h3>系统架构图</h3>
              <div 
                ref="architectureDiagramRef" 
                class="mermaid-container"
                v-html="renderMermaid(systemArchitecture.mermaid_architecture_diagram)"
              ></div>
            </div>
            
            <!-- 功能子系统表格 -->
            <h3>功能子系统</h3>
            <el-table 
              v-if="systemArchitecture?.functional_subsystems_table" 
              :data="systemArchitecture.functional_subsystems_table" 
              border 
              style="width: 100%; margin-top: 16px"
            >
              <el-table-column prop="subsystem_name" label="子系统名称" width="200" />
              <el-table-column prop="frontend_path" label="前端路径" width="200" />
              <el-table-column prop="backend_route" label="后端路由" width="200" />
              <el-table-column prop="service_files" label="服务文件">
                <template #default="{ row }">
                  <span v-for="(file, idx) in row.service_files" :key="idx">
                    {{ file }}<span v-if="idx < row.service_files.length - 1">, </span>
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="key_responsibilities" label="关键职责" min-width="300" />
            </el-table>
            
            <!-- Mermaid 数据流图 -->
            <div v-if="systemArchitecture?.mermaid_data_flow_diagram" class="mermaid-diagram">
              <h3>数据流图</h3>
              <div 
                ref="dataFlowDiagramRef" 
                class="mermaid-container"
                v-html="renderMermaid(systemArchitecture.mermaid_data_flow_diagram)"
              ></div>
            </div>
            
            <!-- Mermaid API 架构图 -->
            <div v-if="systemArchitecture?.mermaid_api_diagram" class="mermaid-diagram">
              <h3>API 架构图</h3>
              <div 
                ref="apiDiagramRef" 
                class="mermaid-container"
                v-html="renderMermaid(systemArchitecture.mermaid_api_diagram)"
              ></div>
            </div>
            
            <!-- 架构模式说明 -->
            <h3>架构模式</h3>
            <div v-if="systemArchitecture?.architectural_patterns" class="architecture-content" v-html="formatMarkdown(systemArchitecture.architectural_patterns)"></div>
            
            <!-- 存储系统表格 -->
            <h3>存储系统</h3>
            <el-table 
              v-if="systemArchitecture?.storage_systems_table" 
              :data="systemArchitecture.storage_systems_table" 
              border 
              style="width: 100%; margin-top: 16px"
            >
              <el-table-column prop="storage_system" label="存储系统" width="150" />
              <el-table-column prop="data_types" label="数据类型" width="200" />
              <el-table-column prop="access_pattern" label="访问模式" width="200" />
              <el-table-column prop="key_use_cases" label="关键用例" />
            </el-table>
            
            <!-- 关键架构决策 -->
            <h3>关键架构决策</h3>
            <div v-if="systemArchitecture?.key_architectural_decisions" class="decisions-list">
              <div 
                v-for="(decision, idx) in systemArchitecture.key_architectural_decisions" 
                :key="idx"
                class="decision-item"
              >
                <h4>{{ decision.decision }}</h4>
                <p><strong>理由：</strong>{{ decision.rationale }}</p>
                <p><strong>影响：</strong>{{ decision.impact }}</p>
              </div>
            </div>
            
            <!-- API 架构说明 -->
            <h3>API 架构</h3>
            <div v-if="systemArchitecture?.api_architecture" class="architecture-content" v-html="formatMarkdown(systemArchitecture.api_architecture)"></div>
            
            <!-- 可扩展性考虑 -->
            <h3>可扩展性考虑</h3>
            <div v-if="systemArchitecture?.scalability_considerations" class="architecture-content" v-html="formatMarkdown(systemArchitecture.scalability_considerations)"></div>
          </section>
          
          <!-- 架构建议 -->
          <section v-if="wikiContent?.architecture_recommendations" id="architecture-recommendations" class="wiki-section">
            <h2>架构建议</h2>
            
            <!-- 检测到的架构模式 -->
            <h3>检测到的架构模式</h3>
            <div v-if="wikiContent.architecture_recommendations.patterns_detected?.length > 0" class="patterns-list">
              <el-card 
                v-for="(pattern, idx) in wikiContent.architecture_recommendations.patterns_detected" 
                :key="idx"
                class="pattern-card"
                shadow="hover"
              >
                <h4>{{ pattern.pattern }}</h4>
                <el-tag :type="pattern.confidence === 'high' ? 'success' : 'warning'">
                  {{ pattern.confidence === 'high' ? '高置信度' : '中置信度' }}
                </el-tag>
                <p>{{ pattern.description }}</p>
              </el-card>
            </div>
            
            <!-- 潜在问题 -->
            <h3>潜在问题</h3>
            <div v-if="wikiContent.architecture_recommendations.potential_issues?.length > 0" class="issues-list">
              <el-alert
                v-for="(issue, idx) in wikiContent.architecture_recommendations.potential_issues"
                :key="idx"
                :title="issue.description"
                :type="issue.severity === 'high' ? 'error' : 'warning'"
                :closable="false"
                style="margin-bottom: 12px"
              >
                <template #default>
                  <p>{{ issue.description }}</p>
                  <div v-if="issue.details && issue.details.length > 0">
                    <ul>
                      <li v-for="(detail, dIdx) in issue.details" :key="dIdx">
                        {{ typeof detail === 'string' ? detail : JSON.stringify(detail) }}
                      </li>
                    </ul>
                  </div>
                </template>
              </el-alert>
            </div>
            
            <!-- 改进建议 -->
            <h3>改进建议</h3>
            <div v-if="wikiContent.architecture_recommendations.improvement_suggestions?.length > 0" class="suggestions-list">
              <el-card 
                v-for="(suggestion, idx) in wikiContent.architecture_recommendations.improvement_suggestions" 
                :key="idx"
                class="suggestion-card"
                shadow="hover"
              >
                <div class="suggestion-header">
                  <h4>建议 {{ idx + 1 }}</h4>
                  <el-tag :type="suggestion.priority === 'high' ? 'danger' : suggestion.priority === 'medium' ? 'warning' : 'info'">
                    {{ suggestion.priority === 'high' ? '高优先级' : suggestion.priority === 'medium' ? '中优先级' : '低优先级' }}
                  </el-tag>
                </div>
                <p><strong>建议：</strong>{{ suggestion.suggestion }}</p>
                <p><strong>影响：</strong>{{ suggestion.impact }}</p>
                <p><strong>实施：</strong>{{ suggestion.implementation }}</p>
              </el-card>
            </div>
          </section>
          
          <!-- 代码质量建议 -->
          <section v-if="wikiContent?.code_quality_recommendations" id="code-quality-recommendations" class="wiki-section">
            <h2>代码质量建议</h2>
            
            <!-- 代码异味 -->
            <h3>代码异味</h3>
            <div v-if="wikiContent.code_quality_recommendations.code_smells?.length > 0" class="smells-list">
              <el-table :data="paginatedCodeSmells" border>
                <el-table-column prop="type" label="类型" width="150" />
                <el-table-column prop="file" label="文件" width="300" />
                <el-table-column prop="symbol" label="符号" width="200">
                  <template #default="{ row }">
                    <span v-if="row.symbol">{{ row.symbol }}</span>
                    <span v-else style="color: #909399;">-</span>
                  </template>
                </el-table-column>
                <el-table-column prop="line" label="行号" width="100" align="center">
                  <template #default="{ row }">
                    <span v-if="row.line">{{ row.line }}</span>
                    <span v-else style="color: #909399;">-</span>
                  </template>
                </el-table-column>
                <el-table-column prop="severity" label="严重程度" width="120">
                  <template #default="{ row }">
                    <el-tag :type="row.severity === 'high' ? 'danger' : row.severity === '中' ? 'warning' : 'info'">
                      {{ row.severity === 'high' ? '高' : row.severity === '中' ? '中' : row.severity || '中' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="description" label="描述" />
              </el-table>
              <el-pagination
                v-model:current-page="codeSmellsPage"
                v-model:page-size="codeSmellsPageSize"
                :page-sizes="[10, 20, 50, 100]"
                :total="totalCodeSmells"
                layout="total, sizes, prev, pager, next, jumper"
                style="margin-top: 16px; justify-content: flex-end;"
                @size-change="handleCodeSmellsSizeChange"
                @current-change="handleCodeSmellsPageChange"
              />
            </div>
            
            <!-- 重构建议 -->
            <h3>重构建议</h3>
            <div v-if="wikiContent.code_quality_recommendations.refactoring_suggestions?.length > 0" class="refactoring-list">
              <el-card 
                v-for="(suggestion, idx) in wikiContent.code_quality_recommendations.refactoring_suggestions" 
                :key="idx"
                class="refactoring-card"
                shadow="hover"
              >
                <div class="suggestion-header">
                  <h4>重构建议 {{ idx + 1 }}</h4>
                  <el-tag :type="suggestion.priority === 'high' ? 'danger' : 'warning'">
                    {{ suggestion.priority === 'high' ? '高优先级' : '中优先级' }}
                  </el-tag>
                </div>
                <p><strong>建议：</strong>{{ suggestion.suggestion }}</p>
                <p><strong>受影响文件：</strong>{{ suggestion.affected_files.join(', ') }}</p>
                <p><strong>步骤：</strong>{{ suggestion.steps }}</p>
              </el-card>
            </div>
            
            <!-- 测试建议 -->
            <h3>测试建议</h3>
            <div v-if="wikiContent.code_quality_recommendations.test_suggestions?.length > 0" class="test-suggestions-list">
              <el-alert
                v-for="(suggestion, idx) in wikiContent.code_quality_recommendations.test_suggestions"
                :key="idx"
                :title="suggestion.description"
                type="info"
                :closable="false"
                style="margin-bottom: 12px"
              >
                <template #default>
                  <div v-if="suggestion.files && suggestion.files.length > 0">
                    <p>缺少测试的文件：</p>
                    <ul>
                      <li v-for="file in suggestion.files" :key="file">{{ file }}</li>
                    </ul>
                  </div>
                </template>
              </el-alert>
            </div>
          </section>

          <!-- 部署模型 -->
          <section id="deployment" class="wiki-section">
            <h2>部署模型</h2>
            <p>项目支持的部署方式：</p>
            <ul>
              <li v-for="deployment in deploymentModels" :key="deployment.name">
                <strong>{{ deployment.name }}:</strong> {{ deployment.description }}
              </li>
            </ul>
          </section>

          <!-- 组件关系 -->
          <section id="component-relationships" class="wiki-section">
            <h2>组件关系</h2>
            <p>主要组件之间的依赖和调用关系：</p>
            <div class="relationships-content">
              <div 
                v-for="relationship in componentRelationships" 
                :key="relationship.from"
                class="relationship-item"
              >
                <strong>{{ relationship.from }}</strong>
                <span class="arrow">→</span>
                <strong>{{ relationship.to }}</strong>
                <span class="description">: {{ relationship.description }}</span>
              </div>
            </div>
          </section>

          <!-- 快速开始 -->
          <section id="getting-started" class="wiki-section">
            <h2>快速开始</h2>
            <div class="getting-started-content">
              <!-- 快速开始总结 -->
              <div v-if="gettingStartedData?.quick_start_summary" class="quick-start-summary">
                <p>{{ gettingStartedData.quick_start_summary }}</p>
              </div>
              
              <!-- 前置要求 -->
              <h3>前置要求</h3>
              <ul v-if="gettingStartedData?.prerequisites && gettingStartedData.prerequisites.length > 0">
                <li v-for="(req, index) in gettingStartedData.prerequisites" :key="index">
                  <strong>{{ req.item }}</strong>
                  <span v-if="req.description">: {{ req.description }}</span>
                </li>
              </ul>
              <ul v-else>
                <li v-for="(req, index) in prerequisites" :key="index">{{ req }}</li>
              </ul>
              
              <!-- 安装步骤 -->
              <h3 v-if="gettingStartedData?.installation_steps && gettingStartedData.installation_steps.length > 0">安装步骤</h3>
              <ol v-if="gettingStartedData?.installation_steps && gettingStartedData.installation_steps.length > 0" class="installation-steps">
                <li v-for="(step, index) in gettingStartedData.installation_steps" :key="index">
                  <strong>{{ step.step }}</strong>
                  <span v-if="step.description">: {{ step.description }}</span>
                </li>
              </ol>
              
              <!-- 运行项目（如果没有安装步骤，显示运行指令） -->
              <h3>运行项目</h3>
              <div v-if="gettingStartedData?.installation_steps && gettingStartedData.installation_steps.length > 0" class="run-project-info">
                <p>按照上述安装步骤完成安装后，根据项目类型运行相应的启动命令。</p>
                <pre v-if="runInstructions" class="code-block"><code>{{ runInstructions }}</code></pre>
              </div>
              <pre v-else class="code-block"><code>{{ runInstructions }}</code></pre>
              
              <!-- 关键端点（如果有 API） -->
              <div v-if="gettingStartedData?.key_endpoints && gettingStartedData.key_endpoints.length > 0" class="key-endpoints">
                <h3>关键 API 端点</h3>
                <table class="endpoints-table">
                  <thead>
                    <tr>
                      <th>方法</th>
                      <th>端点</th>
                      <th>说明</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(endpoint, index) in gettingStartedData.key_endpoints" :key="index">
                      <td><el-tag :type="getMethodTagType(endpoint.method)">{{ endpoint.method }}</el-tag></td>
                      <td><code>{{ endpoint.endpoint }}</code></td>
                      <td>{{ endpoint.description }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </section>

          <!-- AI 聊天 -->
          <div class="ai-chat-section">
            <div class="chat-header">
              <span>询问 AI 关于 {{ repository?.repo_name }}</span>
            </div>
            
            <!-- 聊天历史 -->
            <div v-if="chatHistory.length > 0" class="chat-history">
              <div 
                v-for="(item, index) in chatHistory" 
                :key="index"
                class="chat-message"
              >
                <div class="message-question">
                  <strong>问:</strong> {{ item.question }}
                </div>
                <div class="message-answer" v-html="formatMarkdown(item.answer)"></div>
              </div>
            </div>
            
            <div class="chat-input-wrapper">
              <el-input
                v-model="chatQuestion"
                placeholder="询问 AI 关于此代码库..."
                @keyup.enter="handleChatSubmit"
                :disabled="chatLoading"
              >
                <template #append>
                  <el-button @click="handleChatSubmit" :loading="chatLoading">
                    发送
                  </el-button>
                </template>
              </el-input>
            </div>
          </div>
        </div>
      </main>

      <!-- 右侧目录 -->
      <aside class="wiki-toc">
        <div class="toc-header">
          <el-button size="small" @click="refreshWiki">刷新 Wiki</el-button>
        </div>
        <div class="toc-content">
          <div class="toc-title">本页目录</div>
          <ul class="toc-list">
            <li v-for="section in tocSections" :key="section.id">
              <a 
                :class="{ active: activeSection === section.id }"
                @click="scrollToSection(section.id)"
              >
                {{ section.label }}
              </a>
            </li>
          </ul>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from 'vue'
// 不再需要 Search 图标
import { ElMessage } from 'element-plus'
import * as codeRepositoryApi from '@/api/modules/code-repository'
import type { CodeRepository, CodeStructure, WikiContent } from '@/api/modules/code-repository'

interface Props {
  repository?: CodeRepository
  codeStructure?: CodeStructure
  repoId: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'viewFile', file: any): void
  (e: 'refresh'): void
}>()

// 状态
const showRelevantFiles = ref(false)
const activeSection = ref('overview')
const chatQuestion = ref('')
const chatLoading = ref(false)
const chatHistory = ref<Array<{ question: string; answer: string }>>([])

// 代码异味分页
const codeSmellsPage = ref(1)
const codeSmellsPageSize = ref(20)

// Mermaid 图表容器 refs
const architectureDiagramRef = ref<HTMLElement | null>(null)
const dataFlowDiagramRef = ref<HTMLElement | null>(null)
const apiDiagramRef = ref<HTMLElement | null>(null)
const lastIndexed = computed(() => {
  if (!props.repository?.updated_at) return '未知'
  const date = new Date(props.repository.updated_at)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  const hours = Math.floor(diff / (1000 * 60 * 60))
  const minutes = Math.floor(diff / (1000 * 60))
  
  if (days > 0) return `${days} 天前`
  if (hours > 0) return `${hours} 小时前`
  if (minutes > 0) return `${minutes} 分钟前`
  return '刚刚'
})

// 导航项（更丰富的层级结构，类似 DeepWiki）
const navigationItems = computed(() => {
  const items: Array<{ id: string; label: string; level: number; children?: Array<{ id: string; label: string; level: number }> }> = [
    { id: 'overview', label: '概览', level: 0 },
    { 
      id: 'architecture', 
      label: '架构', 
      level: 0,
      children: [
        { id: 'components', label: '核心组件', level: 1 },
        { id: 'system-architecture', label: '系统架构', level: 1 },
        { id: 'directory-structure', label: '目录结构', level: 1 },
        { id: 'tech-stack', label: '技术栈', level: 1 },
        { id: 'component-relationships', label: '组件关系', level: 1 }
      ]
    },
    { id: 'deployment', label: '部署模型', level: 0 },
    { id: 'getting-started', label: '快速开始', level: 0 }
  ]
  
  // 如果有架构建议，添加到导航
  if (wikiContent.value?.architecture_recommendations) {
    items.push({ id: 'architecture-recommendations', label: '架构建议', level: 0 })
  }
  
  // 如果有代码质量建议，添加到导航
  if (wikiContent.value?.code_quality_recommendations) {
    items.push({ id: 'code-quality-recommendations', label: '代码质量建议', level: 0 })
  }
  
  return items
})

// 内部链接
const internalLinks = computed(() => [
  { id: 'components', label: '核心组件' },
  { id: 'system-architecture', label: '系统架构' },
  { id: 'tech-stack', label: '技术栈' },
  { id: 'deployment', label: '部署模型' },
  { id: 'getting-started', label: '快速开始' }
])

// What is Project
const whatIsProject = computed(() => {
  return wikiContent.value?.what_is_project || ''
})

// Core Value Propositions
const valuePropositions = computed(() => {
  return wikiContent.value?.value_propositions || []
})

// Key Features
const keyFeatures = computed(() => {
  return wikiContent.value?.key_features || []
})

// 目录导航（与左侧导航同步）
const tocSections = computed(() => {
  const sections = [
    { id: 'overview', label: '概览' },
    { id: 'what-is', label: (props.repository?.repo_name || '项目') + ' 是什么' },
    { id: 'core-value', label: '核心价值主张' },
    { id: 'key-features', label: '主要特性' },
    { id: 'components', label: '核心组件' },
    { id: 'system-architecture', label: '系统架构' },
    { id: 'tech-stack', label: '技术栈' },
    { id: 'directory-structure', label: '目录结构' },
    { id: 'deployment', label: '部署模型' },
    { id: 'component-relationships', label: '组件关系' },
    { id: 'getting-started', label: '快速开始' }
  ]
  
  // 如果有架构建议，添加到导航
  if (wikiContent.value?.architecture_recommendations) {
    sections.push({ id: 'architecture-recommendations', label: '架构建议' })
  }
  
  // 如果有代码质量建议，添加到导航
  if (wikiContent.value?.code_quality_recommendations) {
    sections.push({ id: 'code-quality-recommendations', label: '代码质量建议' })
  }
  
  return sections
})

// 相关文件（优先使用 Wiki 中的关键文件列表）
const relevantFiles = computed(() => {
  // 优先使用 Wiki 中的关键文件列表（按重要性排序）
  if (wikiContent.value?.key_files && wikiContent.value.key_files.length > 0) {
    return wikiContent.value.key_files
      .slice(0, 20)  // 最多显示 20 个
      .map(f => ({ 
        path: f.path,
        type: f.type,
        importance: f.importance
      }))
  }
  
  // 回退到使用代码结构中的文件
  if (!props.codeStructure?.files) return []
  return props.codeStructure.files
    .sort((a, b) => (b.lines || 0) - (a.lines || 0))
    .slice(0, 10)
    .map(f => ({ path: f.file_path }))
})

// 代码异味分页计算属性
const totalCodeSmells = computed(() => {
  return wikiContent.value?.code_quality_recommendations?.code_smells?.length || 0
})

const paginatedCodeSmells = computed(() => {
  const smells = wikiContent.value?.code_quality_recommendations?.code_smells || []
  const start = (codeSmellsPage.value - 1) * codeSmellsPageSize.value
  const end = start + codeSmellsPageSize.value
  return smells.slice(start, end)
})

const handleCodeSmellsSizeChange = (val: number) => {
  codeSmellsPageSize.value = val
  codeSmellsPage.value = 1 // 重置到第一页
}

const handleCodeSmellsPageChange = (val: number) => {
  codeSmellsPage.value = val
}

// Wiki 内容（优先从缓存获取）
const wikiContent = ref<WikiContent | null>(null)
const wikiLoading = ref(false)

const loadWikiContent = async (forceRefresh = false) => {
  if (wikiContent.value && !forceRefresh) return // 已加载且不强制刷新
  
  wikiLoading.value = true
  try {
    const res = await codeRepositoryApi.getWikiContent(props.repoId, forceRefresh)
    
    if (res.data) {
      // 检查是否是 WikiContent 类型（有 project_overview 字段）
      if ('project_overview' in res.data) {
        // 直接返回缓存的内容
        wikiContent.value = res.data as WikiContent
      } else if ('status' in res.data && res.data.status === 'processing') {
        // 任务正在生成中，等待后重试（只重试一次）
        ElMessage.info('Wiki 内容正在生成中，请稍候...')
        await new Promise(resolve => setTimeout(resolve, 3000)) // 等待3秒
        // 再次调用，此时应该已经有缓存了
        const retryRes = await codeRepositoryApi.getWikiContent(props.repoId, false)
        if (retryRes.data && 'project_overview' in retryRes.data) {
          wikiContent.value = retryRes.data as WikiContent
        } else {
          ElMessage.warning('Wiki 内容生成中，请稍后刷新页面')
        }
      } else {
        throw new Error('API 返回数据格式错误')
      }
    } else {
      throw new Error('API 返回数据为空')
    }
  } catch (error: any) {
    console.error('加载 Wiki 内容失败:', error)
    ElMessage.error('加载 Wiki 内容失败: ' + (error.message || '未知错误'))
    throw error // 直接抛出错误，不降级
  } finally {
    wikiLoading.value = false
  }
}

// 项目概述
const projectOverview = computed(() => {
  return wikiContent.value?.project_overview || ''
})

// 组件表格（更智能的分析）
const componentsTable = computed(() => {
  if (!props.codeStructure?.files) return []
  
  // 按目录分组（支持多级目录）
  const dirMap = new Map<string, any>()
  props.codeStructure.files.forEach(file => {
    const parts = file.file_path.split(/[/\\]/)
    // 取前两级目录作为组件
    const key = parts.length > 1 ? `${parts[0]}/${parts[1]}` : parts[0] || 'root'
    const displayName = parts.length > 1 ? `${parts[0]}/${parts[1]}` : parts[0] || 'root'
    
    if (!dirMap.has(key)) {
      dirMap.set(key, { 
        name: displayName, 
        files: 0, 
        lines: 0, 
        purpose: '',
        symbols: 0,
        languages: new Set<string>()
      })
    }
    const item = dirMap.get(key)!
    item.files++
    item.lines += file.lines || 0
    if (file.symbols) item.symbols += file.symbols.length
    if (file.language) item.languages.add(file.language)
  })
  
  // 生成组件说明（基于实际代码分析）
  const components = Array.from(dirMap.values()).map(comp => {
    comp.purpose = analyzeComponentPurpose(comp.name, comp)
    comp.languages = Array.from(comp.languages).join(', ')
    return comp
  })
  
  // 只显示前 15 个最重要的组件
  return components.sort((a, b) => b.lines - a.lines).slice(0, 15)
})

function analyzeComponentPurpose(name: string, stats: any): string {
  const nameLower = name.toLowerCase()
  
  // 基于路径和统计信息智能判断
  if (nameLower.includes('component') || nameLower.includes('ui')) {
    return 'UI 组件库，提供可复用的界面组件'
  }
  if (nameLower.includes('service') || nameLower.includes('api')) {
    return '业务服务层，处理核心业务逻辑和 API 接口'
  }
  if (nameLower.includes('util') || nameLower.includes('helper')) {
    return '工具函数库，提供通用的辅助功能'
  }
  if (nameLower.includes('config') || nameLower.includes('setting')) {
    return '配置管理，处理应用配置和参数'
  }
  if (nameLower.includes('model') || nameLower.includes('entity')) {
    return '数据模型层，定义数据结构和实体'
  }
  if (nameLower.includes('test') || nameLower.includes('spec')) {
    return '测试代码，包含单元测试和集成测试'
  }
  if (nameLower.includes('router') || nameLower.includes('route')) {
    return '路由配置，定义应用的路由规则'
  }
  if (nameLower.includes('store') || nameLower.includes('state')) {
    return '状态管理，管理应用的全局状态'
  }
  if (nameLower.includes('view') || nameLower.includes('page')) {
    return '页面视图，定义应用的页面组件'
  }
  if (nameLower.includes('middleware')) {
    return '中间件，处理请求和响应的中间逻辑'
  }
  
  // 基于统计信息推断
  if (stats.symbols > 50) {
    return '核心业务模块，包含大量业务逻辑'
  }
  if (stats.files > 20) {
    return '大型模块，包含多个子模块和功能'
  }
  
  return getComponentPurpose(name.split('/')[0] || name)
}

// 技术栈
const techStack = computed(() => {
  if (!props.codeStructure?.files) return []
  
  const languages = new Set<string>()
  props.codeStructure.files.forEach(file => {
    if (file.language) languages.add(file.language)
  })
  
  return [
    {
      name: '编程语言',
      items: Array.from(languages)
    },
    {
      name: '框架和工具',
      items: detectFrameworks()
    }
  ]
})

// 目录表格
const directoryTable = computed(() => {
  if (!props.codeStructure?.files) return []
  
  const dirMap = new Map<string, any>()
  props.codeStructure.files.forEach(file => {
    const parts = file.file_path.split(/[/\\]/)
    if (parts.length > 1) {
      const dir = parts[0]
      if (!dirMap.has(dir)) {
        dirMap.set(dir, { path: dir, files: 0, purpose: getDirectoryPurpose(dir) })
      }
      dirMap.get(dir)!.files++
    }
  })
  
  return Array.from(dirMap.values()).sort((a, b) => b.files - a.files)
})

// 系统架构（从 Wiki 内容获取）
const systemArchitecture = computed(() => {
  return wikiContent.value?.system_architecture
})

// 架构概述
const architectureOverview = computed(() => {
  if (systemArchitecture.value?.three_tier_architecture) {
    return systemArchitecture.value.three_tier_architecture
  }
  
  if (!props.codeStructure) return ''
  
  const stats = props.codeStructure.statistics
  const hasFrontend = componentsTable.value.some(c => 
    c.name.toLowerCase().includes('frontend') || 
    c.name.toLowerCase().includes('ui') ||
    c.name.toLowerCase().includes('client')
  )
  const hasBackend = componentsTable.value.some(c => 
    c.name.toLowerCase().includes('backend') || 
    c.name.toLowerCase().includes('server') ||
    c.name.toLowerCase().includes('api')
  )
  
  let overview = `${props.repository?.repo_name || '项目'} 采用`
  if (hasFrontend && hasBackend) {
    overview += '前后端分离架构'
  } else if (hasFrontend) {
    overview += '前端架构'
  } else if (hasBackend) {
    overview += '后端架构'
  } else {
    overview += '模块化架构'
  }
  
  overview += `，包含 ${stats?.total_files || 0} 个文件，总计 ${stats?.total_lines || 0} 行代码。`
  overview += `项目主要使用 ${Object.keys(stats?.languages || {}).join('、')} 等编程语言。`
  
  return overview
})

// 服务表格
const servicesTable = computed(() => {
  if (!props.codeStructure?.files) return []
  
  const services: Array<{ name: string; purpose: string; components: string }> = []
  const components = componentsTable.value
  
  // 识别主要服务
  components.forEach(comp => {
    const nameLower = comp.name.toLowerCase()
    if (nameLower.includes('service') || nameLower.includes('api')) {
      services.push({
        name: comp.name,
        purpose: comp.purpose,
        components: `${comp.files} 个文件`
      })
    }
  })
  
  // 如果没有找到服务，基于组件生成
  if (services.length === 0 && components.length > 0) {
    return components.slice(0, 5).map(comp => ({
      name: comp.name,
      purpose: comp.purpose,
      components: `${comp.files} 个文件`
    }))
  }
  
  return services
})

// 部署模型
const deploymentModels = computed(() => {
  const models = []
  
  // 检测部署方式
  if (props.codeStructure?.files) {
    const filePaths = props.codeStructure.files.map(f => f.file_path.toLowerCase())
    
    if (filePaths.some(p => p.includes('docker') || p.includes('dockerfile'))) {
      models.push({
        name: 'Docker 部署',
        description: '支持通过 Docker 容器化部署，包含 Dockerfile 和 docker-compose 配置'
      })
    }
    
    if (filePaths.some(p => p.includes('package.json') || p.includes('requirements.txt'))) {
      models.push({
        name: '本地开发',
        description: '支持本地开发环境，通过包管理器安装依赖并运行'
      })
    }
    
    if (filePaths.some(p => p.includes('k8s') || p.includes('kubernetes'))) {
      models.push({
        name: 'Kubernetes 部署',
        description: '支持 Kubernetes 集群部署'
      })
    }
  }
  
  // 默认部署方式
  if (models.length === 0) {
    models.push({
      name: '标准部署',
      description: '通过源代码直接部署和运行'
    })
  }
  
  return models
})

// 组件关系
const componentRelationships = computed(() => {
  if (!props.codeStructure?.files) return []
  
  const relationships: Array<{ from: string; to: string; description: string }> = []
  const components = componentsTable.value.slice(0, 8)
  
  // 基于目录结构推断关系
  for (let i = 0; i < components.length - 1; i++) {
    const from = components[i].name
    const to = components[i + 1].name
    
    // 推断关系类型
    let description = '数据传递'
    if (from.toLowerCase().includes('api') && to.toLowerCase().includes('service')) {
      description = 'API 调用服务'
    } else if (from.toLowerCase().includes('component') && to.toLowerCase().includes('service')) {
      description = '组件调用服务'
    } else if (from.toLowerCase().includes('service') && to.toLowerCase().includes('model')) {
      description = '服务访问数据模型'
    }
    
    relationships.push({ from, to, description })
  }
  
  return relationships.slice(0, 6) // 只显示前 6 个关系
})

// 前置要求
// 获取快速开始数据（优先使用 LLM 生成的数据）
const gettingStartedData = computed(() => {
  return props.wikiContent?.getting_started
})

const prerequisites = computed(() => {
  // 如果 LLM 生成了数据，优先使用
  if (gettingStartedData.value?.prerequisites && gettingStartedData.value.prerequisites.length > 0) {
    return gettingStartedData.value.prerequisites.map(req => 
      req.description ? `${req.item}: ${req.description}` : req.item
    )
  }
  
  // 否则使用计算的值
  const reqs: string[] = []
  
  if (!props.codeStructure?.files) {
    reqs.push('Node.js 16+')
    reqs.push('Python 3.9+')
    return reqs
  }
  
  const filePaths = props.codeStructure.files.map(f => f.file_path.toLowerCase())
  const languages = new Set(props.codeStructure.files.map(f => f.language).filter(Boolean))
  
  if (languages.has('javascript') || languages.has('typescript')) {
    reqs.push('Node.js 16+')
  }
  if (languages.has('python')) {
    reqs.push('Python 3.9+')
  }
  if (filePaths.some(p => p.includes('package.json'))) {
    reqs.push('npm 或 yarn')
  }
  if (filePaths.some(p => p.includes('requirements.txt'))) {
    reqs.push('pip')
  }
  
  if (reqs.length === 0) {
    reqs.push('根据项目类型安装相应的运行时环境')
  }
  
  return reqs
})

// 获取方法标签类型
const getMethodTagType = (method: string) => {
  const methodUpper = method.toUpperCase()
  if (methodUpper === 'GET') return 'success'
  if (methodUpper === 'POST') return 'primary'
  if (methodUpper === 'PUT' || methodUpper === 'PATCH') return 'warning'
  if (methodUpper === 'DELETE') return 'danger'
  return 'info'
}

// 运行指令
const runInstructions = computed(() => {
  if (!props.codeStructure?.files) {
    return '# 安装依赖\nnpm install\n# 或\npip install -r requirements.txt\n\n# 运行项目\nnpm start\n# 或\npython main.py'
  }
  
  const filePaths = props.codeStructure.files.map(f => f.file_path.toLowerCase())
  
  if (filePaths.some(p => p.includes('package.json'))) {
    return '# 安装依赖\nnpm install\n\n# 开发模式\nnpm run dev\n\n# 生产构建\nnpm run build'
  }
  
  if (filePaths.some(p => p.includes('requirements.txt'))) {
    return '# 安装依赖\npip install -r requirements.txt\n\n# 运行项目\npython main.py\n# 或\nuvicorn app:app --reload'
  }
  
  return '# 根据项目类型运行相应的启动命令'
})

// 工具函数
function getComponentPurpose(name: string): string {
  const purposes: Record<string, string> = {
    'src': '源代码目录',
    'app': '应用主目录',
    'components': 'UI 组件',
    'services': '业务服务',
    'api': 'API 接口',
    'utils': '工具函数',
    'config': '配置文件',
    'tests': '测试文件'
  }
  return purposes[name.toLowerCase()] || '项目组件'
}

function getDirectoryPurpose(name: string): string {
  const purposes: Record<string, string> = {
    'src': '源代码目录',
    'app': '应用主目录',
    'components': 'UI 组件目录',
    'services': '业务服务目录',
    'api': 'API 接口目录',
    'utils': '工具函数目录',
    'config': '配置文件目录',
    'tests': '测试文件目录',
    'public': '静态资源目录',
    'assets': '资源文件目录'
  }
  return purposes[name.toLowerCase()] || '项目目录'
}

function detectFrameworks(): string[] {
  const frameworks: string[] = []
  if (!props.codeStructure?.files) return frameworks
  
  const filePaths = props.codeStructure.files.map(f => f.file_path.toLowerCase())
  
  if (filePaths.some(p => p.includes('vue'))) frameworks.push('Vue.js')
  if (filePaths.some(p => p.includes('react'))) frameworks.push('React')
  if (filePaths.some(p => p.includes('angular'))) frameworks.push('Angular')
  if (filePaths.some(p => p.includes('fastapi') || p.includes('flask'))) frameworks.push('FastAPI/Flask')
  if (filePaths.some(p => p.includes('express'))) frameworks.push('Express.js')
  if (filePaths.some(p => p.includes('next'))) frameworks.push('Next.js')
  if (filePaths.some(p => p.includes('nuxt'))) frameworks.push('Nuxt.js')
  
  return frameworks
}

function getComplexityType(complexity?: number): string {
  if (!complexity) return 'info'
  if (complexity <= 10) return 'success'
  if (complexity <= 20) return 'warning'
  return 'danger'
}

function scrollToSection(id: string) {
  activeSection.value = id
  nextTick(() => {
    const element = document.getElementById(id)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  })
}

function viewFile(file: any) {
  const fullFile = props.codeStructure?.files?.find(f => f.file_path === file.path)
  if (fullFile) {
    emit('viewFile', fullFile)
  }
}

function viewFileDetail(file: any) {
  emit('viewFile', file)
}

async function refreshWiki() {
  try {
    ElMessage.info('正在刷新 Wiki...')
    
    // 强制刷新，重新生成 Wiki 内容
    wikiContent.value = null
    await loadWikiContent(true) // forceRefresh = true
    
    // 触发父组件更新代码结构
    emit('refresh')
    ElMessage.success('Wiki 已刷新')
  } catch (error: any) {
    // 错误已在 loadWikiContent 中处理
    console.error('刷新 Wiki 失败:', error)
  }
}

async function handleChatSubmit() {
  if (!chatQuestion.value.trim()) return
  
  const question = chatQuestion.value
  chatQuestion.value = ''
  chatLoading.value = true
  
  try {
    const res = await codeRepositoryApi.codeQA({
      repository_id: props.repoId,
      question
    })
    
    if (res.data?.answer) {
      chatHistory.value.push({
        question,
        answer: res.data.answer
      })
      
      // 滚动到底部
      nextTick(() => {
        const chatSection = document.querySelector('.ai-chat-section')
        if (chatSection) {
          chatSection.scrollIntoView({ behavior: 'smooth', block: 'end' })
        }
      })
    } else {
      ElMessage.warning('AI 未返回答案')
    }
  } catch (error: any) {
    ElMessage.error('AI 问答失败')
    console.error('AI 问答失败:', error)
  } finally {
    chatLoading.value = false
  }
}

function formatMarkdown(text: string): string {
  if (!text) return ''
  
  return text
    .replace(/\n/g, '<br/>')
    .replace(/## (.*)/g, '<h3>$1</h3>')
    .replace(/### (.*)/g, '<h4>$1</h4>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
}

// 渲染 Mermaid 图表（返回占位符，实际渲染在 renderAllMermaidDiagrams 中完成）
function renderMermaid(mermaidCode: string): string {
  if (!mermaidCode) return ''
  
  // 提取 Mermaid 代码（移除 ```mermaid 和 ```）
  let code = mermaidCode.trim()
  if (code.startsWith('```mermaid')) {
    code = code.substring(10)
  } else if (code.startsWith('```')) {
    code = code.substring(3)
  }
  if (code.endsWith('```')) {
    code = code.substring(0, code.length - 3)
  }
  code = code.trim()
  
  // 返回占位符，实际渲染在 renderAllMermaidDiagrams 中完成
  return ''
}

// 渲染所有 Mermaid 图表
async function renderAllMermaidDiagrams() {
  // 动态导入 Mermaid
  let mermaidModule: any = null
  try {
    mermaidModule = await import('mermaid')
    const mermaid = mermaidModule.default
    mermaid.initialize({ 
      startOnLoad: false,
      theme: 'default',
      securityLevel: 'loose'
    })
  } catch (error) {
    console.warn('Mermaid 未安装，图表渲染功能将不可用。请运行: npm install mermaid')
    // 显示代码块作为降级方案
    if (architectureDiagramRef.value && systemArchitecture.value?.mermaid_architecture_diagram) {
      architectureDiagramRef.value.innerHTML = `<pre class="mermaid-code">${systemArchitecture.value.mermaid_architecture_diagram}</pre>`
    }
    if (dataFlowDiagramRef.value && systemArchitecture.value?.mermaid_data_flow_diagram) {
      dataFlowDiagramRef.value.innerHTML = `<pre class="mermaid-code">${systemArchitecture.value.mermaid_data_flow_diagram}</pre>`
    }
    if (apiDiagramRef.value && systemArchitecture.value?.mermaid_api_diagram) {
      apiDiagramRef.value.innerHTML = `<pre class="mermaid-code">${systemArchitecture.value.mermaid_api_diagram}</pre>`
    }
    return
  }
  
  if (!mermaidModule) return
  const mermaid = mermaidModule.default
  
  await nextTick()
  
  // 渲染架构图
  if (architectureDiagramRef.value && systemArchitecture.value?.mermaid_architecture_diagram) {
    const code = systemArchitecture.value.mermaid_architecture_diagram
      .replace(/```mermaid\n?/g, '')
      .replace(/```\n?/g, '')
      .trim()
    try {
      const id = `mermaid-arch-${Date.now()}`
      const { svg } = await mermaid.render(id, code)
      if (architectureDiagramRef.value) {
        architectureDiagramRef.value.innerHTML = svg
      }
    } catch (error) {
      console.error('渲染架构图失败:', error)
      if (architectureDiagramRef.value) {
        architectureDiagramRef.value.innerHTML = `<pre class="mermaid-code">${code}</pre>`
      }
    }
  }
  
  // 渲染数据流图
  if (dataFlowDiagramRef.value && systemArchitecture.value?.mermaid_data_flow_diagram) {
    const code = systemArchitecture.value.mermaid_data_flow_diagram
      .replace(/```mermaid\n?/g, '')
      .replace(/```\n?/g, '')
      .trim()
    try {
      const id = `mermaid-flow-${Date.now()}`
      const { svg } = await mermaid.render(id, code)
      if (dataFlowDiagramRef.value) {
        dataFlowDiagramRef.value.innerHTML = svg
      }
    } catch (error) {
      console.error('渲染数据流图失败:', error)
      if (dataFlowDiagramRef.value) {
        dataFlowDiagramRef.value.innerHTML = `<pre class="mermaid-code">${code}</pre>`
      }
    }
  }
  
  // 渲染 API 架构图
  if (apiDiagramRef.value && systemArchitecture.value?.mermaid_api_diagram) {
    const code = systemArchitecture.value.mermaid_api_diagram
      .replace(/```mermaid\n?/g, '')
      .replace(/```\n?/g, '')
      .trim()
    try {
      const id = `mermaid-api-${Date.now()}`
      const { svg } = await mermaid.render(id, code)
      if (apiDiagramRef.value) {
        apiDiagramRef.value.innerHTML = svg
      }
    } catch (error) {
      console.error('渲染 API 架构图失败:', error)
      if (apiDiagramRef.value) {
        apiDiagramRef.value.innerHTML = `<pre class="mermaid-code">${code}</pre>`
      }
    }
  }
}

// 监听 Wiki 内容变化，渲染 Mermaid 图表
watch(() => wikiContent.value?.system_architecture, () => {
  if (wikiContent.value?.system_architecture) {
    renderAllMermaidDiagrams()
  }
}, { deep: true })

// 监听代码异味数据变化，重置分页
watch(() => wikiContent.value?.code_quality_recommendations?.code_smells, () => {
  codeSmellsPage.value = 1
}, { deep: true })

// 监听滚动，更新活动章节
onMounted(() => {
  // 加载 Wiki 内容
  loadWikiContent()
  
  // 设置滚动监听
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          activeSection.value = entry.target.id
        }
      })
    },
    { rootMargin: '-20% 0px -70% 0px' }
  )
  
  nextTick(() => {
    tocSections.value.forEach(section => {
      const element = document.getElementById(section.id)
      if (element) observer.observe(element)
    })
    
    // 渲染 Mermaid 图表
    if (wikiContent.value?.system_architecture) {
      renderAllMermaidDiagrams()
    }
  })
})
</script>

<style scoped lang="scss">
.code-structure-wiki {
  width: 100%;
  height: 100%;
  background: #fff;
}

.wiki-container {
  display: flex;
  height: 100%;
  max-width: 1600px;
  margin: 0 auto;
}

// 左侧导航栏
.wiki-sidebar {
  width: 250px;
  border-right: 1px solid #e5e7eb;
  background: #f9fafb;
  overflow-y: auto;
  padding: 20px 0;
  
  .sidebar-header {
    padding: 0 20px 16px;
    border-bottom: 1px solid #e5e7eb;
    margin-bottom: 16px;
    
    .last-indexed {
      font-size: 12px;
      color: #6b7280;
      display: flex;
      flex-direction: column;
      gap: 4px;
      
      .commit-hash {
        font-family: monospace;
        font-size: 11px;
        color: #9ca3af;
      }
    }
  }
  
  .sidebar-nav {
    .nav-item {
      padding: 8px 20px;
      cursor: pointer;
      font-size: 14px;
      color: #374151;
      transition: all 0.2s;
      
      &:hover {
        background: #f3f4f6;
        color: #111827;
      }
      
      &.active {
        background: #eff6ff;
        color: #2563eb;
        font-weight: 500;
      }
      
      .nav-item-main {
        display: flex;
        align-items: center;
      }
    }
  }
}

// 中间主内容
.wiki-main {
  flex: 1;
  overflow-y: auto;
  padding: 40px 60px;
  background: #fff;
  
  .wiki-content {
    max-width: 900px;
    margin: 0 auto;
  }
  
  .wiki-title {
    font-size: 36px;
    font-weight: 700;
    margin-bottom: 24px;
    color: #111827;
  }
  
  .relevant-files-section {
    margin-bottom: 32px;
    
    .expandable-header {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      color: #2563eb;
      font-size: 14px;
      margin-bottom: 12px;
      
      span:first-child {
        transition: transform 0.2s;
        &.expanded {
          transform: rotate(90deg);
        }
      }
    }
    
    .relevant-files-list {
      padding-left: 20px;
      
      .file-item {
        padding: 4px 0;
        color: #2563eb;
        cursor: pointer;
        font-size: 13px;
        font-family: monospace;
        
        &:hover {
          text-decoration: underline;
        }
      }
    }
  }
  
  .intro-section {
    margin-bottom: 48px;
    
    p {
      font-size: 16px;
      line-height: 1.7;
      color: #374151;
      margin-bottom: 16px;
    }
    
    .internal-links {
      list-style: none;
      padding: 0;
      
      li {
        margin-bottom: 8px;
        
        a {
          color: #2563eb;
          cursor: pointer;
          text-decoration: none;
          
          &:hover {
            text-decoration: underline;
          }
        }
      }
    }
  }
  
  .wiki-section {
    margin-bottom: 64px;
    
    h2 {
      font-size: 28px;
      font-weight: 600;
      margin-bottom: 16px;
      color: #111827;
      padding-top: 16px;
      border-top: 1px solid #e5e7eb;
    }
    
    h3 {
      font-size: 20px;
      font-weight: 600;
      margin: 24px 0 12px;
      color: #374151;
    }
    
    p {
      font-size: 16px;
      line-height: 1.7;
      color: #374151;
      margin-bottom: 16px;
    }
    
    ul {
      padding-left: 24px;
      
      li {
        margin-bottom: 8px;
        line-height: 1.6;
        color: #374151;
      }
    }
  }
  
  .tech-stack-content {
    .tech-category {
      margin-bottom: 32px;
    }
  }
  
  .relationships-content {
    margin-top: 16px;
    
    .relationship-item {
      margin-bottom: 12px;
      padding: 12px;
      background: #f9fafb;
      border-radius: 6px;
      font-size: 14px;
      display: flex;
      align-items: center;
      
      strong {
        color: #111827;
      }
      
      .arrow {
        margin: 0 12px;
        color: #6b7280;
        font-size: 16px;
      }
      
      .description {
        color: #6b7280;
        margin-left: 8px;
      }
    }
  }
  
  .getting-started-content {
    h3 {
      font-size: 18px;
      margin: 24px 0 12px;
      color: #374151;
    }
    
    .quick-start-summary {
      background: #f0f9ff;
      border-left: 4px solid #3b82f6;
      padding: 16px 20px;
      margin-bottom: 24px;
      border-radius: 4px;
      
      p {
        margin: 0;
        color: #1e40af;
        line-height: 1.7;
      }
    }
    
    ul {
      margin-bottom: 24px;
      
      li {
        strong {
          color: #111827;
          font-weight: 600;
        }
      }
    }
    
    .installation-steps {
      margin-bottom: 24px;
      padding-left: 24px;
      
      li {
        margin-bottom: 12px;
        line-height: 1.7;
        
        strong {
          color: #111827;
          font-weight: 600;
        }
      }
    }
    
    .run-project-info {
      margin-top: 16px;
      
      p {
        margin-bottom: 12px;
        color: #6b7280;
      }
    }
    
    .key-endpoints {
      margin-top: 32px;
      
      .endpoints-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 12px;
        
        thead {
          background: #f9fafb;
          
          th {
            padding: 12px 16px;
            text-align: left;
            font-weight: 600;
            color: #374151;
            border-bottom: 2px solid #e5e7eb;
            font-size: 14px;
          }
        }
        
        tbody {
          tr {
            border-bottom: 1px solid #e5e7eb;
            
            &:hover {
              background: #f9fafb;
            }
            
            td {
              padding: 12px 16px;
              font-size: 14px;
              color: #374151;
              
              code {
                background: #f3f4f6;
                padding: 4px 8px;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 13px;
                color: #1f2937;
              }
            }
          }
        }
      }
    }
    
    .code-block {
      background: #1f2937;
      color: #f9fafb;
      padding: 16px;
      border-radius: 6px;
      overflow-x: auto;
      font-family: 'Courier New', monospace;
      font-size: 13px;
      line-height: 1.6;
      margin: 16px 0;
      
      code {
        background: transparent;
        padding: 0;
        color: inherit;
      }
    }
  }
  
  .ai-chat-section {
    margin-top: 80px;
    padding-top: 40px;
    border-top: 2px solid #e5e7eb;
    
    .chat-header {
      font-size: 18px;
      font-weight: 600;
      margin-bottom: 16px;
      color: #111827;
    }
    
    .chat-history {
      margin-bottom: 24px;
      max-height: 400px;
      overflow-y: auto;
      
      .chat-message {
        margin-bottom: 24px;
        padding: 16px;
        background: #f9fafb;
        border-radius: 8px;
        
        .message-question {
          margin-bottom: 12px;
          color: #374151;
          font-size: 14px;
          
          strong {
            color: #2563eb;
          }
        }
        
        .message-answer {
          color: #111827;
          line-height: 1.7;
          font-size: 14px;
          
          :deep(h3) {
            font-size: 16px;
            margin: 12px 0 8px;
          }
          
          :deep(h4) {
            font-size: 14px;
            margin: 10px 0 6px;
          }
          
          :deep(code) {
            background: #f3f4f6;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 13px;
          }
          
          :deep(pre) {
            background: #1f2937;
            color: #f9fafb;
            padding: 12px;
            border-radius: 6px;
            overflow-x: auto;
            margin: 12px 0;
            
            code {
              background: transparent;
              padding: 0;
              color: inherit;
            }
          }
        }
      }
    }
    
    .chat-input-wrapper {
      max-width: 600px;
    }
  }
  
  .overview-content {
    line-height: 1.7;
    color: #374151;
    
    :deep(h3) {
      font-size: 20px;
      margin: 24px 0 12px;
      color: #111827;
    }
    
    :deep(h4) {
      font-size: 18px;
      margin: 20px 0 10px;
      color: #374151;
    }
    
    :deep(code) {
      background: #f3f4f6;
      padding: 2px 6px;
      border-radius: 4px;
      font-family: monospace;
    }
    
    :deep(pre) {
      background: #1f2937;
      color: #f9fafb;
      padding: 12px;
      border-radius: 6px;
      overflow-x: auto;
    }
  }
  
  .overview-placeholder {
    padding: 40px;
    text-align: center;
    color: #6b7280;
  }
}

// 右侧目录
.wiki-toc {
  width: 280px;
  border-left: 1px solid #e5e7eb;
  background: #f9fafb;
  padding: 20px;
  overflow-y: auto;
  
  .toc-header {
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid #e5e7eb;
  }
  
  .toc-title {
    font-size: 14px;
    font-weight: 600;
    color: #374151;
    margin-bottom: 12px;
  }
  
  .toc-list {
    list-style: none;
    padding: 0;
    margin: 0;
    
    li {
      margin-bottom: 8px;
      
      a {
        display: block;
        font-size: 13px;
        color: #6b7280;
        text-decoration: none;
        padding: 4px 0;
        transition: color 0.2s;
        
        &:hover {
          color: #2563eb;
        }
        
        &.active {
          color: #2563eb;
          font-weight: 500;
        }
      }
    }
  }
}

// Mermaid 图表样式
.mermaid-diagram {
  margin: 24px 0;
  padding: 16px;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  
  h3 {
    margin-top: 0;
    margin-bottom: 16px;
    color: #1f2937;
  }
  
  .mermaid-container {
    overflow-x: auto;
    text-align: center;
    
    :deep(.mermaid) {
      display: inline-block;
    }
    
    :deep(svg) {
      max-width: 100%;
      height: auto;
    }
  }
}

// 关键文件列表样式增强
.relevant-files-list {
  .file-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border-radius: 4px;
    transition: background-color 0.2s;
    
    &.high-importance {
      background: #fef3c7;
      border-left: 3px solid #f59e0b;
    }
    
    .file-path {
      flex: 1;
      font-family: 'Monaco', 'Courier New', monospace;
      font-size: 13px;
    }
    
    .file-type-badge {
      padding: 2px 8px;
      background: #e5e7eb;
      border-radius: 12px;
      font-size: 11px;
      color: #6b7280;
    }
    
    .importance-badge {
      padding: 2px 8px;
      background: #dbeafe;
      border-radius: 12px;
      font-size: 11px;
      color: #1e40af;
      font-weight: 500;
    }
  }
}

// 架构建议和代码质量建议样式
.patterns-list,
.suggestions-list,
.refactoring-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.pattern-card,
.suggestion-card,
.refactoring-card {
  .suggestion-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    
    h4 {
      margin: 0;
      color: #1f2937;
    }
  }
  
  p {
    margin: 8px 0;
    line-height: 1.6;
    color: #4b5563;
  }
}

.decisions-list {
  .decision-item {
    margin-bottom: 24px;
    padding: 16px;
    background: #f9fafb;
    border-radius: 8px;
    border-left: 4px solid #3b82f6;
    
    h4 {
      margin-top: 0;
      color: #1f2937;
    }
    
    p {
      margin: 8px 0;
      line-height: 1.6;
    }
  }
}

.smells-list {
  margin-top: 16px;
}
</style>
