# Lazy Rabbit Agent

A modern web application for LLM (Large Language Model) interaction with a clean, modular architecture.

## Features

- **Backend**: FastAPI-based REST API with WebSocket support
- **Frontend**: Vue.js 3 with TypeScript and Element Plus UI
- **LLM Integration**: Support for multiple LLM providers
- **Real-time Communication**: WebSocket-based streaming responses
- **Authentication**: JWT-based user authentication
- **Database**: SQLAlchemy ORM with repository pattern
- **Configuration**: Environment-based configuration management
- **AI Coach**: Personal learning coach with 3 modes (coaching, tutoring, quiz), RAG-powered knowledge base, learning goal tracking, and study session logging
- **Knowledge Base**: Upload documents (text/PDF/MD), semantic search via ChromaDB + OpenAI embeddings
- **AI Agent Factory (孵化器)**: A parent agent that compiles one plain-language sentence into a runnable child agent — see below

## AI Agent Factory (孵化器)

Instead of hand-crafting each agent, the factory (父 Agent) compiles a single
sentence into a declarative **AgentSpec** (the 图纸), a human reviews it at a quality
gate, and a generic ReAct runtime assembles and runs it.

Pipeline: `一句话 → 五份图纸 → 人工质检 → 装配子 Agent → ReAct 干活`.

The blueprint has 8 slots (Lilian Weng's *brain + planning/memory/tools* framework
merged with the blog's 0~7 skeleton): `one_liner / role / brain / memory / tools /
policies / prompts / acceptance`. The **decision-rules (policies)** slot is
auto-drafted but must be human-reviewed before approval. Child agents pick tools from
a read-only **tool registry** (high-risk tools like `bash` default to disabled), and
each agent gets its own isolated long-term-memory RAG collection.

Template + filled examples live in [`docs/agent_specs/`](docs/agent_specs/).

Design & spec: `openspec/changes/add-agent-factory/`.

### Factory API

```bash
# 1. Compile one sentence into an AgentSpec draft (five blueprints)
curl -X POST "http://localhost:8000/api/v1/factory/compile" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"one_liner": "帮我做一个日程安排专家：查天气、翻待办、排日程、设提醒"}'

# 2. Review / edit the draft (especially policies) — draft only
curl -X PATCH "http://localhost:8000/api/v1/factory/specs/$SPEC_ID" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"spec": { ... edited AgentSpec ... }}'

# 3. Approve (admin only) — draft → approved, blocks if incomplete
curl -X POST "http://localhost:8000/api/v1/factory/specs/$SPEC_ID/approve" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 4. (optional) Publish to share with others — approved → published
curl -X POST "http://localhost:8000/api/v1/factory/specs/$SPEC_ID/publish" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 5. Assemble and run the child agent (approved/published only)
curl -X POST "http://localhost:8000/api/v1/factory/agents/$SPEC_ID/run" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"input": "帮我安排明天"}'

# List the tool registry (capability catalog)
curl "http://localhost:8000/api/v1/factory/tools" -H "Authorization: Bearer $TOKEN"
```

## Architecture

### Backend Structure
```
backend/
├── app/
│   ├── core/           # Core configuration and utilities
│   ├── services/       # Business logic layer
│   ├── database/       # Database models and repositories
│   ├── api/            # API routes and endpoints
│   ├── user/           # User management
│   ├── prompt/         # Prompt management
│   └── agile/          # Agile workflow features
```

### Frontend Structure
```
frontend/
├── src/
│   ├── components/     # Reusable Vue components
│   ├── views/          # Page components
│   ├── stores/         # Pinia state management
│   ├── services/       # API and WebSocket services
│   ├── types/          # TypeScript type definitions
│   └── router/         # Vue Router configuration
```

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 16+
- npm or yarn

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd lazy-rabbit-agent
   ```

