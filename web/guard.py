import time

# Simple in-memory limits so a public link can't run up the Anthropic bill.
# (Resets if the process restarts — fine for a demo on a single instance.)
WINDOW_SECONDS = 300     # 5-minute sliding window
MAX_PER_IP = 15          # messages per visitor per window
MAX_PER_DAY = 400        # global messages per day (the cost ceiling)

_hits: dict[str, list[float]] = {}   # ip -> recent message timestamps
_day = {"bucket": -1, "count": 0}    # rolling per-day global counter


# Render sits behind a proxy, so the real visitor is the first X-Forwarded-For entry.
def client_ip(request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "?"


# Return (allowed, message). `message` is a friendly note to show the user when blocked.
def allow(ip: str) -> tuple[bool, str]:
    now = time.time()
    bucket = int(now // 86400)
    if _day["bucket"] != bucket:          # new day -> reset the global counter
        _day["bucket"], _day["count"] = bucket, 0
    if _day["count"] >= MAX_PER_DAY:
        return False, "This public demo has hit its daily usage cap (it runs on a real API key). Please check back tomorrow."
    recent = [t for t in _hits.get(ip, []) if now - t < WINDOW_SECONDS]
    if len(recent) >= MAX_PER_IP:
        return False, "You're going a little fast for this shared demo — give it a minute and try again."
    recent.append(now)
    _hits[ip] = recent
    _day["count"] += 1
    return True, ""
