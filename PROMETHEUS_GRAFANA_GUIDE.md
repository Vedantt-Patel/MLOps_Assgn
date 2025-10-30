# 📊 Prometheus & Grafana Monitoring Setup

## Overview

This setup provides complete monitoring for the Fake News Detector ML application using:

- **Prometheus** - Metrics collection and storage
- **Grafana** - Visualization and dashboards
- **Custom Metrics** - ML-specific metrics (predictions, accuracy, latency, etc.)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Monitoring Stack                         │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │  FastAPI     │───▶│  Prometheus  │───▶│   Grafana    │ │
│  │  (Metrics)   │    │  (Storage)   │    │  (Dashboards)│ │
│  │  Port 8000   │    │  Port 9090   │    │  Port 3000   │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│         │                                        │          │
│         └────────────────────────────────────────┘          │
│              Metrics Endpoint: /metrics                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Metrics Exposed

### Application Metrics

1. **fakenews_predictions_total** (Counter)
   - Total number of predictions
   - Labels: `result` (REAL/FAKE)
2. **fakenews_prediction_latency_seconds** (Histogram)

   - Time taken for predictions
   - Buckets: [0.1, 0.5, 1.0, 2.0, 5.0]

3. **fakenews_feedback_total** (Counter)

   - User feedback submissions
   - Labels: `feedback_type` (correct/incorrect)

4. **fakenews_average_rating** (Gauge)

   - Current average user rating (1-5)

5. **fakenews_total_predictions** (Gauge)

   - Total predictions in database

6. **fakenews_model_accuracy** (Gauge)

   - Model accuracy based on user feedback (%)

7. **fakenews_fake_count** (Gauge)

   - Number of FAKE predictions

8. **fakenews_real_count** (Gauge)
   - Number of REAL predictions

### HTTP Metrics (Auto-instrumented)

9. **http_requests_total** (Counter)

   - Total HTTP requests
   - Labels: `method`, `handler`, `status`

10. **http_request_duration_seconds** (Histogram)

    - HTTP request duration

11. **fakenews_requests_inprogress** (Gauge)
    - Currently active requests

---

## 🚀 Quick Start

### 1. Start All Services

```powershell
# Build and start all services (including Prometheus & Grafana)
docker-compose up -d --build

# Wait for services to be ready (~30 seconds)
timeout /t 30 /nobreak

# Check status
docker-compose ps
```

### 2. Access Services

| Service         | URL                           | Credentials |
| --------------- | ----------------------------- | ----------- |
| **Main App**    | http://localhost:8000         | -           |
| **API Metrics** | http://localhost:8000/metrics | -           |
| **Prometheus**  | http://localhost:9090         | -           |
| **Grafana**     | http://localhost:3000         | admin/admin |
| **MLflow**      | http://localhost:5000         | -           |

### 3. Access Grafana Dashboard

1. Open http://localhost:3000
2. Login: `admin` / `admin`
3. (Optional) Change password when prompted
4. Dashboard auto-loads: "Fake News Detector - ML Monitoring"

---

## 📈 Using Prometheus

### Access Prometheus UI

1. Open http://localhost:9090
2. Go to **Status** → **Targets** to verify scraping
3. Should see target: `fakenews-api` with status **UP**

### Sample Queries

```promql
# Total predictions
fakenews_predictions_total

# Prediction rate (per minute)
rate(fakenews_predictions_total[1m])

# Average latency (p95)
histogram_quantile(0.95, rate(fakenews_prediction_latency_seconds_bucket[5m]))

# Current accuracy
fakenews_model_accuracy

# FAKE vs REAL ratio
fakenews_fake_count / fakenews_real_count

# Request rate by endpoint
rate(http_requests_total[5m])

# Active requests
fakenews_requests_inprogress

# Error rate
rate(http_requests_total{status=~"5.."}[5m])
```

### Explore Metrics

1. Click **Graph** tab
2. Start typing metric name (autocomplete available)
3. Click **Execute** to visualize
4. Use time range selector for different periods

---

## 📊 Using Grafana

### Pre-configured Dashboard

The dashboard includes:

**Row 1: Key Metrics**

- Total Predictions (stat panel)
- Model Accuracy (gauge)
- Average Rating (gauge)
- Predictions Rate (stat panel)

**Row 2: Trends**

- Predictions Over Time (graph)
- REAL vs FAKE Distribution (pie chart)

**Row 3: Performance**

