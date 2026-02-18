# Workflow Builder - FastAPI + Streamlit

A modern AI-powered workflow builder that combines FastAPI backend with Streamlit frontend to create n8n workflows using natural language.

## 🎯 Features

- **AI-Powered Workflow Generation**: Describe your workflow in natural language
- **FastAPI Backend**: High-performance REST API with WebSocket support
- **Streamlit Frontend**: Interactive web interface for workflow building
- **Real-time Updates**: See workflow changes as they're built
- **JSON Export**: Download your workflows as JSON for use with n8n

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Groq API key (for LLM)

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables (create `.env` file):
```env
GROQ_API_KEY=your_groq_api_key_here
```

### Running the Application

#### Method 1: Run Backend and Frontend Separately

**Terminal 1 - Start FastAPI Backend:**
```bash
python main.py
```
The API will be available at `http://localhost:8000`

**Terminal 2 - Start Streamlit Frontend:**
```bash
streamlit run streamlit_app.py
```
The frontend will open at `http://localhost:8501`

#### Method 2: Run Both with a Script

Create `run_all.py`:
```python
import subprocess
import time
import webbrowser

# Start API
api_process = subprocess.Popen(["python", "main.py"])
time.sleep(2)

# Start Streamlit
streamlit_process = subprocess.Popen(["streamlit", "run", "streamlit_app.py"])
time.sleep(2)

# Open browser
webbrowser.open("http://localhost:8501")

try:
    streamlit_process.wait()
except KeyboardInterrupt:
    api_process.terminate()
    streamlit_process.terminate()
```

Then run:
```bash
python run_all.py
```

## 📡 API Endpoints

### Health Check
```bash
GET /health
```

### Get Node Types
```bash
GET /node-types
```

### Build Workflow
```bash
POST /workflow
Content-Type: application/json

{
  "message": "Create a workflow that checks weather API every hour"
}
```

### Get Workflow
```bash
GET /workflow/{workflow_id}
```

### Execute Workflow
```bash
POST /workflow/{workflow_id}/execute
```

### WebSocket (Real-time)
```
WS /ws/workflow
```

## 🎨 Frontend Features

### Main Interface
- **Input Area**: Describe your workflow
- **Workflow Tab**: View all nodes added
- **Connections Tab**: See how nodes are connected
- **Chat Tab**: Have multi-turn conversations
- **JSON Tab**: Export your workflow as JSON

### Sidebar
- API Status indicator
- API URL configuration
- Available node types browser
- Example prompts

## 📝 Example Prompts

Try these to get started:

1. "Create a workflow that checks a weather API every hour and sends me an email if it's going to rain"
2. "Build a workflow that processes incoming webhooks and stores data in a database"
3. "Create a workflow that scrapes data from a website and sends it via Slack"
4. "Build a workflow that monitors a GitHub repository and sends notifications"

## 🔧 Configuration

### Customize API URL
In Streamlit interface, use the sidebar to change the API URL if running on a different host/port.

### Adjust LLM Provider
Edit `llm_provider.py` to change from Groq to another LLM provider.

### Add Custom Node Types
Modify `node_types.json` to add your custom node definitions.

## 📊 Architecture

```
┌─────────────────┐
│  Streamlit App  │
│  (Port 8501)    │
└────────┬────────┘
         │ HTTP
         ↓
┌─────────────────┐
│  FastAPI Server │
│  (Port 8000)    │
└────────┬────────┘
         │
    ┌────┴─────┬──────────┬─────────────┐
    ↓          ↓          ↓              ↓
   LLM    Node Search  Agents        Tools
  (Groq)  Engine
```

## 🐛 Troubleshooting

### "Cannot connect to API"
- Make sure `python main.py` is running
- Check that port 8000 is not in use
- Verify API URL in Streamlit sidebar

### "API request timed out"
- The LLM might be slow, try again
- Check your internet connection
- Increase timeout in `streamlit_app.py`

### Missing Environment Variables
- Create `.env` file with `GROQ_API_KEY`
- The code will look for it automatically

## 📦 Project Structure

```
workflow_n8n/
├── main.py                 # FastAPI application
├── streamlit_app.py       # Streamlit frontend
├── main.py               # Core orchestrator
├── llm_provider.py       # LLM configuration
├── requirements.txt      # Python dependencies
├── node_types.json       # Available node definitions
├── backend/              # Backend modules
│   ├── agents/          # AI agents
│   ├── chains/          # LLM chains
│   ├── engines/         # Search engines
│   ├── tools/           # Workflow tools
│   ├── types/           # Data types
│   └── utils/           # Utilities
└── README.md            # This file
```

## 🔒 Security Notes

- ⚠️ The current CORS configuration allows all origins. Restrict this in production:
  ```python
  allow_origins=["http://localhost:3000"]  # Your frontend URL
  ```

- ⚠️ Store API keys in environment variables, not in code

- ⚠️ Use authentication/authorization for production deployments

## 📚 API Documentation

Once the API is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🤝 Contributing

Feel free to enhance the application with:
- More node types
- Additional LLM providers
- Database persistence
- Workflow versioning
- Execution capabilities

## 📄 License

This project is open source and available under the MIT License.

## 💡 Tips & Tricks

1. **Be Descriptive**: The more details in your prompt, the better the workflow
2. **Iterate**: Use follow-up messages to refine the workflow
3. **Export**: Download JSON to import into actual n8n
4. **Experiment**: Try different prompts to see various workflow patterns

---

**Happy Workflow Building! 🎉**
