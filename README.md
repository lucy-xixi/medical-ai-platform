# Medical Data Intelligence Platform

面向医院信息中心的医疗数据智能分析与 RAG 平台。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 初始化数据库（Synthetic EHR）

```bash
python database/init_data.py
```

脚本将自动：

- 创建 SQLite 数据库文件 `database/hospital.db`
- 建立所有医疗数据表（Patient / Encounter / Condition / Medication / Observation）
- 生成并插入 Synthetic EHR 测试数据

预期输出末尾：

```
Database initialization completed.
```

### 3. 数据量

| 表 | 记录数 |
|----|--------|
| patients | 1,000 |
| encounters | 5,000 |
| conditions | 3,000 |
| medications | 3,000 |
| observations | 10,000 |

### 4. 运行 ETL 数据流水线

ETL 模块模拟医院数据采集、清洗、标准化和入库流程。

```bash
python etl/pipeline.py
```

预期输出末尾：

```
ETL pipeline completed.
```

**流程说明：**

| 阶段 | 模块 | 说明 |
|------|------|------|
| Extract | `etl/extract.py` | 读取 `data/raw/` 原始 CSV |
| Transform | `etl/transform.py` | 清洗标准化，输出至 `data/processed/` |
| Load | `etl/load.py` | 写入 `database/hospital.db` |

**原始数据文件（需预先放置）：**

```
data/raw/patients.csv
data/raw/conditions.csv
data/raw/medications.csv
```

**清洗后输出：**

```
data/processed/processed_patient.csv
data/processed/processed_condition.csv
data/processed/processed_medication.csv
```

**日志文件：** `logs/etl.log`

### 5. 运行数据质量评估

数据质量管理模块模拟医院数据治理（Data Governance）与数据质量（Data Quality）流程。

```bash
python quality/quality_report.py
```

预期输出：

```
Data quality report generated:
reports/data_quality_report.html
```

**评估维度：**

| 维度 | 模块 | 说明 |
|------|------|------|
| Completeness | `quality/completeness.py` | 关键字段非空覆盖率 |
| Accuracy | `quality/accuracy.py` | 日期格式、gender、ICD、数值有效性 |
| Consistency | `quality/consistency.py` | 外键引用、日期逻辑 |
| Uniqueness | `quality/uniqueness.py` | 主键唯一性 |

**输出文件：**

- HTML 报告：`reports/data_quality_report.html`
- 运行日志：`logs/data_quality.log`

### 6. 构建医疗数据仓库

数据仓库模块模拟医院信息中心的数据仓库建设，采用星型模型（Star Schema）。

```bash
python warehouse/build_warehouse.py
```

预期输出：

```
Healthcare data warehouse created successfully.
```

**星型模型结构：**

| 类型 | 表名 | 说明 |
|------|------|------|
| 维度表 | `dim_patient` | 患者维度（gender, birth_year, age_group） |
| 维度表 | `dim_condition` | 诊断维度（icd_code, condition_name） |
| 维度表 | `dim_medication` | 药品维度（drug_name） |
| 事实表 | `fact_encounter` | 就诊事实 |
| 事实表 | `fact_observation` | 观测/检验事实 |
| 事实表 | `fact_condition` | 诊断事实（患者-诊断关联） |
| 事实表 | `fact_medication` | 用药事实（患者-药品关联） |

**数据流：**

```
database/hospital.db  →  warehouse/build_warehouse.py  →  warehouse/warehouse.db
```

**日志文件：** `logs/warehouse.log`

### 7. 运行临床统计分析 (Clinical Analytics)

基于数据仓库 `warehouse/warehouse.db` 进行临床统计与医院运营分析（只读，不访问 hospital.db）。

```bash
# 请先确保数据仓库已构建
python warehouse/build_warehouse.py

python analytics/analytics_report.py
```

预期输出：

```
Clinical analytics report generated successfully.
```

**分析模块：**

| 模块 | 输出 |
|------|------|
| `patient_analysis.py` | `reports/patient_statistics.csv` |
| `disease_analysis.py` | `reports/disease_statistics.csv` |
| `medication_analysis.py` | `reports/medication_statistics.csv` |
| `laboratory_analysis.py` | `reports/laboratory_statistics.csv` |
| `hospital_kpi.py` | `reports/hospital_kpi.csv` |
| `analytics_report.py` | `reports/clinical_analytics_report.html` |

**日志文件：** `logs/analytics.log`

### 8. 构建临床知识库 (Clinical Knowledge Base)

将非结构化临床知识文档采集、切分、向量化并建立 FAISS 可检索知识库。

```bash
python knowledge_base/ingestion.py
python knowledge_base/document_processor.py
python knowledge_base/embedding.py
python knowledge_base/vector_store.py
python knowledge_base/knowledge_search.py
```

`vector_store.py` 完成后输出：

```
Clinical Knowledge Base created successfully.
```

**知识检索示例：**

```bash
python knowledge_base/knowledge_search.py "糖尿病患者HbA1c多少需要关注？"
```

