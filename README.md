
# Medical Data Intelligence Platform

A healthcare data engineering and analytics prototype designed around hospital information-center workflows. It demonstrates how synthetic EHR data can be processed, validated, organized into an analytical warehouse, and combined with a clinical knowledge base for retrieval-augmented question answering.

> **Project status:** Independent portfolio prototype using synthetic EHR data. It is not a production hospital information system, a validated clinical decision-support tool, or a substitute for professional medical judgment.

## Overview

Hospital analytics workflows often need to combine structured patient and encounter data with clinical knowledge documented in unstructured text. This project demonstrates an end-to-end architecture connecting data preparation, quality controls, analytical storage, reporting, and RAG.

## Key Features

### 1. Synthetic EHR data and ETL

- Initializes a local SQLite database.
- Creates patient, encounter, condition, medication, and observation records.
- Demonstrates extraction, transformation, standardization, and loading.
- Produces processed CSV files and pipeline logs.

The current synthetic dataset contains:

| Entity | Records |
|---|---:|
| Patients | 1,000 |
| Encounters | 5,000 |
| Conditions | 3,000 |
| Medications | 3,000 |
| Observations | 10,000 |

### 2. Data quality assessment

The quality workflow checks four dimensions:

- **Completeness:** Required-field coverage.
- **Validity:** Date formats, gender values, ICD-related fields, and numeric validity.
- **Consistency:** Foreign-key references and date logic.
- **Uniqueness:** Primary-key uniqueness.

It generates an HTML data-quality report and execution logs.

### 3. Analytical data warehouse

The warehouse uses a star-schema design with the following tables:

| Type | Table | Purpose |
|---|---|---|
| Dimension | `dim_patient` | Patient attributes |
| Dimension | `dim_condition` | Diagnosis attributes |
| Dimension | `dim_medication` | Medication attributes |
| Fact | `fact_encounter` | Encounter events |
| Fact | `fact_observation` | Observation and laboratory events |
| Fact | `fact_condition` | Patient-diagnosis relationships |
| Fact | `fact_medication` | Patient-medication relationships |

The warehouse is created separately from the operational SQLite database.

### 4. Clinical and operational analytics

The analytical modules generate reports for:

- Patient statistics
- Disease statistics
- Medication statistics
- Laboratory statistics
- Hospital KPIs

### 5. Clinical knowledge base

The knowledge-base workflow ingests clinical documents, processes them into chunks, generates embeddings, and creates a FAISS vector index.

The current implementation uses `sentence-transformers` with the multilingual model `paraphrase-multilingual-MiniLM-L12-v2`.

### 6. Dual-retrieval RAG assistant

The RAG workflow combines two sources of context:

1. **Structured retrieval:** Patient, disease, and KPI information from the analytical warehouse.
2. **Knowledge retrieval:** Relevant passages from the FAISS clinical knowledge base.

A context builder combines the retrieved information before response generation. The LLM layer supports an optional OpenAI API integration and a local fallback path.

### 7. Streamlit demonstration dashboard

The dashboard provides an internal demonstration interface for platform overview, clinical RAG questions, and system documentation.

## Architecture

```text
Synthetic EHR CSVs
        |
        v
ETL: Extract -> Transform -> Load
        |
        v
Operational SQLite Database
        |
        +----------------------+
        |                      |
        v                      v
Data Quality Assessment    Star-Schema Warehouse
        |                      |
        v                      v
HTML Quality Report        Clinical Analytics
                               |
                               v
                         Hospital KPI Reports

Clinical Documents
        |
        v
Document Processing -> Embeddings -> FAISS Index
                                         |
                                         v
User Question -> Structured Retrieval + Knowledge Retrieval
                                         |
                                         v
                                  Context Builder
                                         |
                                         v
                                  LLM / Fallback
```

## Technology Stack

- Python
- SQLite and SQLAlchemy
- pandas
- FastAPI components where applicable
- Streamlit
- sentence-transformers
- FAISS
- Optional OpenAI API integration

## Quick Start

Run the commands from the repository root.

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize the synthetic database

```bash
python database/init_data.py
```

This creates `database/hospital.db` and initializes synthetic EHR records.

### 3. Run the ETL pipeline

```bash
python etl/pipeline.py
```

Processed outputs are written under `data/processed/`. The pipeline log is stored in `logs/etl.log`.

The current workflow expects the following raw CSV files to be present when running the ETL stage:

```text
data/raw/patients.csv
data/raw/conditions.csv
data/raw/medications.csv
```

### 4. Generate the data-quality report

```bash
python quality/quality_report.py
```

Expected output:

```text
reports/data_quality_report.html
```

### 5. Build the analytical warehouse

```bash
python warehouse/build_warehouse.py
```

The warehouse is written to:

```text
warehouse/warehouse.db
```

### 6. Generate clinical analytics reports

```bash
python warehouse/build_warehouse.py
python analytics/analytics_report.py
```

Outputs include patient, disease, medication, laboratory, and hospital KPI reports under `reports/`.

### 7. Build the clinical knowledge base

Run the knowledge-base steps in order:

```bash
python knowledge_base/ingestion.py
python knowledge_base/document_processor.py
python knowledge_base/embedding.py
python knowledge_base/vector_store.py
```

To run a knowledge search:

```bash
python knowledge_base/knowledge_search.py "What HbA1c level should be monitored in a patient with diabetes?"
```

### 8. Run the RAG assistant

Ensure the warehouse and vector index have been created, then run:

```bash
python rag/clinical_rag.py "What HbA1c level should be monitored in a patient with diabetes?"
```

To inspect retrieved context:

```bash
python rag/clinical_rag.py -v "How many patients are in the hospital dataset?"
```

To start an interactive session:

```bash
python rag/clinical_rag.py --interactive
```

An OpenAI API key can be configured in `.env` when using the optional API-backed response path:

```env
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4o-mini
```

Do not commit API keys or other secrets to the repository.

### 9. Launch the dashboard

```bash
streamlit run dashboard/app.py
```

Open `http://localhost:8501` in a browser.

The repository documents default demo credentials for local demonstration. They should not be used in a deployed or externally accessible environment; configure credentials securely before any shared deployment.

## Outputs

Representative outputs include:

- `database/hospital.db`
- `warehouse/warehouse.db`
- `reports/data_quality_report.html`
- `reports/clinical_analytics_report.html`
- `reports/patient_statistics.csv`
- `reports/disease_statistics.csv`
- `reports/medication_statistics.csv`
- `reports/laboratory_statistics.csv`
- `reports/hospital_kpi.csv`
- `knowledge_base/vector_store/faiss.index`

## Limitations and Responsible Use

- All EHR records are synthetic and do not represent real patients.
- The RAG assistant may produce incomplete or incorrect answers and requires independent review.
- Retrieved passages and generated text are not equivalent to clinically validated recommendations.
- The current implementation is a demonstration architecture, not a production-grade clinical system.
- Security, privacy, access control, monitoring, and clinical validation would require additional work before real-world use.

## License

See the repository's `LICENSE` file.
