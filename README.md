# VidScan — Video Engagement Intelligence

RAG-powered video analysis tool. Compare two YouTube or Instagram Reels by their transcripts, metadata, and engagement stats using **NVIDIA NIM API**.

---

## Stack

| Layer      | Technology                                      |
|------------|-------------------------------------------------|
| Frontend   | React + Vite                                    |
| Backend    | FastAPI + LangGraph                             |
| LLM        | NVIDIA NIM — `meta/llama-3.1-70b-instruct`      |
| Embeddings | NVIDIA NIM — `nvidia/nv-embedqa-e5-v5`          |
| Vector DB  | ChromaDB (local, persistent)                    |
| Transcripts| youtube-transcript-api / yt-dlp / Whisper       |

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- **NVIDIA API key** — get one free at https://build.nvidia.com

---

## Setup & Run

### 1. Clone 

cd vidscan
```

### 2. Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Open .env and set: NVIDIA_API_KEY=nvapi-...your-key-here...

# Start server
uvicorn main:app --reload --port 8000
```

### 3. Frontend (new terminal)

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## Environment Variables

```env
# Required
NVIDIA_API_KEY=nvapi-...your-key-here...

# Optional overrides
CHAT_MODEL=meta/llama-3.1-70b-instruct   # default
EMBED_MODEL=nvidia/nv-embedqa-e5-v5      # default
CHROMA_PERSIST_DIR=./chroma_db           # default
CHROMA_COLLECTION=yt_chunks              # default
```

### Alternative NVIDIA models you can use

**Chat models** (set `CHAT_MODEL`):
- `meta/llama-3.1-70b-instruct` (default, recommended)
- `nvidia/llama-3.1-nemotron-70b-instruct`
- `mistralai/mixtral-8x22b-instruct-v0.1`
- `meta/llama-3.1-8b-instruct` (faster, lighter)

**Embedding models** (set `EMBED_MODEL`):
- `nvidia/nv-embedqa-e5-v5` (default, recommended)
- `nvidia/nv-embed-v1`
- `baai/bge-m3`

---

## Usage

1. Paste a YouTube URL into **Video A** and **Video B** fields
2. Click **⚡ Analyze Both** to ingest both videos
3. Ask questions in the chat panel, e.g.:
   - *"Compare the hooks of both videos"*
   - *"Which video has a higher engagement rate and why?"*
   - *"What CTAs does Video A use?"*

---

## API Endpoints

| Method | Path                  | Description                      |
|--------|-----------------------|----------------------------------|
| POST   | `/api/ingest`         | Ingest a video URL               |
| GET    | `/api/ingest/status`  | Check ingestion status           |
| POST   | `/api/chat/stream`    | Streaming chat (SSE)             |
| GET    | `/health`             | Health check                     |

---

## Architecture

```
Browser (React)
    │
    ▼
FastAPI (port 8000)
    ├── /api/ingest   ──► fetch_transcript + fetch_metadata
    │                      ──► chunk_transcript
    │                      ──► upsert_chunks (NVIDIA embeddings → ChromaDB)
    │
    └── /api/chat/stream ──► retrieve (ChromaDB similarity search)
                             ──► generate (NVIDIA LLM streaming)
```
