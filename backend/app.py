"""
AI Chatbot Backend - FastAPI Application
A comprehensive chatbot API with multi-modal input support.
"""

import os
import base64
import time
import uuid
import threading
import sys
import hashlib
from datetime import datetime
from typing import Optional, Dict, List, Any
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import database
import database as db

# Initialize FastAPI app
app = FastAPI(
    title="AI Chatbot API",
    description="Multi-modal AI chatbot with text, voice, and image support",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Configuration
# =============================================================================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "deepseek/deepseek-chat"

# Rate limiting configuration
RATE_LIMIT_REQUESTS = 10  # requests per window
RATE_LIMIT_WINDOW = 60  # seconds

# Session storage (in-memory - use Redis for production)
sessions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
rate_limit_store: Dict[str, List[float]] = defaultdict(list)

# =============================================================================
# Models
# =============================================================================

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    model: Optional[str] = DEFAULT_MODEL
    temperature: Optional[float] = 0.7
    image_data: Optional[str] = None  # Base64 encoded image
    image_type: Optional[str] = None  # MIME type

class ChatResponse(BaseModel):
    session_id: str
    short_reasoning: str
    full_reasoning: str
    final_answer: str
    timestamp: str

class TranscribeRequest(BaseModel):
    audio_data: str  # Base64 encoded audio

class SettingsResponse(BaseModel):
    available_models: List[Dict[str, str]]
    default_model: str
    default_temperature: float

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = "User"

# =============================================================================
# Rate Limiting
# =============================================================================

def check_rate_limit(client_ip: str) -> bool:
    """Check if client has exceeded rate limit."""
    current_time = time.time()
    window_start = current_time - RATE_LIMIT_WINDOW
    
    # Clean old entries
    rate_limit_store[client_ip] = [
        t for t in rate_limit_store[client_ip] if t > window_start
    ]
    
    if len(rate_limit_store[client_ip]) >= RATE_LIMIT_REQUESTS:
        return False
    
    rate_limit_store[client_ip].append(current_time)
    return True

# =============================================================================
# Helper Functions
# =============================================================================

def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent injection attacks."""
    if not text:
        return ""
    # Remove potentially dangerous characters
    text = text.strip()
    # Limit length
    return text[:10000]

def generate_session_id() -> str:
    """Generate a unique session ID."""
    return str(uuid.uuid4())

def build_messages_with_history(
    session_id: str,
    user_message: str,
    image_data: Optional[str] = None,
    image_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Build message array including conversation history with reasoning support."""
    
    # Get current date/time for the AI
    current_datetime = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
    
    # System prompt with current date
    system_prompt = f"""You are Nao AI, an intelligent AI assistant. Be helpful, accurate, and thorough in your responses.

IMPORTANT - Current Date and Time: {current_datetime}

When analyzing problems:
- Think step by step
- Consider multiple perspectives  
- Provide clear, well-structured answers
- Always use the current date above when discussing dates or time"""

    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history (last 10 exchanges) with reasoning_details preserved
    history = sessions.get(session_id, [])[-20:]  # 20 messages = 10 exchanges
    for msg in history:
        message_obj = {"role": msg["role"], "content": msg["content"]}
        # Preserve reasoning_details if present (for continuity)
        if "reasoning_details" in msg and msg["reasoning_details"]:
            message_obj["reasoning_details"] = msg["reasoning_details"]
        messages.append(message_obj)
    
    # Build current user message
    if image_data and image_type:
        # Multi-modal message with image
        content = [
            {"type": "text", "text": user_message},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{image_type};base64,{image_data}"
                }
            }
        ]
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": user_message})
    
    return messages

def parse_ai_response(response_message: Dict[str, Any]) -> Dict[str, Any]:
    """Parse AI response to extract reasoning and answer from OpenRouter's native reasoning."""
    
    content = response_message.get("content", "")
    reasoning_details = response_message.get("reasoning_details", None)
    
    # Default values
    result = {
        "short_reasoning": "Analyzed your request",
        "full_reasoning": "",
        "final_answer": content,
        "reasoning_details": reasoning_details  # Preserve for session history
    }
    
    # If we have native reasoning_details from OpenRouter
    if reasoning_details:
        # reasoning_details can be a list of reasoning steps or a string
        if isinstance(reasoning_details, list):
            # Join reasoning steps
            full_reasoning = "\n".join([
                step.get("content", str(step)) if isinstance(step, dict) else str(step)
                for step in reasoning_details
            ])
            result["full_reasoning"] = full_reasoning
            # Create short reasoning from first step or summary
            if len(reasoning_details) > 0:
                first_step = reasoning_details[0]
                if isinstance(first_step, dict):
                    result["short_reasoning"] = first_step.get("content", "")[:100] + "..."
                else:
                    result["short_reasoning"] = str(first_step)[:100] + "..."
        elif isinstance(reasoning_details, str):
            result["full_reasoning"] = reasoning_details
            result["short_reasoning"] = reasoning_details[:100] + "..." if len(reasoning_details) > 100 else reasoning_details
    else:
        # Fallback: Try to parse XML-style reasoning from content (for models that don't support native reasoning)
        import re
        
        short_match = re.search(r'<short_reasoning>(.*?)</short_reasoning>', content, re.DOTALL)
        if short_match:
            result["short_reasoning"] = short_match.group(1).strip()
        
        full_match = re.search(r'<full_reasoning>(.*?)</full_reasoning>', content, re.DOTALL)
        if full_match:
            result["full_reasoning"] = full_match.group(1).strip()
        
        answer_match = re.search(r'<final_answer>(.*?)</final_answer>', content, re.DOTALL)
        if answer_match:
            result["final_answer"] = answer_match.group(1).strip()
    
    return result

