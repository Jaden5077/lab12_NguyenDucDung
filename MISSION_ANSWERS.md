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

#### 4.1

```bash
$ curl http://localhost:8000/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}
```

```bash
$ curl http://localhost:8000/ask -X POST \
  -H "X-API-Key: demo-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
{"detail":"Invalid API key."}
```

```bash
$ curl http://localhost:8000/ask -X POST \
  -H "X-API-Key: my-secret-123" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
{"detail":[{"type":"missing","loc":["query","question"],"msg":"Field required","input":null}]}
```

#### 4.2

```bash
$ curl http://localhost:8000/auth/token -X POST \
  -H "Content-Type: application/json" \
  -d '{"username": "student", "password": "demo123"}'
{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdHVkZW50Iiwicm9sZSI6InVzZXIiLCJpYXQiOjE3NzY0MjAwNDUsImV4cCI6MTc3NjQyMzY0NX0.QkHMK3JvzbPIusv9JYof9XMR7YYEujJhaD1Br0rFbUI","token_type":"bearer","expires_in_minutes":60,"hint":"Include in header: Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."}
```

```bash
$ TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdHVkZW50Iiwicm9sZSI6InVzZXIiLCJpYXQiOjE3NzY0MjAwNDUsImV4cCI6MTc3NjQyMzY0NX0.QkHMK3JvzbPIusv9JYof9XMR7YYEujJhaD1Br0rFbUI"
curl http://localhost:8000/ask -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "Explain JWT"}'
{"question":"Explain JWT","answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic.","usage":{"requests_remaining":9,"budget_remaining_usd":2.1e-05}}
```

#### 4.3

```bash
$ for i in {1..20}; do
  curl http://localhost:8000/ask -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"question": "Test '$i'"}'
  echo ""
done
{"question":"Test 1","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.","usage":{"requests_remaining":8,"budget_remaining_usd":3.7e-05}}
{"question":"Test 2","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.","usage":{"requests_remaining":7,"budget_remaining_usd":5.3e-05}}
{"question":"Test 3","answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic.","usage":{"requests_remaining":6,"budget_remaining_usd":7.4e-05}}
{"question":"Test 4","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.","usage":{"requests_remaining":5,"budget_remaining_usd":9.3e-05}}
{"question":"Test 5","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.","usage":{"requests_remaining":4,"budget_remaining_usd":0.000112}}
{"question":"Test 6","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.","usage":{"requests_remaining":3,"budget_remaining_usd":0.00013}}
{"question":"Test 7","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.","usage":{"requests_remaining":2,"budget_remaining_usd":0.000146}}
{"question":"Test 8","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.","usage":{"requests_remaining":1,"budget_remaining_usd":0.000163}}
{"question":"Test 9","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.","usage":{"requests_remaining":0,"budget_remaining_usd":0.000181}}
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":9}}
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":9}}
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":9}}
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":8}}
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":8}}
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":8}}
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":7}}
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":7}}
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":7}}
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":7}}
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":6}}

```

### Exercise 4.4: Cost guard implementation

Để giải quyết bài toán quản lý ngân sách (Cost Guard) một cách bền vững trong môi trường production, chúng ta chuyển từ lưu trữ in-memory sang sử dụng **Redis**.

**Lợi ích của Redis:**
- **Persistence:** Budget không bị mất khi hop/container bị restart.
- **Shared State:** Nếu chạy nhiều instance của Agent (scaling), tất cả đều check chung một nguồn dữ liệu budget.
- **Performance:** Thao tác đọc/ghi cực nhanh, không làm chậm API.
- **TTL (Time To Live):** Tự động reset dữ liệu cũ (ví dụ sau 32 ngày).

**Mô tả logic:**
1. Tạo một `month_key` dựa trên tháng hiện tại (ví dụ: `2024-04`).
2. Sử dụng key định dạng `budget:{user_id}:{month_key}` để theo dõi chi tiêu của từng user theo từng tháng.
3. Trước mỗi request, lấy chi tiêu hiện tại từ Redis.
4. Nếu chi tiêu hiện tại + chi phí dự kiến > giới hạn ($10), trả về `False` (Blocked).
5. Nếu còn budget, cập nhật chi tiêu mới vào Redis bằng lệnh `incrbyfloat` (nguyên tử) và đặt thời gian hết hạn (expire) để tránh rác dữ liệu.

**Implementation code:**

```python
import redis
from datetime import datetime

# Kết nối tới Redis (thông tin lấy từ environment variables trong thực tế)
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def check_budget(user_id: str, estimated_cost: float) -> bool:
    """
    Kiểm tra xem User còn đủ ngân sách để thực hiện request không.
    Ngân sách tối đa: $10/tháng.
    """
    # 1. Tạo key theo tháng để tự động reset mỗi đầu tháng
    month_key = datetime.now().strftime("%Y-%m")
    redis_key = f"budget:{user_id}:{month_key}"

    # 2. Lấy số tiền đã chi tiêu (mặc định là 0 nếu chưa có)
    current_spent = float(r.get(redis_key) or 0)

    # 3. Kiểm tra nếu vượt quá giới hạn $10
    if current_spent + estimated_cost > 10.0:
        return False

    # 4. Cộng dồn chi phí mới
    r.incrbyfloat(redis_key, estimated_cost)

    # 5. Đặt TTL là 32 ngày (đảm bảo tồn tại qua hết tháng hiện tại)
    r.expire(redis_key, 32 * 24 * 3600)
    
    return True
```

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
