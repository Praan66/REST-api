# FastAPI CRUD + Observability Project

A production-style REST API built using **FastAPI** with full containerized infrastructure including database, reverse proxy, logging, monitoring, and visualization.

---

## 🛠️ Features & </> Tech Stack

- Basic CRUD REST APIs using FastAPI
- SQLAlchemy ORM for database operations
- PostgreSQL database
- JWT Authentication
- Dockerized:
- - FFmpeg, Nginx reverse proxy, load balancing, rate limiting, caching
- - Prometheus (metrics)
- - Grafana (visualization)
- Python logging (middleware global logging + global exception handler)
- Basic testing example

---

## 📁 Project Setup

### 1. Clone the repository
```
git clone https://github.com/Praan66/REST-api.git
cd REST-api
```
---
## Environment Variables

Create a `.env` file inside REST-api folder:
```
POSTGRES_USER=postgres
POSTGRES_PASSWORD=admin
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DBNAME=mydb

# run "python key.py" to generate random and paste here. 
SSECRET_KEY= 
# (HMAC + SHA256)
SALGORITHM=HS256
SACCESS_TOKEN_EXPIRE_MINUTES=30
```
### To the Application(start Docker Desktop which start Docker Daemon process)
Use Docker Compose to spin up the entire stack:

#### bash/cmd/powershell
```
docker compose up --build -d
```
```
docker compose logs -f
```

## 📊 Monitoring & Metrics
This project includes a full monitoring suite to track application performance.

### 1. Prometheus
Navigate to: 
```
http://localhost:9090
```

Go to Status > Targets.

Verify that the target shows UP. Prometheus automatically collect metrics from `/metrics` to visualize your data.

### 2. Grafana
Navigate to: 
```
http://localhost:3000
```
Login with: <br>
Email or Username - `admin` <br> 
Password - `admin`

**Configure Datasource:**
1. Go to Connections > Data Sources.
2. Select Prometheus and set the URL to `http://localhost:9090`.
3. Click Save & Test.

**Import Dashboard:**
1. Go to Dashboards > New > Import.
2. Enter ID `22676` and click Load.

## 🌐 Expose Project to the Internet (Cloudflare Tunnel)
To expose your local FastAPI application to the internet securely, **Cloudflare Tunnel** is best.

### 1. Quick Start (Temporary Tunnel)
If we want to test your API publicly, use `trycloudflare`:
1. Ensure `cloudflared` is installed on your machine.
2. Run the following command in your terminal while your Docker stack is running:
```
cloudflared tunnel --url http://localhost:80
```
**Global Exception Handling**: Centralized error management for consistent API responses.<br> 
**Global Logging**: Middleware-based application logging for better traceability.<br>
**Kind of Production Ready**: Pre-configured with Nginx, Prometheus, and Grafana for enterprise-grade monitoring.