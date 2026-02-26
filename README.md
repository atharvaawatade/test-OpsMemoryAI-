# checkout-service

> Sample production microservice protected by [OpsMemory AI](https://github.com/atharvaawatade/OpsMemoryAI) deployment gate.

## What this repo demonstrates

Every pull request to `main` is analyzed by **OpsMemory AI** before it can merge.
The AI agent checks the diff against:
- 📋 25+ Architecture Decision Records (ADRs)
- 🧠 Semantic incident memory (ELSER on Elasticsearch)
- 📊 Historical failure patterns (ES|QL)

If the change is dangerous → **the CI check fails** and the deployment is blocked.

## CI Pipeline

```
PR opened → Unit Tests → OpsMemory AI Gate → Merge allowed / Blocked
```

## Stack

| Layer | Tech |
|-------|------|
| API | Flask 3.1 |
| DB | PostgreSQL (stubbed) |
| Payments | Stripe |
| AI Gate | OpsMemory AI (Elastic Agent Builder + ELSER) |
| CI | GitHub Actions |

## Run locally

```bash
pip install -r requirements.txt
pytest tests/ -v
python -m src.app
```

## Protected by

[![OpsMemory AI](https://img.shields.io/badge/OpsMemory_AI-Deployment_Gate-00BFB3?style=flat&logo=elasticsearch)](https://ops-memory-ai.vercel.app)