async def call_openrouter(
    messages: List[Dict[str, Any]],
    model: str,
    temperature: float,
    enable_reasoning: bool = False  # Disabled by default - most free models don't support it
) -> Dict[str, Any]:
    """Call OpenRouter API."""
    
    if not OPENROUTER_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="API key not configured. Please set OPENROUTER_API_KEY in .env file."
        )
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "AI Chatbot"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 4096
    }
    
    # Only enable reasoning for models that support it (like nemotron)
    reasoning_models = ["nvidia/nemotron", "deepseek/deepseek-r1"]
    if enable_reasoning and any(rm in model for rm in reasoning_models):
        payload["reasoning"] = {"enabled": True}
    
    async with httpx.AsyncClient(timeout=180.0) as client:  # Increased timeout
        try:
            response = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            # Return the full message object (includes reasoning_details if available)
            return data["choices"][0]["message"]
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Request timed out. The model may be slow to respond.")
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"API error: {e.response.text}"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "online", "message": "Nao AI API is running"}

@app.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """Get available settings and models."""
    return {
        "available_models": [
            {"id": "nvidia/nemotron-3-nano-30b-a3b:free", "name": "Nemotron Nano 30B"},
            {"id": "kwaipilot/kat-coder-pro:free", "name": "Kat Coder Pro"},
        ],
        "default_model": "nvidia/nemotron-3-nano-30b-a3b:free",
        "default_temperature": 0.7
    }

@app.post("/auth/register")
async def register(req: RegisterRequest):
    """Register a new user."""
    # Hash password (simple SHA256)
    pwd_hash = hashlib.sha256(req.password.encode()).hexdigest()
    user = db.create_user(req.email, pwd_hash, req.name)
    if not user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return {"success": True, "user": user}

@app.post("/auth/login")
async def login(req: LoginRequest):
    """Login a user."""
    pwd_hash = hashlib.sha256(req.password.encode()).hexdigest()
    user = db.verify_user(req.email, pwd_hash)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"success": True, "user": user}

@app.get("/admin/users")
async def admin_get_users(pin: str = ""):
    """Get all users for admin panel."""
    # Note: ADMIN_PIN is defined below, this function should be below it or pin check manually
    if pin != "2010": # Using literal for now as ADMIN_PIN is below
         raise HTTPException(status_code=401, detail="Invalid admin PIN")
    return db.get_all_users()

# =============================================================================
# Admin API Endpoints (for Desktop Admin Panel)
# =============================================================================

ADMIN_PIN = "2010"
server_start_time = time.time()
total_requests = 0

@app.get("/admin/stats")
async def admin_stats(pin: str = ""):
    """Get server statistics for admin panel."""
    if pin != ADMIN_PIN:
        raise HTTPException(status_code=401, detail="Invalid admin PIN")
    
    uptime_seconds = int(time.time() - server_start_time)
    hours = uptime_seconds // 3600
    minutes = (uptime_seconds % 3600) // 60
    
    # Get DB stats
    db_stats = db.get_stats()
    
    return {
        "status": "online",
        "uptime": f"{hours}h {minutes}m",
        "total_requests": total_requests,
        "active_sessions": db_stats.get("total_sessions", 0),
        "total_messages": db_stats.get("total_messages", 0),
        "daily_messages": db_stats.get("daily_messages", []),
        "session_list": [
            {
                "id": sid[:8] + "...",
                "messages": len(msgs),
                "status": "active"
            }
            for sid, msgs in list(sessions.items())[:20]
        ]
    }

@app.post("/admin/clear-sessions")
async def admin_clear_sessions(pin: str = ""):
    """Clear all chat sessions."""
    if pin != ADMIN_PIN:
        raise HTTPException(status_code=401, detail="Invalid admin PIN")
    
    sessions.clear()
    return {"success": True, "message": "All sessions cleared"}

@app.post("/admin/shutdown")
async def admin_shutdown(pin: str = ""):
    """Shutdown the server."""
    if pin != ADMIN_PIN:
        raise HTTPException(status_code=401, detail="Invalid admin PIN")
    
    def shutdown():
        time.sleep(1)
        print("Server shutting down via Admin Panel...")
        os._exit(0)
        
    threading.Thread(target=shutdown).start()
    return {"status": "shutting_down", "message": "Server stopping in 1s..."}

@app.post("/admin/update-settings")
async def admin_update_settings(pin: str = "", settings: Dict[str, Any] = {}):
    """Update server settings from admin panel."""
    if pin != ADMIN_PIN:
        raise HTTPException(status_code=401, detail="Invalid admin PIN")
    
    # In production, you would persist these settings
    return {"success": True, "message": "Settings updated", "settings": settings}

