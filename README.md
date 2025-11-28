# Performance Testing Framework

A modular, containerized framework for conducting performance, load, and stress testing on REST APIs. This system uses **k6** as the testing engine, wrapped in **Docker** for consistency, and orchestrated by **Python** for ease of use. It generates detailed HTML dashboards, PDF reports, and Jenkins-compatible XML metrics.

## Features

* **Universal Testing:** Supports GET, POST, PUT, DELETE, PATCH, and complex JSON/Form payloads.
* **Zero-Dependency Runtime:** Runs entirely within Docker containers; no need to install k6 locally.
* **Automated Reporting:** Generates interactive HTML dashboards and PDF snapshots for every run.
* **Security First:** Credentials and tokens are managed via environment variables (`.env`), never hardcoded.
* **CI/CD Ready:** Outputs JUnit XML for integration with Jenkins, GitLab CI, or other pipelines.
* **SLA Enforcement:** Automatically fails builds if API latency or error rates exceed defined thresholds.

---

## Quick Start

### Prerequisites
* [Docker Desktop](https://www.docker.com/products/docker-desktop) (Running)
* [Python 3.9+](https://www.python.org/downloads/)

### 1. Setup
Install the necessary Python dependencies for the orchestrator:
```bash
pip3 install -r requirements.txt
playwright install
chmod +x run.sh

### run_test.py --config projects/demo-project/config.json