**目录结构：**

```
knowledge_base/
├── documents/                  # 临床知识文档（中文）
├── processed_documents.json    # 切分后的文本块
├── document_embeddings.npy     # 向量矩阵
└── vector_store/
    └── faiss.index             # FAISS 向量索引
```

**技术栈：** sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`) + FAISS

**日志文件：** `logs/knowledge_base.log`

### 9. Clinical RAG Assistant（临床 RAG 智能助手）

整合**数据仓库结构化数据**与 **FAISS 临床知识库**，实现双路检索增强生成（RAG）。

```
User Question
      ↓
Clinical RAG Assistant
      ↓
┌─────────────┬──────────────────┐
Patient Data  Medical Knowledge
(Warehouse)   (FAISS Vector DB)
      ↓              ↓
      └── Context Retrieval ──┘
                ↓
          LLM Response
```

**前置条件：**

```bash
python warehouse/build_warehouse.py
python knowledge_base/vector_store.py
```

**运行：**

```bash
# 单次问答
python rag/clinical_rag.py "糖尿病患者HbA1c多少需要关注？"

# 显示检索上下文
python rag/clinical_rag.py -v "医院有多少患者？"

# 交互模式
python rag/clinical_rag.py --interactive
```

**模块说明：**

| 文件 | 职责 |
|------|------|
| `rag/patient_retriever.py` | 从 warehouse.db 检索患者/疾病/KPI 数据 |
| `rag/knowledge_retriever.py` | 从 FAISS 知识库检索临床指南 |
| `rag/context_builder.py` | 合并双路上下文，构建 Prompt |
| `rag/llm_response.py` | LLM 回答（支持 OpenAI，无 Key 时本地回退） |
| `rag/clinical_rag.py` | 主入口 |

**可选 OpenAI 配置（.env）：**

```env
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4o-mini
```

**日志文件：** `logs/rag.log`

## 数据库配置

默认使用本地 SQLite，**无需安装 MySQL / Docker**。

数据库文件路径：`database/hospital.db`

### 切换至 MySQL / PostgreSQL（可选）

在项目根目录创建 `.env` 文件：

```env
# MySQL
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/medical_platform

# PostgreSQL
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/medical_platform
```

## 项目结构

```
medical-ai-platform/
├── database/
│   ├── models.py        # SQLAlchemy ORM 模型
│   ├── connection.py    # 数据库连接与 Session
│   ├── init_data.py     # Synthetic EHR 初始化
│   ├── hospital.db      # SQLite 数据库（运行后生成）
│   └── schema.sql       # MySQL 参考 DDL（生产迁移用）
├── analytics/
├── api/
├── dashboard/
├── etl/
│   ├── extract.py       # 数据抽取
│   ├── transform.py     # 数据清洗与标准化
│   ├── load.py          # 数据入库
│   └── pipeline.py      # ETL 完整流水线
├── data/
│   ├── raw/             # 原始 CSV 数据
│   └── processed/       # 清洗后数据
├── logs/
│   ├── etl.log          # ETL 运行日志
│   ├── data_quality.log # 数据质量评估日志
│   ├── warehouse.log    # 数据仓库构建日志
│   ├── analytics.log    # 临床分析日志
│   ├── knowledge_base.log # 知识库日志
│   └── rag.log            # RAG 日志
├── quality/
│   ├── completeness.py  # 完整性检查
│   ├── accuracy.py      # 准确性检查
│   ├── consistency.py   # 一致性检查
│   ├── uniqueness.py    # 唯一性检查
│   └── quality_report.py # 质量报告生成
├── reports/
│   └── data_quality_report.html
├── warehouse/
│   ├── models.py          # 星型模型 ORM
│   ├── build_warehouse.py # 数据仓库构建
│   └── warehouse.db       # 数据仓库（运行后生成）
├── analytics/
│   ├── patient_analysis.py
│   ├── disease_analysis.py
│   ├── medication_analysis.py
│   ├── laboratory_analysis.py
│   ├── hospital_kpi.py
│   └── analytics_report.py
├── knowledge_base/
│   ├── documents/             # 临床知识文档
│   ├── ingestion.py           # 知识采集
│   ├── document_processor.py  # 文本切分
│   ├── embedding.py           # 向量化
│   ├── vector_store.py        # FAISS 索引
│   └── knowledge_search.py    # 语义检索
├── rag/
│   ├── patient_retriever.py   # 患者数据检索
│   ├── knowledge_retriever.py # 知识库检索
│   ├── context_builder.py     # 上下文构建
│   ├── llm_response.py        # LLM 回答
│   └── clinical_rag.py        # RAG 主入口
├── nlp/
├── rag/
└── ...
```

## 技术栈

- **数据库**: SQLite（开发）/ MySQL / PostgreSQL（生产）
- **ORM**: SQLAlchemy 2.0
- **数据生成**: Faker
- **API**: FastAPI
- **前端**: Streamlit
- **RAG**: LangChain + FAISS