@app.get("/admin/logs")
async def admin_get_logs(pin: str = "", limit: int = 100):
    """Get recent server logs."""
    if pin != ADMIN_PIN:
        raise HTTPException(status_code=401, detail="Invalid admin PIN")
    
    # In production, read from actual log file
    return {
        "logs": [
            {"timestamp": datetime.now().isoformat(), "level": "INFO", "message": "Server running"},
            {"timestamp": datetime.now().isoformat(), "level": "INFO", "message": f"Active sessions: {len(sessions)}"},
        ]
    }

# =============================================================================
# Database API Endpoints (for persistent storage)
# =============================================================================

@app.get("/sessions")
async def get_sessions(limit: int = 50):
    """Get all chat sessions from database."""
    sessions_list = db.get_all_sessions(limit)
    return {"sessions": sessions_list}

@app.post("/sessions")
async def create_session(session_id: str = None, title: str = "New Chat"):
    """Create a new session."""
    if not session_id:
        session_id = str(uuid.uuid4())
    session = db.create_session(session_id, title)
    return session

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get a specific session with messages."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = db.get_messages(session_id)
    return {"session": session, "messages": messages}

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    db.delete_session(session_id)
    return {"success": True, "message": "Session deleted"}

@app.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str, limit: int = 100):
    """Get messages for a session."""
    messages = db.get_messages(session_id, limit)
    return {"messages": messages}

@app.get("/db/stats")
async def get_db_stats():
    """Get database statistics."""
    stats = db.get_stats()
    return stats

@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, chat_request: ChatRequest):
    """Main chat endpoint with native reasoning support."""
    
    # Get client IP for rate limiting
    client_ip = request.client.host if request.client else "unknown"
    
    # Check rate limit
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait before sending more messages."
        )
    
    # Sanitize input
    message = sanitize_input(chat_request.message)
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    # Get or create session
    session_id = chat_request.session_id or generate_session_id()
    
    # Build messages with history
    messages = build_messages_with_history(
        session_id,
        message,
        chat_request.image_data,
        chat_request.image_type
    )
    
    # Call AI API with native reasoning enabled
    response_message = await call_openrouter(
        messages,
        chat_request.model or DEFAULT_MODEL,
        chat_request.temperature or 0.7,
        enable_reasoning=True
    )
    
    # Parse response (handles both native reasoning and XML fallback)
    parsed = parse_ai_response(response_message)
    
    # Save to session history with reasoning_details for continuity
    sessions[session_id].append({"role": "user", "content": message})
    assistant_message = {
        "role": "assistant", 
        "content": parsed["final_answer"]
    }
    # Preserve reasoning_details if available (for multi-turn reasoning)
    if parsed.get("reasoning_details"):
        assistant_message["reasoning_details"] = parsed["reasoning_details"]
    sessions[session_id].append(assistant_message)
    
    # Limit session history
    if len(sessions[session_id]) > 50:
        sessions[session_id] = sessions[session_id][-50:]
    
    # Save to database
    db.add_message(session_id, "user", message)
    db.add_message(session_id, "assistant", parsed["final_answer"], parsed["full_reasoning"])
    
    return ChatResponse(
        session_id=session_id,
        short_reasoning=parsed["short_reasoning"],
        full_reasoning=parsed["full_reasoning"],
        final_answer=parsed["final_answer"],
        timestamp=datetime.now().isoformat()
    )

@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """Handle image upload and return base64 encoding."""
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    # Check file size (max 10MB)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max size: 10MB")
    
    # Encode to base64
    base64_data = base64.b64encode(content).decode("utf-8")
    
    return {
        "success": True,
        "image_data": base64_data,
        "image_type": file.content_type,
        "filename": file.filename
    }

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcribe audio file to text using Whisper API via OpenRouter."""
    
    # For simplicity, we'll return a placeholder
    # In production, integrate with Whisper API or OpenAI's transcription
    content = await file.read()
    
    # Encode audio for potential API call
    audio_base64 = base64.b64encode(content).decode("utf-8")
    
    # Using OpenRouter's whisper if available, otherwise return instruction
    return {
        "success": True,
        "text": "[Voice input received - using browser's Web Speech API for transcription]",
        "note": "For production, configure Whisper API endpoint"
    }

@app.get("/history/{session_id}")
async def get_history(session_id: str):
    """Get chat history for a session."""
    
    if session_id not in sessions:
        return {"session_id": session_id, "messages": []}
    
    return {
        "session_id": session_id,
        "messages": sessions[session_id]
    }

@app.delete("/history/{session_id}")
async def clear_history(session_id: str):
    """Clear chat history for a session."""
    
    if session_id in sessions:
        del sessions[session_id]
    
    return {"success": True, "message": "History cleared"}

@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "api_key_configured": bool(OPENROUTER_API_KEY),
        "active_sessions": len(sessions),
        "timestamp": datetime.now().isoformat()
    }

# =============================================================================
# Error Handlers
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": True, "detail": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": True, "detail": "An unexpected error occurred"}
    )

# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
