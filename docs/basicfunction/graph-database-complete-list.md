# 开源图数据库完整列表

> 调研日期：2025-01-28  
> 目的：列出所有可用的开源图数据库，供知识图谱项目选型参考

---

## 📊 一、推荐使用的开源图数据库（按推荐度排序）

### ⭐⭐⭐⭐⭐ 强烈推荐

#### 1. NebulaGraph
- **许可证**：Apache 2.0 ✅
- **类型**：原生图数据库
- **查询语言**：nGQL
- **GitHub**：https://github.com/vesoft-inc/nebula
- **特点**：
  - ✅ 高性能，支持大规模分布式
  - ✅ 国产化支持，社区活跃
  - ✅ 完全开源，商业友好
  - ✅ 适合大规模知识图谱场景
- **推荐理由**：性能优异、许可证友好、国产化支持

---

### ⭐⭐⭐⭐ 推荐

#### 2. Memgraph
- **许可证**：Apache 2.0 ✅
- **类型**：内存图数据库
- **查询语言**：Cypher
- **GitHub**：https://github.com/memgraph/memgraph
- **特点**：
  - ✅ 内存图数据库，实时性能优异
  - ✅ 兼容Cypher，学习成本低
  - ✅ 部署简单
  - ⚠️ 受内存限制（< 50万实体）
- **推荐理由**：实时性能好、兼容Cypher、许可证友好

#### 3. Dgraph
- **许可证**：Apache 2.0 ✅
- **类型**：分布式图数据库
- **查询语言**：GraphQL
- **GitHub**：https://github.com/dgraph-io/dgraph
- **特点**：
  - ✅ GraphQL查询，API友好
  - ✅ 水平扩展，现代架构
  - ✅ 完全开源，商业友好
  - ⚠️ 社区相对较小
- **推荐理由**：GraphQL查询、现代架构、许可证友好

---

### ⭐⭐⭐ 可以考虑

#### 4. JanusGraph
- **许可证**：Apache 2.0 ✅
- **类型**：分布式图数据库
- **查询语言**：Gremlin
- **GitHub**：https://github.com/JanusGraph/janusgraph
- **特点**：
  - ✅ 可扩展性强，支持多种存储后端
  - ✅ 与Hadoop生态集成
  - ⚠️ 配置复杂，运维成本高
  - ⚠️ 需要额外存储后端
- **推荐理由**：可扩展性强、生态丰富，但配置复杂

#### 5. HugeGraph
- **许可证**：Apache 2.0 ✅
- **类型**：分布式图数据库
- **查询语言**：Gremlin
- **GitHub**：https://github.com/apache/hugegraph
- **特点**：
  - ✅ 国产化支持
  - ✅ 与Hadoop生态集成
  - ⚠️ 社区较小，文档较少
- **推荐理由**：国产化支持，但生态不成熟

#### 6. FalkorDB
- **许可证**：BSD 3-Clause ✅
- **类型**：基于Redis的图数据库
- **查询语言**：Cypher
- **GitHub**：https://github.com/FalkorDB/FalkorDB
- **特点**：
  - ✅ 基于Redis，性能优异
  - ✅ 兼容openCypher
  - ✅ 内存图数据库
  - ⚠️ 社区较小，受内存限制
- **推荐理由**：Redis生态、性能好，但社区较小

---

### ⭐⭐ 不推荐（但有特定场景可用）

#### 7. Neo4j Community
- **许可证**：GPL 3.0 ⚠️
- **类型**：原生图数据库
- **查询语言**：Cypher
- **GitHub**：https://github.com/neo4j/neo4j
- **特点**：
  - ✅ 最成熟稳定，生态最丰富
  - ✅ Cypher查询语言易学
  - ⚠️ GPL 3.0许可证（分发需开源）
  - ⚠️ 单机限制，集群功能受限
- **推荐理由**：成熟稳定，但GPL许可证需注意

#### 8. OrientDB
- **许可证**：Apache 2.0 ✅
- **类型**：多模型数据库
- **查询语言**：SQL/Gremlin
- **GitHub**：https://github.com/orientechnologies/orientdb
- **特点**：
  - ✅ 多模型支持
  - ⚠️ 社区活跃度下降
  - ⚠️ 性能不如专业图数据库
- **推荐理由**：多模型支持，但社区活跃度低

