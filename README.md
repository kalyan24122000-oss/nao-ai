# AI Chatbot - Intelligent Assistant

A powerful AI chatbot system with multi-modal input support (text, voice, and image), featuring a beautiful modern UI and FastAPI backend.

![AI Chatbot](https://via.placeholder.com/800x400/1a1a2e/6366f1?text=AI+Chatbot)

## ✨ Features

- **🔤 Text Input** - Standard chat interface with markdown support
- **🎤 Voice Input** - Speech-to-text using Web Speech API
- **🖼️ Image Analysis** - Upload and analyze images with AI
- **🧠 AI Reasoning** - View short preview with expandable full reasoning
- **💾 Session Memory** - Maintains conversation context
- **🌓 Dark/Light Theme** - Customizable appearance
- **⚙️ Settings Panel** - Temperature, model selection, voice output
- **📥 Export Chat** - Download conversation as text file
- **📱 Responsive Design** - Works on desktop and mobile

## 📁 Project Structure

```
ai-chatbot/
├── backend/
│   ├── app.py              # FastAPI application
│   ├── requirements.txt    # Python dependencies
│   └── .env.example        # Environment template
├── frontend/
│   ├── index.html          # Main HTML file
│   ├── style.css           # Styling
│   └── script.js           # Frontend logic
├── .gitignore              # Git ignore file
└── README.md               # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Modern web browser (Chrome, Firefox, Edge, Safari)
- OpenRouter API key (get one at https://openrouter.ai/keys)

### Step 1: Set Up Backend

1. Navigate to the backend directory:
   ```bash
   cd ai-chatbot/backend
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create `.env` file with your API key:
   ```bash
   copy .env.example .env
   ```
   
   Then edit `.env` and add your OpenRouter API key:
   ```
   OPENROUTER_API_KEY=your_actual_api_key_here
   ```

5. Start the server:
   ```bash
   python app.py
   ```
   
   Or using uvicorn:
   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

   The API will be available at `http://localhost:8000`

### Step 2: Open Frontend

Simply open `frontend/index.html` in your web browser:
- Double-click the file, OR
- Right-click → Open with → Your browser, OR
- Use VS Code Live Server extension

### Step 3: Start Chatting!

1. Type a message in the input box
2. Press Enter or click the send button
3. Use the microphone button for voice input
4. Use the image button to upload and analyze images

## 🔧 Configuration

### API Endpoint

If your backend runs on a different port or host, update the API endpoint in Settings:
1. Click the ⚙️ Settings button
2. Change "API Endpoint" to your backend URL
3. Click "Save Settings"

### Available Models

The chatbot supports multiple AI models via OpenRouter:
- DeepSeek Chat (default)
- GPT-4o / GPT-4o Mini
- Claude 3.5 Sonnet / Claude 3 Haiku
- Gemini Pro 1.5
- Llama 3.1 70B

Select your preferred model from the dropdown in the header.

### Temperature

Adjust temperature (0-2) in Settings:
- Lower (0-0.5): More focused, deterministic responses
- Medium (0.7): Balanced creativity and accuracy
- Higher (1-2): More creative, varied responses

## 🔐 Security Features

- ✅ API key stored in `.env` (never exposed to frontend)
- ✅ CORS protection configured
- ✅ Rate limiting (10 requests/minute per IP)
- ✅ Input sanitization
- ✅ Secure session management

## 🌐 Deployment

### Local Development

The setup above is suitable for local development.

### Production Deployment

For production, consider:

1. **Use a production ASGI server:**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app
   ```

2. **Serve frontend with a web server:**
   - Nginx
   - Apache
   - Or use a static hosting service

3. **Environment variables:**
   - Set proper CORS origins
   - Use secure session storage (Redis)
   - Enable HTTPS

4. **Docker deployment:**
   ```dockerfile
   # Example Dockerfile for backend
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/health` | GET | Detailed health status |
| `/settings` | GET | Get available models and settings |
| `/chat` | POST | Send message and get AI response |
| `/upload-image` | POST | Upload and encode image |
| `/transcribe` | POST | Transcribe audio to text |
| `/history/{session_id}` | GET | Get chat history |
| `/history/{session_id}` | DELETE | Clear chat history |

### Chat Request Example

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how are you?",
    "session_id": "my-session",
    "model": "deepseek/deepseek-chat",
    "temperature": 0.7
  }'
```

### Response Format

```json
{
  "session_id": "my-session",
  "short_reasoning": "Analyzing greeting...",
  "full_reasoning": "The user sent a friendly greeting...",
  "final_answer": "Hello! I'm doing great, thank you for asking!",
  "timestamp": "2024-01-15T10:30:00"
}
```

## 🛠️ Troubleshooting

### Backend won't start
- Ensure Python 3.10+ is installed
- Check if port 8000 is available
- Verify all dependencies are installed

### API key error
- Make sure `.env` file exists in the backend folder
- Verify your API key is correct
- Check if you have credits on OpenRouter

### Voice input not working
- Allow microphone access in browser
- Use Chrome or Edge for best compatibility
- Check if HTTPS is being used (required for some browsers)

### CORS errors
- Ensure backend is running on correct port
- Check API endpoint in frontend settings
- Verify CORS origins in `app.py`

## 📄 License

MIT License - feel free to use and modify as needed.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

---

Built with ❤️ using FastAPI and vanilla JavaScript
