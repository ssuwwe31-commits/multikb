FROM opensearchproject/opensearch:2.11.0

# 安装IK中文分词插件
RUN bin/opensearch-plugin install -b https://github.com/medcl/elasticsearch-analysis-ik/releases/download/v8.11.0/elasticsearch-analysis-ik-8.11.0.zip

# 复制IK配置文件
COPY ik/ /usr/share/opensearch/plugins/ik/config/

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=5 CMD curl -f http://localhost:9200/_cluster/health || exit 1