#### 9. Cayley
- **许可证**：Apache 2.0 ✅
- **类型**：轻量级图数据库
- **查询语言**：Gremlin
- **GitHub**：https://github.com/cayleygraph/cayley
- **特点**：
  - ✅ Google开源，轻量级
  - ✅ 支持多种后端
  - ⚠️ 社区活跃度低，维护较少
- **推荐理由**：轻量级，但维护较少

#### 10. Blazegraph
- **许可证**：GPL 2.0 ⚠️
- **类型**：RDF图数据库
- **查询语言**：SPARQL
- **GitHub**：https://github.com/blazegraph/database
- **特点**：
  - ✅ 高性能RDF存储
  - ✅ 支持SPARQL
  - ⚠️ GPL许可证需注意
  - ⚠️ 主要面向RDF数据
- **推荐理由**：RDF场景可用，但GPL许可证需注意

---

## ❌ 不推荐使用的图数据库

### 1. ArangoDB
- **许可证**：BSL 1.1 ❌
- **原因**：不适合SaaS/多租户场景，有商业使用限制
- **状态**：2028年后转为Apache 2.0

### 2. RedisGraph
- **状态**：已停止维护 ❌
- **原因**：Redis Labs停止开发，许可证限制

### 3. Titan
- **状态**：已停止维护 ❌
- **原因**：被JanusGraph替代

---

## 📋 二、按许可证分类

### Apache 2.0（完全开源，商业友好）✅

1. **NebulaGraph** ⭐⭐⭐⭐⭐
2. **Memgraph** ⭐⭐⭐⭐
3. **Dgraph** ⭐⭐⭐⭐
4. **JanusGraph** ⭐⭐⭐
5. **HugeGraph** ⭐⭐⭐
6. **OrientDB** ⭐⭐
7. **Cayley** ⭐⭐

### BSD 3-Clause（完全开源，商业友好）✅

1. **FalkorDB** ⭐⭐⭐

### GPL 2.0/3.0（开源，但分发需开源）⚠️

1. **Neo4j Community** ⭐⭐⭐
2. **Blazegraph** ⭐⭐

### BSL 1.1（非开源，商业限制）❌

1. **ArangoDB** ❌ 不推荐

---

## 📋 三、按查询语言分类

### Cypher

1. **Memgraph** ⭐⭐⭐⭐
2. **Neo4j Community** ⭐⭐⭐
3. **FalkorDB** ⭐⭐⭐

### nGQL

1. **NebulaGraph** ⭐⭐⭐⭐⭐

### GraphQL

1. **Dgraph** ⭐⭐⭐⭐

### Gremlin

1. **JanusGraph** ⭐⭐⭐
2. **HugeGraph** ⭐⭐⭐
3. **Cayley** ⭐⭐

### SPARQL（RDF）

1. **Blazegraph** ⭐⭐

### AQL

1. **ArangoDB** ❌ 不推荐

---

## 📋 四、按使用场景分类

### 大规模分布式场景（> 100万实体）

1. **NebulaGraph** ⭐⭐⭐⭐⭐（首选）
2. **JanusGraph** ⭐⭐⭐
3. **HugeGraph** ⭐⭐⭐

### 中小规模场景（< 100万实体）

1. **Memgraph** ⭐⭐⭐⭐（实时性能好）
2. **Dgraph** ⭐⭐⭐⭐（GraphQL）
3. **FalkorDB** ⭐⭐⭐（Redis生态）

### 学习研究场景

1. **Neo4j Community** ⭐⭐⭐（最成熟）
2. **Cayley** ⭐⭐（轻量级）

### RDF/语义网场景

1. **Blazegraph** ⭐⭐（GPL需注意）

---

## 🎯 五、最终推荐

### 首选：NebulaGraph
- ✅ Apache 2.0许可证
- ✅ 性能优异，支持大规模
- ✅ 国产化支持
- ✅ 社区活跃

### 次选：Memgraph
- ✅ Apache 2.0许可证
- ✅ 实时性能优异
- ✅ 兼容Cypher
- ⚠️ 受内存限制

### 备选：Dgraph
- ✅ Apache 2.0许可证
- ✅ GraphQL查询
- ✅ 现代架构
- ⚠️ 社区较小

---

**调研完成日期**：2025-01-28  
**调研人**：AI Assistant