- Prediction Latency p50/p95/p99 (graph)
- User Feedback Distribution (bar chart)

**Row 4: HTTP Metrics**

- HTTP Request Rate (graph)
- HTTP Request Duration (graph)

**Row 5: System Health**

- Active Requests (stat)
- System Health Status (table)

### Customizing Dashboard

1. Click dashboard title → **Settings**
2. Add new panel: Click **Add panel**
3. Select visualization type
4. Enter PromQL query
5. Customize appearance
6. Click **Apply** and **Save**

### Creating Alerts

1. Edit panel → **Alert** tab
2. Create alert rule
3. Set conditions (e.g., accuracy < 70%)
4. Configure notification channel
5. Save

---

## 🔧 Configuration Files

### prometheus.yml

Location: `./prometheus.yml`

**Key Sections:**

```yaml
global:
  scrape_interval: 15s # How often to scrape metrics

scrape_configs:
  - job_name: "fakenews-api"
    scrape_interval: 10s
    metrics_path: "/metrics"
    static_configs:
      - targets: ["api:8000"]
```

**Modify scrape interval:**

```yaml
scrape_interval: 5s # Scrape every 5 seconds (more frequent)
```

### Grafana Datasource

Location: `./grafana/provisioning/datasources/prometheus.yml`

Auto-configures Prometheus as datasource:

```yaml
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
    isDefault: true
```

### Grafana Dashboard

Location: `./grafana/provisioning/dashboards/fakenews-dashboard.json`

Auto-loads on Grafana startup. Can be edited via UI.

---

## 📝 Monitoring Workflow

### 1. Generate Some Data

```powershell
# Make predictions via API
curl -X POST "http://localhost:8000/predict" `
     -H "Content-Type: application/json" `
     -d '{\"title\":\"Breaking News\",\"text\":\"This is a test article\"}'

# Or use the web interface
# Open http://localhost:8000 and make predictions
```

### 2. Check Metrics Endpoint

```powershell
# View raw metrics
curl http://localhost:8000/metrics
```

Output example:

```
# HELP fakenews_predictions_total Total number of predictions made
# TYPE fakenews_predictions_total counter
fakenews_predictions_total{result="FAKE"} 5.0
fakenews_predictions_total{result="REAL"} 3.0

# HELP fakenews_model_accuracy Model accuracy based on user feedback
# TYPE fakenews_model_accuracy gauge
fakenews_model_accuracy 75.0
```

### 3. View in Prometheus

1. Open http://localhost:9090
2. Query: `fakenews_predictions_total`
3. Click **Graph** to visualize
4. Adjust time range

### 4. View in Grafana

1. Open http://localhost:3000
2. Dashboard loads automatically
3. Metrics update in real-time
4. Set auto-refresh (top right): 10s, 30s, 1m, etc.

---

## 🎯 Use Cases

### Monitor Model Performance

**Metrics to watch:**

- `fakenews_model_accuracy` - Should stay > 70%
- `fakenews_average_rating` - User satisfaction
- `fakenews_predictions_total` - Usage trends

**Alert if:**

- Accuracy drops below 70%
- Average rating below 3.0
- Sudden spike in FAKE predictions

### Monitor System Performance

**Metrics to watch:**

- `fakenews_prediction_latency_seconds` - Should be < 1s
- `http_request_duration_seconds` - API responsiveness
- `fakenews_requests_inprogress` - Load

**Alert if:**

- Latency p95 > 2 seconds
- Active requests > 100
- Error rate > 5%

### Track Usage Patterns

**Metrics to watch:**

- `rate(fakenews_predictions_total[1h])` - Requests per hour
- `fakenews_fake_count / fakenews_real_count` - Detection ratio
- `fakenews_feedback_total` - User engagement

**Insights:**

- Peak usage times
- FAKE vs REAL distribution
- User feedback trends

---

## 🔍 Troubleshooting

### Prometheus Not Scraping

**Check target status:**

```powershell
curl http://localhost:9090/api/v1/targets
```

**If target is DOWN:**

1. Check API is running: `docker ps | findstr api`
2. Check metrics endpoint: `curl http://localhost:8000/metrics`
3. Check Prometheus logs: `docker-compose logs prometheus`
4. Verify network: `docker network inspect fakenews-network`

**Fix:**

```powershell
# Restart services
docker-compose restart prometheus api
```

### Grafana Shows No Data

**Check datasource:**

