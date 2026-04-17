> **Student Name:** Nguyễn Đức Dũng  
> **Student ID:** 2A202600148  
> **Date:** 17/04/2026

# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

1. API key hardcode trong code, push là lộ
2. Không có config management, phải sử code để đổi config
3. Không có health check
4. Không có graceful shutdown
5. Port cố định

### Exercise 1.3: Comparison table

| Feature      | Basic    | Advanced                 | Tại sao quan trọng?                                                         |
| ------------ | -------- | ------------------------ | --------------------------------------------------------------------------- |
| Config       | Hardcode | Env vars                 | Bảo mật (không lộ keys), linh hoạt (thay đổi config không cần sửa code).    |
| Health check | Không có | Có (Liveness, Readiness) | Platform (Docker/K8s) biết khi nào cần restart hoặc route traffic đến app.  |
| Logging      | print()  | JSON                     | Dễ dàng parse, lọc lỗi và giám sát hệ thống tập trung (ELK, Datadog).       |
| Shutdown     | Đột ngột | Graceful                 | Đảm bảo request dở dang được hoàn tất, tránh mất dữ liệu hoặc lỗi cho user. |

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. Base image: python:3.11 = full Python distribution (~1 GB)
2. Working directory: /app
3. Tại sao COPY requirements.txt trước: để tận dụng Docker layer cache - lần sau cài lại sẽ dùng cache và tiết kiệm thời gian.
4. CMD vs ENTRYPOINT khác nhau thế nào: CMD là command mặc định khi container start, ENTRYPOINT là command được gọi khi container start. CMD có thể bị ghi đè bởi docker run, còn ENTRYPOINT thì không.

### Exercise 2.3: Image size comparison

- Stage 1: tạo môi trường để cài dependencies
- Stage 2: copy dependencies từ stage 1 sang stage 2
- Develop: 424MB
- Production: 56.6MB
- Difference: 86.6%

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- URL: https://lab12-sv-production.up.railway.app
- Screenshot: ![Alt text](railway_app_2.png)

## Part 4: API Security

### Exercise 4.1-4.3: Test results

[Paste your test outputs]

### Exercise 4.4: Cost guard implementation

[Explain your approach]

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes

[Your explanations and test results]

```

---

### 2. Full Source Code - Lab 06 Complete (60 points)

Your final production-ready agent with all files:

```

your-repo/
├── app/
│ ├── main.py # Main application
│ ├── config.py # Configuration
│ ├── auth.py # Authentication
│ ├── rate_limiter.py # Rate limiting
│ └── cost_guard.py # Cost protection
├── utils/
│ └── mock_llm.py # Mock LLM (provided)
├── Dockerfile # Multi-stage build
├── docker-compose.yml # Full stack
├── requirements.txt # Dependencies
├── .env.example # Environment template
├── .dockerignore # Docker ignore
├── railway.toml # Railway config (or render.yaml)
└── README.md # Setup instructions

````

**Requirements:**
-  All code runs without errors
-  Multi-stage Dockerfile (image < 500 MB)
-  API key authentication
-  Rate limiting (10 req/min)
-  Cost guard ($10/month)
-  Health + readiness checks
-  Graceful shutdown
-  Stateless design (Redis)
-  No hardcoded secrets

---

### 3. Service Domain Link

Create a file `DEPLOYMENT.md` with your deployed service information:

```markdown
# Deployment Information

## Public URL
https://your-agent.railway.app

## Platform
Railway / Render / Cloud Run

## Test Commands

### Health Check
```bash
curl https://your-agent.railway.app/health
# Expected: {"status": "ok"}
````

### API Test (with authentication)

```bash
curl -X POST https://your-agent.railway.app/ask \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "question": "Hello"}'
```

## Environment Variables Set

- PORT
- REDIS_URL
- AGENT_API_KEY
- LOG_LEVEL

## Screenshots

- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)

````

##  Pre-Submission Checklist

- [ ] Repository is public (or instructor has access)
- [ ] `MISSION_ANSWERS.md` completed with all exercises
- [ ] `DEPLOYMENT.md` has working public URL
- [ ] All source code in `app/` directory
- [ ] `README.md` has clear setup instructions
- [ ] No `.env` file committed (only `.env.example`)
- [ ] No hardcoded secrets in code
- [ ] Public URL is accessible and working
- [ ] Screenshots included in `screenshots/` folder
- [ ] Repository has clear commit history

---

##  Self-Test

Before submitting, verify your deployment:

```bash
# 1. Health check
curl https://your-app.railway.app/health

# 2. Authentication required
curl https://your-app.railway.app/ask
# Should return 401

# 3. With API key works
curl -H "X-API-Key: YOUR_KEY" https://your-app.railway.app/ask \
  -X POST -d '{"user_id":"test","question":"Hello"}'
# Should return 200

# 4. Rate limiting
for i in {1..15}; do
  curl -H "X-API-Key: YOUR_KEY" https://your-app.railway.app/ask \
    -X POST -d '{"user_id":"test","question":"test"}';
done
# Should eventually return 429
````
