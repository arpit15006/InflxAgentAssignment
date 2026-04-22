# AutoStream — Social-to-Lead Agentic AI Workflow

This repository contains a production-style conversational AI agent that:

- Classifies user intent (greeting vs pricing/product vs high-intent signup)
- Answers product/policy questions using a local RAG knowledge base (FAISS)
- Runs a deterministic, state-driven lead capture workflow with a guarded tool call

The system strictly classifies user input into three intents only:
- `greeting`
- `pricing`
- `high_intent`



## Live Demo

- Frontend (Vercel): https://inflx-agent-assignment-cz64.vercel.app/
- Backend (Railway): https://inflxagentassignment-production.up.railway.app/
- Swagger docs: https://inflxagentassignment-production.up.railway.app/docs

## Demo Video (2–3 minutes)

Add your screen recording link here before submitting:

- Demo video: (https://www.loom.com/share/37cf9eedfd044d1dadbdf0a2ec0ed3a2)

## Features (Must-Haves)

1. **Intent identification**
   - `greeting` → friendly welcome
   - `pricing` → RAG answer grounded in local knowledge base
   - `high_intent` → lead capture flow (asks for name/email/platform)

2. **RAG-powered knowledge retrieval (local)**
   - Knowledge base: [backend/knowledge_base.json](backend/knowledge_base.json)
   - Contains required pricing + policies:
     - Basic: $29/month, 10 videos/month, 720p
     - Pro: $79/month, unlimited videos, 4K, AI captions
     - Policies: no refunds after 7 days; 24/7 support on Pro

   The RAG pipeline uses sentence embeddings to convert knowledge base entries into vectors stored in FAISS.
   User queries are embedded and matched against this vector store to retrieve relevant context, which is then used by the LLM to generate grounded responses.

3. **Tool execution: lead capture (strict guard)**
   - Tool: `mock_lead_capture(name, email, platform)`
   - Only executes after ALL 3 values are collected and validated.

4. **State management (5–6 turns)**
   - Maintains short-term session memory per `session_id`
   - Trims conversation history to a 5–6 turn window

## Architecture

This project uses **LangGraph** because the agent’s behavior is best represented as a deterministic workflow rather than a single “chat completion.” LangGraph provides a clear graph of nodes and conditional routing, which makes the system easier to reason about, test, and extend (for example, adding more intents or inserting moderation/guard rails). The backend exposes a small FastAPI surface (`/chat`, `/health`), and each message is processed through a LangGraph state machine with dedicated nodes for intent detection, RAG answering, lead capture, and an “unknown” fallback.

State is managed using a per-session in-memory store keyed by `session_id`. Each incoming user message is appended to `state["messages"]`, the graph runs once, and the agent response is appended back into the same history. To meet the assignment requirement of retaining memory across 5–6 turns, the session history is trimmed to a fixed-size window after each request. The lead capture flow stores structured fields (`name`, `email`, `platform`) inside the same state object and progresses through stages (`ask_name → ask_email → ask_platform → complete`). The **tool call is guarded**: the backend refuses to execute `mock_lead_capture` unless all required fields are present.

## Why LangGraph over LangChain-only

LangChain alone is not ideal for managing deterministic multi-step workflows. LangGraph enables explicit state transitions and conditional routing, making it more suitable for structured agent flows like lead capture.

## API

### Endpoints

- `GET /health` → health check
- `POST /chat` → main chat endpoint

### Example request

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message":"Hi, tell me your pricing","session_id":"demo-session-1"}'
```

Response:

```json
{"response":"..."}
```

## Running Locally

### Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- A Groq API key (used by `langchain-groq`) — set as `GROQ_API_KEY`

### One-command dev (recommended)

From repo root:

```bash
chmod +x start.sh
./start.sh
```

This starts:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs

### Manual setup

Backend:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

### Backend

- `GROQ_API_KEY` (required)
- `FRONTEND_ORIGINS` (optional): comma-separated allowlist for CORS, e.g.
  `https://inflx-agent-assignment-cz64.vercel.app/,http://localhost:5173`

### Frontend

- `VITE_API_URL` (optional for local dev)
  - default: `http://localhost:8000`
  - set in Vercel to your Railway backend URL

## Guardrails and Validation

- Tool execution is strictly blocked until all required fields (`name`, `email`, `platform`) are collected
- Email format is validated before acceptance
- Invalid or unrelated inputs during lead flow are rejected or redirected
- Interruptions (e.g., policy questions mid-flow) are handled without losing state

## Expected Conversation Flow (Demo Script)

1. Greeting + pricing question
   - User: “Hi, tell me about your pricing.”
   - Agent: answers using RAG (Basic vs Pro)
2. High intent
   - User: “That sounds good, I want the Pro plan for my YouTube channel.”
   - Agent: detects high intent and asks for name → email → platform
3. Tool execution
   - After the user provides all 3 fields, the backend calls `mock_lead_capture()` and prints the required confirmation.

## WhatsApp Integration (Webhook Approach)

To integrate this agent with WhatsApp, I would use the **WhatsApp Business Cloud API** (Meta) with a webhook-based architecture:

1. **Webhook receiver**: expose a public HTTPS endpoint (e.g. `/webhooks/whatsapp`) in FastAPI.
2. **Verification**: implement the GET challenge flow (verify token) required by Meta during webhook setup.
3. **Message ingestion**: on incoming POST events, extract the sender’s WhatsApp `wa_id` and message text.
4. **Session mapping**: use `wa_id` as the `session_id` so each WhatsApp user gets persistent 5–6 turn memory.
5. **Agent invocation**: call the existing `process_message(message, session_id)` and get the agent response.
6. **Reply**: send the response back to WhatsApp using the Cloud API “Send Message” endpoint.
7. **Reliability**: acknowledge webhooks quickly (200 OK), process asynchronously if needed, and implement idempotency using message IDs.
8. **Security**: validate webhook signatures (when available), store API tokens in secrets, rate-limit abusive senders, and log minimally (avoid leaking PII).

This approach keeps the same agent logic while swapping the UI channel from web chat to WhatsApp.

## Limitations

- Session state is stored in-memory and resets on server restart
- RAG is limited to a small local knowledge base
- No persistent database or CRM integration

## Deployment Notes

- Frontend is hosted on Vercel. Set `VITE_API_URL` to the Railway backend URL.
- Backend is hosted on Railway and serves FastAPI on `$PORT` via [backend/Procfile](backend/Procfile).
- If you see CORS errors in the browser, configure `FRONTEND_ORIGINS` on Railway.