1. Grafana → Configuration → Data Sources
2. Click Prometheus
3. Click **Test** button
4. Should show "Data source is working"

**If not working:**

1. Verify Prometheus URL: `http://prometheus:9090`
2. Check Prometheus is running: `docker ps | findstr prometheus`
3. Check Grafana logs: `docker-compose logs grafana`

**Fix:**

```powershell
# Restart Grafana
docker-compose restart grafana
```

### Dashboard Not Loading

**Check provisioning:**

```powershell
# Verify files exist
dir grafana\provisioning\dashboards\
dir grafana\provisioning\datasources\

# Check Grafana logs
docker-compose logs grafana | findstr dashboard
```

**Reload dashboard:**

1. Grafana → Dashboards → Browse
2. Find "Fake News Detector - ML Monitoring"
3. Click to open

### Metrics Not Updating

**Check app is generating metrics:**

```powershell
# Make a prediction
curl -X POST "http://localhost:8000/predict" `
     -H "Content-Type: application/json" `
     -d '{\"title\":\"Test\",\"text\":\"Test article\"}'

# Check metrics immediately
curl http://localhost:8000/metrics | findstr predictions_total
```

**Verify in Prometheus:**

```
fakenews_predictions_total
```

Should increment after prediction.

---

## 🔐 Security Recommendations

### Production Deployment

1. **Change Grafana password:**

   ```yaml
   environment:
     - GF_SECURITY_ADMIN_PASSWORD=your_secure_password
   ```

2. **Enable authentication:**

   - Set up user accounts in Grafana
   - Disable anonymous access

3. **Use HTTPS:**

   - Configure TLS for Prometheus and Grafana
   - Use reverse proxy (nginx/traefik)

4. **Restrict access:**

   - Don't expose ports publicly
   - Use firewall rules
   - VPN for access

5. **Secure metrics endpoint:**
   - Add authentication to `/metrics`
   - Use internal network only

---

## 📦 Data Retention

### Prometheus Storage

**Default retention:** 15 days

**Change retention in docker-compose.yml:**

```yaml
command:
  - "--storage.tsdb.retention.time=30d" # Keep 30 days
```

**Check storage usage:**

```powershell
docker exec fakenews-prometheus du -sh /prometheus
```

### Grafana Storage

**Dashboard persistence:** Stored in `grafana-data` volume

**Backup dashboards:**

1. Grafana → Dashboard → Settings
2. Click **JSON Model**
3. Copy and save

**Backup volume:**

```powershell
docker run --rm -v fakenews-grafana-data:/data -v ${PWD}:/backup `
    alpine tar czf /backup/grafana-backup.tar.gz -C /data .
```

---

## 🎨 Custom Metrics

### Add New Metric

**1. In main.py:**

```python
from prometheus_client import Counter

# Define metric
custom_metric = Counter(
    'fakenews_custom_metric',
    'Description of metric',
    ['label1', 'label2']
)

# Increment metric
custom_metric.labels(label1='value1', label2='value2').inc()
```

**2. Restart API:**

```powershell
docker-compose restart api
```

**3. Verify in Prometheus:**

```
fakenews_custom_metric
```

**4. Add to Grafana dashboard**

---

## 📊 Exporting Data

### Export Prometheus Data

```powershell
# Query specific metric
curl "http://localhost:9090/api/v1/query?query=fakenews_predictions_total"

# Query range
curl "http://localhost:9090/api/v1/query_range?query=fakenews_predictions_total&start=2024-01-01T00:00:00Z&end=2024-01-02T00:00:00Z&step=1m"
```

### Export Grafana Dashboard

1. Dashboard → Share → Export
2. Save as JSON
3. Can import later: Dashboard → Import

---

## ✅ Verification Checklist

After setup, verify:

- [ ] Prometheus accessible at http://localhost:9090
- [ ] Grafana accessible at http://localhost:3000
- [ ] Metrics endpoint working: http://localhost:8000/metrics
- [ ] Prometheus scraping API (Status → Targets shows UP)
- [ ] Grafana datasource configured and working
- [ ] Dashboard loads with data
- [ ] Make prediction → metrics update
- [ ] Submit feedback → feedback metrics update
- [ ] All panels showing data in Grafana

---

**Happy Monitoring!** 📊🎉

For issues, check:

- Prometheus logs: `docker-compose logs prometheus`
- Grafana logs: `docker-compose logs grafana`
- API logs: `docker-compose logs api`
