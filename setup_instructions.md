# Verba Setup Instructions

## Prerequisites
- Python >= 3.10.0, < 3.13.0
- Git (for building from source)
- Docker (for Docker deployment)

## Option 1: Install via pip (Easiest)

1. **Create a virtual environment** (Very Important!)
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install Verba**
```bash
pip install goldenverba
```

3. **Launch Verba**
```bash
verba start
```

4. **Access the application**
- Open your browser and go to: http://localhost:8000
- Weaviate will be automatically managed via Embedded Weaviate

## Option 2: Build from Source

1. **Clone the repository**
```bash
git clone https://github.com/weaviate/Verba.git
cd Verba
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate
```

3. **Install in development mode**
```bash
pip install -e .
```

4. **Launch Verba**
```bash
verba start
```

## Option 3: Docker Deployment (Recommended for production)

1. **Clone the repository**
```bash
git clone https://github.com/weaviate/Verba.git
cd Verba
```

2. **Create environment file**
```bash
cp goldenverba/.env.example .env
# Edit .env file with your API keys (see below)
```

3. **Start with Docker Compose**
```bash
docker compose up -d --build
```

4. **Access the applications**
- Verba frontend: http://localhost:8000
- Weaviate instance: http://localhost:8080

## Environment Variables Setup

Create a `.env` file in your project directory with the following variables (only add the ones you need):

```bash
# Weaviate Cloud (if using hosted Weaviate)
# WEAVIATE_URL_VERBA=your-weaviate-url
# WEAVIATE_API_KEY_VERBA=your-api-key

# OpenAI (for GPT models)
# OPENAI_API_KEY=your-openai-key

# Ollama (for local models)
# OLLAMA_URL=http://localhost:11434
# OLLAMA_MODEL=llama3
# OLLAMA_EMBED_MODEL=llama3

# Other providers (optional)
# COHERE_API_KEY=your-cohere-key
# ANTHROPIC_API_KEY=your-anthropic-key
# GROQ_API_KEY=your-groq-key

# Data ingestion services (optional)
# UNSTRUCTURED_API_KEY=your-unstructured-key
# GITHUB_TOKEN=your-github-token
```

## Using with Ollama (Local AI Models)

If you want to use local AI models:

1. **Install Ollama**
   - Download from: https://ollama.com/download

2. **Install a model**
```bash
ollama run llama3
```

3. **Set environment variables**
```bash
export OLLAMA_URL=http://localhost:11434
export OLLAMA_MODEL=llama3
export OLLAMA_EMBED_MODEL=llama3
```

## First Steps After Installation

1. **Select Deployment Mode**
   - Choose between Local, Docker, Weaviate Cloud, or Custom
   - Local uses Embedded Weaviate (not supported on Windows)

2. **Import Your Data**
   - Click "Import Data" in the interface
   - Add files, directories, or URLs
   - Configure chunking and processing options

3. **Start Querying**
   - Use the Chat interface to ask questions about your data
   - Configure RAG pipeline settings as needed

## Troubleshooting

- **Windows users**: Use Docker deployment as Embedded Weaviate isn't supported
- **Port conflicts**: Use `verba start --port 9000` to change the port
- **Ollama connection**: For Docker, use `OLLAMA_URL=http://host.docker.internal:11434`
- **Clear Weaviate data**: Delete `~/.local/share/weaviate` directory

## Optional Extensions

For HuggingFace models:
```bash
pip install goldenverba[huggingface]
```
