# Verba Quick Start Guide - Docker Setup Complete! 🎉

## ✅ Current Status
Your Verba application is now running successfully with Docker!

### Access Points:
- **Verba Frontend**: http://localhost:8000
- **Weaviate Database**: http://localhost:8080

### What's Running:
- ✅ Verba application container
- ✅ Weaviate vector database container
- ✅ Docker networking between containers

## 🚀 Next Steps to Import PDFs

### Option 1: Use OpenAI (Recommended - Most Reliable)

1. **Get an OpenAI API key** from https://platform.openai.com/api-keys

2. **Add your API key to the .env file:**
   ```bash
   # Edit the .env file and uncomment/update this line:
   OPENAI_API_KEY=sk-your-actual-openai-key-here
   ```

3. **Restart the containers:**
   ```bash
   docker compose down
   docker compose up -d
   ```

4. **Import your PDF:**
   - Go to http://localhost:8000
   - Select "Docker" deployment
   - Click "Import Data" → "Add Files"
   - Upload your PDF
   - In the configuration, select "OpenAI" as your embedder
   - Click "Import"

### Option 2: Use HuggingFace (Free, but slower)

1. **Go to http://localhost:8000**
2. **Select "Docker" deployment**
3. **Import your PDF:**
   - Click "Import Data" → "Add Files"
   - Upload your PDF
   - In the configuration, select "HuggingFace" as your embedder
   - Choose a model like "sentence-transformers/all-MiniLM-L6-v2"
   - Click "Import"

### Option 3: Install Ollama for Local Models

1. **Install Ollama on your host system:**
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. **Download a model:**
   ```bash
   ollama run llama3
   ```

3. **Update .env file:**
   ```bash
   # Uncomment these lines in .env:
   OLLAMA_URL=http://host.docker.internal:11434
   OLLAMA_MODEL=llama3
   OLLAMA_EMBED_MODEL=llama3
   ```

4. **Restart containers and import as above**

## 🔧 Managing Your Setup

### Stop the application:
```bash
docker compose down
```

### Start the application:
```bash
docker compose up -d
```

### View logs:
```bash
docker logs verba-verba-1
docker logs verba-weaviate-1
```

### Check container status:
```bash
docker ps
```

## 🎯 Testing Your Setup

1. **Open http://localhost:8000**
2. **Select "Docker" deployment**
3. **Try importing a small PDF first**
4. **Once imported, use the Chat interface to ask questions about your document**

## 🐛 Troubleshooting

If PDF import fails:
1. Check the logs: `docker logs verba-verba-1`
2. Ensure you have a valid API key configured
3. Try with a smaller PDF first
4. Make sure you selected the correct embedder in the import configuration

## 📝 Notes

- The first import might take longer as models are downloaded
- Larger PDFs will take more time to process
- You can import multiple documents and query across all of them
- The data persists in Docker volumes between restarts

Your Verba setup is ready to use! 🚀