2. **Start the application**
   
   **On Linux/macOS:**
   ```bash
   ./start.sh
   ```
   
   **On Windows:**
   ```cmd
   start.bat
   ```

   The script will:
   - Create virtual environments
   - Install dependencies
   - Generate configuration files
   - Start both backend and frontend services

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Manual Setup

If you prefer to set up manually:

#### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd app
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## Configuration

### Backend Configuration

Create a `.env` file in the `backend/` directory:

```env
# Database Configuration
DATABASE_URL=sqlite:///./app.db
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PWD=password
DB_NAME=lazy_rabbit

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# LLM Configuration

LLM_STREAM=true
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-pro
LLM_API_KEY=sk-xxx

# External APIs
LBS_API_KEY=your-lbs-api-key-here

# Debug
DEBUG_FLAG=false

# AI Coach / RAG Configuration
CHROMA_PERSIST_DIR=data/chroma          # ChromaDB storage directory
LLM_EMBEDDING_MODEL=text-embedding-3-small  # OpenAI embedding model
```

### Frontend Configuration

Create a `.env` file in the `frontend/` directory:

```env
# API Configuration
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

## Usage

### Startup Script Commands

**Linux/macOS:**
```bash
./start.sh [command]
```

**Windows:**
```cmd
start.bat [command]
```

Available commands:
- `start` (default) - Start all services
- `stop` - Stop all services
- `restart` - Restart all services
- `status` - Show service status
- `help` - Show help message

### API Usage

#### Authentication
```bash
# Login
curl -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_username&password=your_password"
```

#### WebSocket Connection
```javascript
const socket = new WebSocket('ws://localhost:8000/ws');
socket.onopen = () => {
  socket.send(JSON.stringify({
    model: "gpt-3.5-turbo",
    messages: [
      { role: "user", content: "Hello!" }
    ]
  }));
};
```

#### AI Coach API

```bash
# Create a learning goal
curl -X POST "http://localhost:8000/api/v1/coach/goals" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"subject": "Python 进阶", "daily_target_minutes": 30}'

# Log a study session
curl -X POST "http://localhost:8000/api/v1/coach/sessions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"goal_id": "...", "duration_minutes": 25, "difficulty": "medium"}'

# Chat with coach (SSE streaming)
curl "http://localhost:8000/api/v1/coach/chat/stream?message=帮我制定学习计划&mode=coach&token=$TOKEN"

# Upload knowledge document
curl -X POST "http://localhost:8000/api/v1/knowledge/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Python Notes", "content": "...", "tags": ["python"]}'

# Semantic search
curl -X POST "http://localhost:8000/api/v1/knowledge/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "如何使用装饰器", "top_k": 5}'
```

## Development

### Backend Development

The backend uses a layered architecture:

- **Routes**: API endpoints and request handling
- **Services**: Business logic and external service integration
- **Repositories**: Data access layer
- **Models**: Database models and schemas

### Frontend Development

The frontend uses Vue.js 3 with:

- **Composition API**: Modern Vue.js development
- **TypeScript**: Type safety and better development experience
- **Pinia**: State management
- **Element Plus**: UI component library

### Adding New Features

1. **Backend**: Add routes, services, and models following the existing patterns
2. **Frontend**: Create components, stores, and services as needed
3. **Types**: Update TypeScript interfaces for new data structures

## Testing

### Backend Testing
```bash
cd backend
source venv/bin/activate
pytest
```

### Frontend Testing
```bash
cd frontend
npm run test
```

## Deployment

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up -d
```

### Production Deployment

1. Set up a production database (PostgreSQL/MySQL)
2. Configure environment variables for production
3. Build the frontend for production
4. Use a production WSGI server (Gunicorn) for the backend
5. Set up reverse proxy (Nginx) for static files and load balancing

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Check the API documentation at http://localhost:8000/docs
- Review the code comments and documentation

## Changelog

### v1.0.0
- Initial release with basic LLM interaction
- WebSocket support for real-time communication
- User authentication and authorization
- Modular architecture with service layer separation
- TypeScript frontend with Vue.js 3