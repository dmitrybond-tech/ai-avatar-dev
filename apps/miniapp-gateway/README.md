# Mini App Gateway

FastAPI service that provides fuzzy-match query resolution powered by Notion database.

## Features

- **Notion Integration**: Fetches skills/services data from Notion DB
- **Fuzzy Matching**: Uses rapidfuzz for intelligent query matching
- **Caching**: 10-minute TTL cache to minimize API calls
- **CORS Enabled**: Ready for Mini App frontend integration

## API Endpoints

### `GET /healthz`
Health check endpoint.

**Response:**
```json
{
  "ok": true
}
```

### `POST /reply`
Process user query and return fuzzy-matched answer from Notion DB.

**Request:**
```json
{
  "text": "Python"
}
```

**Response:**
```json
{
  "verdict": "I can help with Python! • Level: Expert • Experience: 5 years",
  "level": "Expert",
  "years": 5,
  "examples": "Django REST APIs, Data pipelines, ML models",
  "cal_link": "https://cal.com/youraccount"
}
```

### `POST /refresh`
Force refresh Notion DB cache.

**Response:**
```json
{
  "ok": true,
  "count": 42,
  "message": "Refreshed 42 skills from Notion"
}
```

## Notion Database Schema

Your Notion database must have the following properties:

| Property | Type | Description |
|----------|------|-------------|
| `name` | Title | Skill/service name (e.g., "Python", "React") |
| `level` | Select | Proficiency level (e.g., "Expert", "Advanced") |
| `years` | Number | Years of experience |
| `tags` | Multi-select | Technology tags for matching |
| `keywords` | Rich text | Additional searchable keywords |
| `examples` | Rich text | Portfolio examples or project descriptions |

## Configuration

Set these environment variables (see `env.miniapp.example`):

- `NOTION_SECRET`: Notion integration secret token
- `NOTION_DB`: Notion database ID
- `CAL_LINK`: Booking calendar link (e.g., Cal.com)
- `CACHE_TTL_SECONDS`: Cache duration (default: 600)
- `GATEWAY_PORT`: Port to run on (default: 8080)

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python main.py

# Or with uvicorn
uvicorn main:app --reload --port 8080
```

## Docker

```bash
# Build
docker build -t miniapp-gateway .

# Run
docker run -p 8080:8080 --env-file .env.miniapp miniapp-gateway
```

## Dependencies

- FastAPI==0.115.0
- uvicorn==0.30.6
- requests==2.32.3
- rapidfuzz==3.9.6
- python-dotenv==1.0.1

