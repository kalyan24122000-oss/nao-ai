/**
 * AI Chatbot - Frontend JavaScript
 * Handles chat functionality, voice input, image upload, and settings
 */

// =============================================================================
// Configuration & State
// =============================================================================

const CONFIG = {
    apiEndpoint: localStorage.getItem('apiEndpoint') || 'http://localhost:8000',
    model: localStorage.getItem('model') || 'deepseek/deepseek-chat',
    temperature: parseFloat(localStorage.getItem('temperature')) || 0.7,
    voiceOutput: localStorage.getItem('voiceOutput') === 'true',
    theme: localStorage.getItem('theme') || 'dark'
};

// Migration: Update old default endpoint to localhost
if (CONFIG.apiEndpoint === 'https://nao-ai.onrender.com/') {
    CONFIG.apiEndpoint = 'http://localhost:8000';
    localStorage.setItem('apiEndpoint', CONFIG.apiEndpoint);
}

const STATE = {
    sessionId: localStorage.getItem('sessionId') || generateSessionId(),
    isRecording: false,
    mediaRecorder: null,
    audioChunks: [],
    currentImage: null,
    imageType: null,
    isProcessing: false,
    messages: []
};

// Save session ID
localStorage.setItem('sessionId', STATE.sessionId);

// =============================================================================
// DOM Elements
// =============================================================================

const elements = {
    // Main containers
    sidebar: document.getElementById('sidebar'),
    messagesContainer: document.getElementById('messagesContainer'),
    welcomeMessage: document.getElementById('welcomeMessage'),

    // Input elements
    messageInput: document.getElementById('messageInput'),
    sendBtn: document.getElementById('sendBtn'),
    voiceBtn: document.getElementById('voiceBtn'),
    imageBtn: document.getElementById('imageBtn'),
    imageInput: document.getElementById('imageInput'),
    imagePreview: document.getElementById('imagePreview'),
    previewImg: document.getElementById('previewImg'),
    removeImage: document.getElementById('removeImage'),

    // Header elements
    menuToggle: document.getElementById('menuToggle'),
    modelSelect: document.getElementById('modelSelect'),
    exportBtn: document.getElementById('exportBtn'),
    newChatBtn: document.getElementById('newChatBtn'),

    // Settings modal
    settingsModal: document.getElementById('settingsModal'),
    settingsBtn: document.getElementById('settingsBtn'),
    closeSettings: document.getElementById('closeSettings'),
    temperatureSlider: document.getElementById('temperatureSlider'),
    temperatureValue: document.getElementById('temperatureValue'),
    voiceOutputToggle: document.getElementById('voiceOutputToggle'),
    apiEndpointInput: document.getElementById('apiEndpoint'),
    saveSettings: document.getElementById('saveSettings'),
    resetSettings: document.getElementById('resetSettings'),
    themeOptions: document.querySelectorAll('.theme-option'),

    // Reasoning modal
    reasoningModal: document.getElementById('reasoningModal'),
    closeReasoning: document.getElementById('closeReasoning'),
    fullReasoningContent: document.getElementById('fullReasoningContent'),

    // Other
    themeToggle: document.getElementById('themeToggle'),
    chatHistory: document.getElementById('chatHistory'),
    toast: document.getElementById('toast'),
    toastMessage: document.getElementById('toastMessage')
};

// =============================================================================
// Utility Functions
// =============================================================================

function generateSessionId() {
    return 'session_' + Math.random().toString(36).substring(2, 15);
}

function formatTime(date) {
    return new Intl.DateTimeFormat('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    }).format(date);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message, type = 'success') {
    elements.toastMessage.textContent = message;
    elements.toast.querySelector('i').className =
        type === 'success' ? 'fas fa-check-circle' :
            type === 'error' ? 'fas fa-exclamation-circle' : 'fas fa-info-circle';
    elements.toast.classList.add('show');
    setTimeout(() => elements.toast.classList.remove('show'), 3000);
}

function autoResizeTextarea() {
    elements.messageInput.style.height = 'auto';
    elements.messageInput.style.height = Math.min(elements.messageInput.scrollHeight, 150) + 'px';
}

// =============================================================================
// Theme Management
// =============================================================================

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    CONFIG.theme = theme;
    localStorage.setItem('theme', theme);

    // Update theme toggle icon
    const icon = elements.themeToggle.querySelector('i');
    icon.className = theme === 'dark' ? 'fas fa-moon' : 'fas fa-sun';

    // Update active state in settings
    elements.themeOptions.forEach(option => {
        option.classList.toggle('active', option.dataset.theme === theme);
    });
}

// Initialize theme
setTheme(CONFIG.theme);

// =============================================================================
// Message Handling
// =============================================================================

function createMessageElement(role, content, reasoning = null, imageUrl = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const time = formatTime(new Date());

    let imageHtml = '';
    if (imageUrl) {
        imageHtml = `<img src="${imageUrl}" alt="Uploaded image" class="message-image">`;
    }

    let reasoningHtml = '';
    if (reasoning && role === 'bot') {
        reasoningHtml = `
            <div class="reasoning-section" onclick="toggleReasoning(this)">
                <div class="reasoning-header">
                    <div class="reasoning-preview">
                        <i class="fas fa-brain"></i>
                        <span>${escapeHtml(reasoning.short)}</span>
                    </div>
                    <div class="reasoning-toggle">
                        <span>View full reasoning</span>
                        <i class="fas fa-chevron-down"></i>
                    </div>
                </div>
            </div>
        `;
        // Store full reasoning as data attribute
        messageDiv.dataset.fullReasoning = reasoning.full;
    }

    messageDiv.innerHTML = `
        <div class="message-avatar">
            <i class="fas ${role === 'user' ? 'fa-user' : 'fa-robot'}"></i>
        </div>
        <div class="message-content">
            ${imageHtml}
            <div class="message-bubble">${formatMessageContent(content)}</div>
            ${reasoningHtml}
            <span class="message-time">${time}</span>
        </div>
    `;

    return messageDiv;
}

function formatMessageContent(content) {
    // Basic markdown-like formatting
    let formatted = escapeHtml(content);

    // Code blocks
    formatted = formatted.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
        return `<pre><code class="language-${lang || 'text'}">${code.trim()}</code></pre>`;
    });

    // Inline code
    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Italic
    formatted = formatted.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Line breaks
    formatted = formatted.replace(/\n/g, '<br>');

    return formatted;
}

function addMessage(role, content, reasoning = null, imageUrl = null) {
    // Hide welcome message
    if (elements.welcomeMessage) {
        elements.welcomeMessage.style.display = 'none';
    }

    const messageElement = createMessageElement(role, content, reasoning, imageUrl);
    elements.messagesContainer.appendChild(messageElement);

    // Scroll to bottom
    elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;

    // Save to state
    STATE.messages.push({ role, content, reasoning, imageUrl, timestamp: new Date() });

    // Text-to-speech for bot messages
    if (role === 'bot' && CONFIG.voiceOutput) {
        speakText(content);
    }

    return messageElement;
}

function showTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot';
    typingDiv.id = 'typingIndicator';
    typingDiv.innerHTML = `
        <div class="message-avatar">
            <i class="fas fa-robot"></i>
        </div>
        <div class="message-content">
            <div class="typing-indicator">
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        </div>
    `;
    elements.messagesContainer.appendChild(typingDiv);
    elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
        indicator.remove();
    }
}

// =============================================================================
// Reasoning Toggle
// =============================================================================

function toggleReasoning(element) {
    const messageDiv = element.closest('.message');
    const fullReasoning = messageDiv.dataset.fullReasoning;

    if (fullReasoning) {
        elements.fullReasoningContent.textContent = fullReasoning;
        elements.reasoningModal.classList.add('active');
    }
}

// Make it global for onclick
window.toggleReasoning = toggleReasoning;

// =============================================================================
// API Communication
// =============================================================================

async function sendMessage(message, imageData = null, imageType = null) {
    if (STATE.isProcessing) return;

    STATE.isProcessing = true;
    elements.sendBtn.disabled = true;

    // Create image URL for display
    let imageUrl = null;
    if (imageData) {
        imageUrl = `data:${imageType};base64,${imageData}`;
    }

    // Add user message
    addMessage('user', message, null, imageUrl);

    // Clear input and image
    elements.messageInput.value = '';
    autoResizeTextarea();
    clearImagePreview();

    // Show typing indicator
    showTypingIndicator();

    try {
        const response = await fetch(`${CONFIG.apiEndpoint}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                session_id: STATE.sessionId,
                model: CONFIG.model,
                temperature: CONFIG.temperature,
                image_data: imageData,
                image_type: imageType
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to get response');
        }

        const data = await response.json();

        // Remove typing indicator
        removeTypingIndicator();

        // Add bot message with reasoning
        addMessage('bot', data.final_answer, {
            short: data.short_reasoning,
            full: data.full_reasoning
        });

        // Update session ID if new
        if (data.session_id) {
            STATE.sessionId = data.session_id;
            localStorage.setItem('sessionId', STATE.sessionId);
        }

        // Refresh chat history in sidebar (no page reload needed)
        loadChatHistory();

    } catch (error) {
        removeTypingIndicator();
        addMessage('bot', `Sorry, I encountered an error: ${error.message}. Please check if the backend server is running.`);
        showToast(error.message, 'error');
    } finally {
        STATE.isProcessing = false;
        elements.sendBtn.disabled = false;
        elements.messageInput.focus();
    }
}

// =============================================================================
// Voice Input (Speech-to-Text)
// =============================================================================

async function startVoiceRecording() {
    try {
        // Check for browser support
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            // Fall back to MediaRecorder
            await startMediaRecording();
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();

        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        STATE.isRecording = true;
        elements.voiceBtn.classList.add('recording');
        elements.voiceBtn.querySelector('i').className = 'fas fa-stop';

        recognition.onresult = (event) => {
            const transcript = Array.from(event.results)
                .map(result => result[0].transcript)
                .join('');
            elements.messageInput.value = transcript;
            autoResizeTextarea();
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            stopVoiceRecording();
            showToast('Voice recognition failed. Please try again.', 'error');
        };

        recognition.onend = () => {
            stopVoiceRecording();
            if (elements.messageInput.value.trim()) {
                // Optionally auto-send
                // elements.sendBtn.click();
            }
        };

        STATE.recognition = recognition;
        recognition.start();
        showToast('Listening...', 'info');

    } catch (error) {
        console.error('Voice recording error:', error);
        showToast('Could not access microphone', 'error');
        stopVoiceRecording();
    }
}

async function startMediaRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        STATE.mediaRecorder = new MediaRecorder(stream);
        STATE.audioChunks = [];

        STATE.mediaRecorder.ondataavailable = (event) => {
            STATE.audioChunks.push(event.data);
        };

        STATE.mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(STATE.audioChunks, { type: 'audio/webm' });
            await transcribeAudio(audioBlob);
            stream.getTracks().forEach(track => track.stop());
        };

        STATE.isRecording = true;
        elements.voiceBtn.classList.add('recording');
        elements.voiceBtn.querySelector('i').className = 'fas fa-stop';
        STATE.mediaRecorder.start();
        showToast('Recording...', 'info');

    } catch (error) {
        console.error('Media recording error:', error);
        showToast('Could not access microphone', 'error');
    }
}

function stopVoiceRecording() {
    STATE.isRecording = false;
    elements.voiceBtn.classList.remove('recording');
    elements.voiceBtn.querySelector('i').className = 'fas fa-microphone';

    if (STATE.recognition) {
        STATE.recognition.stop();
        STATE.recognition = null;
    }

    if (STATE.mediaRecorder && STATE.mediaRecorder.state === 'recording') {
        STATE.mediaRecorder.stop();
    }
}

async function transcribeAudio(audioBlob) {
    try {
        const formData = new FormData();
        formData.append('file', audioBlob, 'recording.webm');

        const response = await fetch(`${CONFIG.apiEndpoint}/transcribe`, {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const data = await response.json();
            if (data.text) {
                elements.messageInput.value = data.text;
                autoResizeTextarea();
            }
        }
    } catch (error) {
        console.error('Transcription error:', error);
    }
}

// =============================================================================
// Text-to-Speech
// =============================================================================

function speakText(text) {
    if (!('speechSynthesis' in window)) return;

    // Cancel any ongoing speech
    speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    utterance.pitch = 1;
    utterance.volume = 1;

    speechSynthesis.speak(utterance);
}

// =============================================================================
// Image Upload
// =============================================================================

function handleImageUpload(file) {
    if (!file) return;

    const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!validTypes.includes(file.type)) {
        showToast('Please upload a valid image (JPEG, PNG, GIF, WebP)', 'error');
        return;
    }

    if (file.size > 10 * 1024 * 1024) {
        showToast('Image too large. Maximum size is 10MB', 'error');
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        const base64 = e.target.result.split(',')[1];
        STATE.currentImage = base64;
        STATE.imageType = file.type;

        elements.previewImg.src = e.target.result;
        elements.imagePreview.style.display = 'block';
    };
    reader.readAsDataURL(file);
}

function clearImagePreview() {
    STATE.currentImage = null;
    STATE.imageType = null;
    elements.imagePreview.style.display = 'none';
    elements.previewImg.src = '';
    elements.imageInput.value = '';
}

// =============================================================================
// Chat Export
// =============================================================================

function exportChat() {
    if (STATE.messages.length === 0) {
        showToast('No messages to export', 'error');
        return;
    }

    // Create text content
    let content = 'Nao AI - Chat Export\n';
    content += `Generated: ${new Date().toLocaleString()}\n`;
    content += '='.repeat(50) + '\n\n';

    STATE.messages.forEach(msg => {
        const time = formatTime(msg.timestamp);
        const role = msg.role === 'user' ? 'You' : 'AI';
        content += `[${time}] ${role}:\n${msg.content}\n`;
        if (msg.reasoning) {
            content += `\nReasoning: ${msg.reasoning.short}\n`;
        }
        content += '\n' + '-'.repeat(30) + '\n\n';
    });

    // Download as text file
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat-export-${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    showToast('Chat exported successfully!');
}

// =============================================================================
// Settings Management
// =============================================================================

function loadSettings() {
    elements.modelSelect.value = CONFIG.model;
    elements.temperatureSlider.value = CONFIG.temperature;
    elements.temperatureValue.textContent = CONFIG.temperature;
    elements.voiceOutputToggle.checked = CONFIG.voiceOutput;
    elements.apiEndpointInput.value = CONFIG.apiEndpoint;
}

function saveSettingsToStorage() {
    CONFIG.model = elements.modelSelect.value;
    CONFIG.temperature = parseFloat(elements.temperatureSlider.value);
    CONFIG.voiceOutput = elements.voiceOutputToggle.checked;
    CONFIG.apiEndpoint = elements.apiEndpointInput.value;

    localStorage.setItem('model', CONFIG.model);
    localStorage.setItem('temperature', CONFIG.temperature);
    localStorage.setItem('voiceOutput', CONFIG.voiceOutput);
    localStorage.setItem('apiEndpoint', CONFIG.apiEndpoint);

    elements.settingsModal.classList.remove('active');
    showToast('Settings saved!');
}

function resetSettingsToDefaults() {
    elements.temperatureSlider.value = 0.7;
    elements.temperatureValue.textContent = '0.7';
    elements.voiceOutputToggle.checked = false;
    elements.apiEndpointInput.value = 'http://localhost:8000';
    elements.modelSelect.value = 'deepseek/deepseek-chat';
    setTheme('dark');
}

// =============================================================================
// New Chat
// =============================================================================

function startNewChat() {
    STATE.sessionId = generateSessionId();
    STATE.messages = [];
    localStorage.setItem('sessionId', STATE.sessionId);

    // Clear messages
    elements.messagesContainer.innerHTML = '';

    // Show welcome message
    if (elements.welcomeMessage) {
        elements.welcomeMessage.style.display = 'flex';
        elements.messagesContainer.appendChild(elements.welcomeMessage);
    }

    showToast('Started new chat');
}

// =============================================================================
// Event Listeners
// =============================================================================

// Send message
elements.sendBtn.addEventListener('click', () => {
    const message = elements.messageInput.value.trim();
    if (message || STATE.currentImage) {
        sendMessage(
            message || 'What is in this image?',
            STATE.currentImage,
            STATE.imageType
        );
    }
});

// Enter to send
elements.messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        elements.sendBtn.click();
    }
});

// Auto-resize textarea
elements.messageInput.addEventListener('input', autoResizeTextarea);

// Voice button
elements.voiceBtn.addEventListener('click', () => {
    if (STATE.isRecording) {
        stopVoiceRecording();
    } else {
        startVoiceRecording();
    }
});

// Image upload
elements.imageBtn.addEventListener('click', () => {
    elements.imageInput.click();
});

elements.imageInput.addEventListener('change', (e) => {
    if (e.target.files[0]) {
        handleImageUpload(e.target.files[0]);
    }
});

elements.removeImage.addEventListener('click', clearImagePreview);

// Model selection
elements.modelSelect.addEventListener('change', (e) => {
    CONFIG.model = e.target.value;
    localStorage.setItem('model', CONFIG.model);
});

// Export
elements.exportBtn.addEventListener('click', exportChat);

// New chat
elements.newChatBtn.addEventListener('click', startNewChat);

// Settings modal
elements.settingsBtn.addEventListener('click', () => {
    loadSettings();
    elements.settingsModal.classList.add('active');
});

elements.closeSettings.addEventListener('click', () => {
    elements.settingsModal.classList.remove('active');
});

elements.saveSettings.addEventListener('click', saveSettingsToStorage);
elements.resetSettings.addEventListener('click', resetSettingsToDefaults);

// Temperature slider
elements.temperatureSlider.addEventListener('input', (e) => {
    elements.temperatureValue.textContent = e.target.value;
});

// Theme options in settings
elements.themeOptions.forEach(option => {
    option.addEventListener('click', () => {
        setTheme(option.dataset.theme);
    });
});

// Theme toggle button
elements.themeToggle.addEventListener('click', () => {
    setTheme(CONFIG.theme === 'dark' ? 'light' : 'dark');
});

// Reasoning modal
elements.closeReasoning.addEventListener('click', () => {
    elements.reasoningModal.classList.remove('active');
});

// Close modals on overlay click
document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', () => {
        overlay.closest('.modal').classList.remove('active');
    });
});

// Mobile sidebar
elements.menuToggle.addEventListener('click', () => {
    elements.sidebar.classList.toggle('open');
});

// Close sidebar when clicking outside on mobile
document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768 &&
        !elements.sidebar.contains(e.target) &&
        !elements.menuToggle.contains(e.target)) {
        elements.sidebar.classList.remove('open');
    }
});

// Drag and drop for images
elements.messagesContainer.addEventListener('dragover', (e) => {
    e.preventDefault();
    e.stopPropagation();
});

elements.messagesContainer.addEventListener('drop', (e) => {
    e.preventDefault();
    e.stopPropagation();

    const files = e.dataTransfer.files;
    if (files.length > 0 && files[0].type.startsWith('image/')) {
        handleImageUpload(files[0]);
    }
});

// =============================================================================
// Initialization
// =============================================================================

// Auth
// Auth
let isRegistering = false;

function checkLogin() {
    const isLoggedIn = !!localStorage.getItem('authToken');
    const user = JSON.parse(localStorage.getItem('user') || '{}');

    // Toggle header elements
    const authButtons = document.getElementById('headerAuthButtons');
    const userProfile = document.getElementById('headerUserProfile');
    const userName = document.getElementById('headerUserName');

    if (authButtons && userProfile) {
        if (isLoggedIn) {
            authButtons.style.display = 'none';
            userProfile.style.display = 'flex';
            if (userName) userName.textContent = user.name || 'User';
        } else {
            authButtons.style.display = 'flex';
            userProfile.style.display = 'none';
        }
    }

    // Hide modal if logged in (safety check)
    if (isLoggedIn) {
        document.getElementById('loginModal').style.display = 'none';
    }
}

// Auth Event Listeners
document.getElementById('toggleAuthMode')?.addEventListener('click', (e) => {
    e.preventDefault();
    isRegistering = !isRegistering;
    updateAuthModalState();
});

document.getElementById('authForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    const name = document.getElementById('registerName').value;

    if (!email || !password) {
        showToast('Please fill in all fields', 'error');
        return;
    }
    if (isRegistering && !name) {
        showToast('Please enter your name', 'error');
        return;
    }

    const btn = document.getElementById('authSubmitBtn');
    btn.disabled = true;
    btn.textContent = 'Processing...';

    const endpoint = isRegistering ? '/auth/register' : '/auth/login';
    const payload = isRegistering ? { email, password, name } : { email, password };

    try {
        const res = await fetch(`${CONFIG.apiEndpoint}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (data.success || res.ok) {
            localStorage.setItem('authToken', 'true');
            localStorage.setItem('user', JSON.stringify(data.user));
            document.getElementById('loginModal').style.display = 'none';
            showToast(`Welcome, ${data.user.name}!`);
            checkLogin(); // Update UI
        } else {
            showToast(data.detail || 'Authentication failed', 'error');
            document.getElementById('loginModal').classList.add('shake');
            setTimeout(() => document.getElementById('loginModal').classList.remove('shake'), 500);
        }
    } catch (err) {
        showToast('Server connection error', 'error');
        console.error(err);
    } finally {
        btn.disabled = false;
        btn.textContent = isRegistering ? 'Register' : 'Login';
    }
});

async function init() {
    // Check Auth
    checkLogin();

    // Load settings
    loadSettings();

    // Focus input
    elements.messageInput.focus();

    // Load chat history from database
    await loadChatHistory();

    // Load current session messages if exists
    await loadCurrentSession();

    // Check API health
    fetch(`${CONFIG.apiEndpoint}/`)
        .then(res => res.json())
        .then(data => {
            if (data.status === 'online') {
                console.log('Backend connected successfully');
            }
        })
        .catch(err => {
            console.warn('Backend not available:', err);
        });
}

// Load chat history from database
async function loadChatHistory() {
    try {
        const response = await fetch(`${CONFIG.apiEndpoint}/sessions?limit=20`);
        const data = await response.json();

        if (data.sessions && data.sessions.length > 0) {
            elements.chatHistory.innerHTML = '';

            data.sessions.forEach(session => {
                const item = document.createElement('div');
                item.className = 'history-item';
                item.dataset.sessionId = session.id;

                const title = session.title || 'New Chat';
                const messageCount = session.message_count || 0;

                item.innerHTML = `
                    <i class="fas fa-comment"></i>
                    <span class="history-text">${escapeHtml(title.substring(0, 30))}${title.length > 30 ? '...' : ''}</span>
                    <span class="history-count">${messageCount}</span>
                    <button class="delete-chat-btn" onclick="deleteSession('${session.id}', event)">
                        <i class="fas fa-trash"></i>
                    </button>
                `;

                item.addEventListener('click', () => loadSession(session.id));
                elements.chatHistory.appendChild(item);
            });
        }
    } catch (error) {
        console.log('Could not load chat history:', error);
    }
}

// Load a specific session
async function loadSession(sessionId) {
    try {
        const response = await fetch(`${CONFIG.apiEndpoint}/sessions/${sessionId}`);
        const data = await response.json();

        if (data.messages) {
            // Update current session
            STATE.sessionId = sessionId;
            localStorage.setItem('sessionId', sessionId);
            STATE.messages = [];

            // Clear messages container
            elements.messagesContainer.innerHTML = '';
            elements.welcomeMessage.style.display = 'none';

            // Add messages to UI
            data.messages.forEach(msg => {
                addMessage(msg.role, msg.content, msg.reasoning);
            });

            // Update active state in sidebar
            document.querySelectorAll('.history-item').forEach(item => {
                item.classList.toggle('active', item.dataset.sessionId === sessionId);
            });

            showToast('Chat loaded!');
        }
    } catch (error) {
        console.error('Could not load session:', error);
        showToast('Error loading chat', 'error');
    }
}

// Load current session if exists
async function loadCurrentSession() {
    const currentSessionId = STATE.sessionId;
    try {
        const response = await fetch(`${CONFIG.apiEndpoint}/sessions/${currentSessionId}`);
        if (response.ok) {
            const data = await response.json();
            if (data.messages && data.messages.length > 0) {
                elements.welcomeMessage.style.display = 'none';
                data.messages.forEach(msg => {
                    addMessage(msg.role, msg.content, msg.reasoning);
                });
            }
        }
    } catch (error) {
        // Session doesn't exist yet, that's fine
    }
}

// Delete a session
async function deleteSession(sessionId, event) {
    event.stopPropagation();

    if (!confirm('Delete this chat?')) return;

    try {
        await fetch(`${CONFIG.apiEndpoint}/sessions/${sessionId}`, {
            method: 'DELETE'
        });

        // Refresh chat history
        await loadChatHistory();

        // If deleting current session, start new chat
        if (sessionId === STATE.sessionId) {
            startNewChat();
        }

        showToast('Chat deleted!');
    } catch (error) {
        showToast('Error deleting chat', 'error');
    }
}

// Header Auth Buttons
document.getElementById('headerLoginBtn')?.addEventListener('click', () => {
    isRegistering = false;
    updateAuthModalState();
    document.getElementById('loginModal').style.display = 'flex';
    document.getElementById('loginEmail').focus();
});

document.getElementById('headerSignupBtn')?.addEventListener('click', () => {
    isRegistering = true;
    updateAuthModalState();
    document.getElementById('loginModal').style.display = 'flex';
    document.getElementById('registerName').focus();
});

document.getElementById('headerLogoutBtn')?.addEventListener('click', () => {
    if (confirm('Are you sure you want to logout?')) {
        localStorage.removeItem('authToken');
        localStorage.removeItem('user');
        checkLogin();
        showToast('Logged out successfully');
        elements.messagesContainer.innerHTML = ''; // Clear chat on logout? Optional.
        // startNewChat(); // Maybe reset chat
        if (elements.welcomeMessage) elements.welcomeMessage.style.display = 'flex';
    }
});

function updateAuthModalState() {
    document.getElementById('authTitle').textContent = isRegistering ? 'Create Account' : 'Login';
    document.getElementById('authSubmitBtn').textContent = isRegistering ? 'Register' : 'Login';
    document.getElementById('nameGroup').style.display = isRegistering ? 'block' : 'none';
    document.getElementById('authText').textContent = isRegistering ? 'Already have an account? ' : 'New here? ';
    document.getElementById('toggleAuthMode').textContent = isRegistering ? 'Login' : 'Create an account';
}

// Make deleteSession available globally
window.deleteSession = deleteSession;

// Run initialization
init();

// =============================================================================
// Admin Panel
// =============================================================================

const ADMIN_PIN = '2010';
let messageCount = 0;

// Admin elements
const adminElements = {
    adminBtn: document.getElementById('adminBtn'),
    adminPinModal: document.getElementById('adminPinModal'),
    closePinModal: document.getElementById('closePinModal'),
    adminPin: document.getElementById('adminPin'),
    pinError: document.getElementById('pinError'),
    submitPin: document.getElementById('submitPin'),
    adminModal: document.getElementById('adminModal'),
    closeAdmin: document.getElementById('closeAdmin'),
    closeAdminBtn: document.getElementById('closeAdminBtn'),
    totalMessages: document.getElementById('totalMessages'),
    totalSessions: document.getElementById('totalSessions'),
    currentModel: document.getElementById('currentModel'),
    adminDefaultModel: document.getElementById('adminDefaultModel'),
    adminApiEndpoint: document.getElementById('adminApiEndpoint'),
    maxMessages: document.getElementById('maxMessages'),
    rateLimit: document.getElementById('rateLimit'),
    clearAllChats: document.getElementById('clearAllChats'),
    resetSystem: document.getElementById('resetSystem'),
    saveAdminSettings: document.getElementById('saveAdminSettings')
};

// Track message count
function updateMessageCount() {
    messageCount++;
    if (adminElements.totalMessages) {
        adminElements.totalMessages.textContent = messageCount;
    }
}

// Update current model display
function updateCurrentModelDisplay() {
    if (adminElements.currentModel) {
        const modelName = CONFIG.model.split('/').pop().split(':')[0];
        adminElements.currentModel.textContent = modelName.charAt(0).toUpperCase() + modelName.slice(1);
    }
}

// Open PIN modal
if (adminElements.adminBtn) {
    adminElements.adminBtn.addEventListener('click', () => {
        adminElements.adminPinModal.classList.add('active');
        adminElements.adminPin.value = '';
        adminElements.pinError.style.display = 'none';
        adminElements.adminPin.focus();
    });
}

// Close PIN modal
if (adminElements.closePinModal) {
    adminElements.closePinModal.addEventListener('click', () => {
        adminElements.adminPinModal.classList.remove('active');
    });
}

// Submit PIN
function verifyPin() {
    const enteredPin = adminElements.adminPin.value;

    if (enteredPin === ADMIN_PIN) {
        adminElements.adminPinModal.classList.remove('active');
        openAdminPanel();
    } else {
        adminElements.pinError.style.display = 'block';
        adminElements.adminPin.value = '';
        adminElements.adminPin.focus();
    }
}

if (adminElements.submitPin) {
    adminElements.submitPin.addEventListener('click', verifyPin);
}

// Enter key on PIN input
if (adminElements.adminPin) {
    adminElements.adminPin.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            verifyPin();
        }
    });
}

// Open Admin Panel
function openAdminPanel() {
    // Update stats
    if (adminElements.totalMessages) {
        adminElements.totalMessages.textContent = STATE.messages.length;
    }
    if (adminElements.totalSessions) {
        adminElements.totalSessions.textContent = '1';
    }
    updateCurrentModelDisplay();

    // Load current settings
    if (adminElements.adminDefaultModel) {
        adminElements.adminDefaultModel.value = CONFIG.model;
    }
    if (adminElements.adminApiEndpoint) {
        adminElements.adminApiEndpoint.value = CONFIG.apiEndpoint;
    }

    adminElements.adminModal.classList.add('active');
}

// Close Admin Panel
if (adminElements.closeAdmin) {
    adminElements.closeAdmin.addEventListener('click', () => {
        adminElements.adminModal.classList.remove('active');
    });
}

if (adminElements.closeAdminBtn) {
    adminElements.closeAdminBtn.addEventListener('click', () => {
        adminElements.adminModal.classList.remove('active');
    });
}

// Save Admin Settings
if (adminElements.saveAdminSettings) {
    adminElements.saveAdminSettings.addEventListener('click', () => {
        // Update default model
        if (adminElements.adminDefaultModel) {
            CONFIG.model = adminElements.adminDefaultModel.value;
            elements.modelSelect.value = CONFIG.model;
            localStorage.setItem('model', CONFIG.model);
        }

        // Update API endpoint
        if (adminElements.adminApiEndpoint) {
            CONFIG.apiEndpoint = adminElements.adminApiEndpoint.value;
            localStorage.setItem('apiEndpoint', CONFIG.apiEndpoint);
        }

        // Save other settings
        if (adminElements.maxMessages) {
            localStorage.setItem('maxMessages', adminElements.maxMessages.value);
        }
        if (adminElements.rateLimit) {
            localStorage.setItem('rateLimit', adminElements.rateLimit.value);
        }

        updateCurrentModelDisplay();
        showToast('Admin settings saved!');
        adminElements.adminModal.classList.remove('active');
    });
}

// Clear All Chats
if (adminElements.clearAllChats) {
    adminElements.clearAllChats.addEventListener('click', () => {
        if (confirm('Are you sure you want to clear all chats? This cannot be undone.')) {
            startNewChat();
            messageCount = 0;
            if (adminElements.totalMessages) {
                adminElements.totalMessages.textContent = '0';
            }
            showToast('All chats cleared!');
        }
    });
}

// Reset System
if (adminElements.resetSystem) {
    adminElements.resetSystem.addEventListener('click', () => {
        if (confirm('Are you sure you want to reset the system? This will clear all data and settings.')) {
            // Clear localStorage
            localStorage.clear();

            // Reset to defaults
            CONFIG.apiEndpoint = 'http://localhost:8000';
            CONFIG.model = 'google/gemini-2.0-flash-exp:free';
            CONFIG.temperature = 0.7;
            CONFIG.voiceOutput = false;
            CONFIG.theme = 'dark';

            // Clear messages
            startNewChat();

            // Reset session
            STATE.sessionId = generateSessionId();
            localStorage.setItem('sessionId', STATE.sessionId);

            // Apply theme
            setTheme('dark');

            showToast('System reset complete!');
            adminElements.adminModal.classList.remove('active');

            // Reload page
            setTimeout(() => location.reload(), 1000);
        }
    });
}

// Listen for model changes to update admin display
elements.modelSelect.addEventListener('change', updateCurrentModelDisplay);

// Initialize model display
updateCurrentModelDisplay();

// =============================================================================
// Enhanced Admin Panel Features
// =============================================================================

// Session start time for uptime
const sessionStartTime = Date.now();
let totalTokensEstimate = 0;
let responseTimes = [];

// Admin tab switching
document.querySelectorAll('.admin-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        // Remove active from all tabs
        document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.admin-tab-content').forEach(c => c.classList.remove('active'));

        // Activate clicked tab
        tab.classList.add('active');
        const tabId = `tab-${tab.dataset.tab}`;
        document.getElementById(tabId)?.classList.add('active');
    });
});

// Update uptime display
function updateUptime() {
    const uptime = document.getElementById('uptime');
    if (uptime) {
        const elapsed = Math.floor((Date.now() - sessionStartTime) / 1000);
        if (elapsed < 60) {
            uptime.textContent = `${elapsed}s`;
        } else if (elapsed < 3600) {
            uptime.textContent = `${Math.floor(elapsed / 60)}m`;
        } else {
            uptime.textContent = `${Math.floor(elapsed / 3600)}h`;
        }
    }
}
setInterval(updateUptime, 1000);

// Track tokens estimate
function estimateTokens(text) {
    return Math.ceil(text.length / 4);
}

// Temperature slider in admin
const adminTemp = document.getElementById('adminTemperature');
const adminTempValue = document.getElementById('adminTempValue');
if (adminTemp && adminTempValue) {
    adminTemp.addEventListener('input', () => {
        adminTempValue.textContent = adminTemp.value;
    });
}

// API Key toggle visibility
const toggleApiKey = document.getElementById('toggleApiKey');
const adminApiKey = document.getElementById('adminApiKey');
if (toggleApiKey && adminApiKey) {
    toggleApiKey.addEventListener('click', () => {
        const type = adminApiKey.type === 'password' ? 'text' : 'password';
        adminApiKey.type = type;
        toggleApiKey.querySelector('i').className = type === 'password' ? 'fas fa-eye' : 'fas fa-eye-slash';
    });
}

// Color options
document.querySelectorAll('.color-option').forEach(option => {
    option.addEventListener('click', () => {
        document.querySelectorAll('.color-option').forEach(o => o.classList.remove('active'));
        option.classList.add('active');
        const color = option.dataset.color;
        document.documentElement.style.setProperty('--accent-primary', color);
        localStorage.setItem('accentColor', color);
    });
});

// Export as TXT
document.getElementById('exportTxt')?.addEventListener('click', () => {
    exportChat();
    showToast('Exported as TXT!');
});

// Export as JSON
document.getElementById('exportJson')?.addEventListener('click', () => {
    const data = {
        exportDate: new Date().toISOString(),
        sessionId: STATE.sessionId,
        messages: STATE.messages,
        settings: CONFIG
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat-export-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Exported as JSON!');
});

// Export as Markdown
document.getElementById('exportMd')?.addEventListener('click', () => {
    let content = `# AI Chatbot Export\n\n**Date:** ${new Date().toLocaleString()}\n\n---\n\n`;
    STATE.messages.forEach(msg => {
        const role = msg.role === 'user' ? '**You**' : '**AI**';
        content += `${role}:\n\n${msg.content}\n\n---\n\n`;
    });
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat-export-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Exported as Markdown!');
});

// Backup all data
document.getElementById('backupData')?.addEventListener('click', () => {
    const backup = {
        version: '1.0',
        date: new Date().toISOString(),
        config: CONFIG,
        state: {
            sessionId: STATE.sessionId,
            messages: STATE.messages
        },
        localStorage: { ...localStorage }
    };
    const blob = new Blob([JSON.stringify(backup, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chatbot-backup-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Backup created!');
});

// Restore data
document.getElementById('restoreData')?.addEventListener('click', () => {
    document.getElementById('restoreFile')?.click();
});

document.getElementById('restoreFile')?.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (event) => {
            try {
                const backup = JSON.parse(event.target.result);
                if (backup.version && backup.config) {
                    Object.assign(CONFIG, backup.config);
                    if (backup.state) {
                        STATE.sessionId = backup.state.sessionId;
                        STATE.messages = backup.state.messages || [];
                    }
                    // Restore localStorage
                    if (backup.localStorage) {
                        Object.entries(backup.localStorage).forEach(([key, value]) => {
                            localStorage.setItem(key, value);
                        });
                    }
                    showToast('Backup restored! Reloading...');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showToast('Invalid backup file', 'error');
                }
            } catch (err) {
                showToast('Error reading backup file', 'error');
            }
        };
        reader.readAsText(file);
    }
});

// Test API connection
document.getElementById('testConnection')?.addEventListener('click', async () => {
    try {
        showToast('Testing connection...', 'info');
        const response = await fetch(`${CONFIG.apiEndpoint}/`);
        const data = await response.json();
        if (data.status === 'online') {
            showToast('✅ API connected successfully!');
        } else {
            showToast('API responded but status unclear', 'error');
        }
    } catch (err) {
        showToast('❌ Cannot connect to API', 'error');
    }
});

// Clear cache
document.getElementById('clearCache')?.addEventListener('click', () => {
    if (confirm('Clear all cached data? This will not affect your chat history.')) {
        // Clear specific cache items
        ['accentColor', 'bubbleStyle'].forEach(key => localStorage.removeItem(key));
        showToast('Cache cleared!');
    }
});

// View logs
document.getElementById('viewLogs')?.addEventListener('click', () => {
    const logs = [
        `Session started: ${new Date(sessionStartTime).toLocaleString()}`,
        `Messages sent: ${STATE.messages.length}`,
        `Current model: ${CONFIG.model}`,
        `API endpoint: ${CONFIG.apiEndpoint}`,
        `Theme: ${CONFIG.theme}`,
        `Temperature: ${CONFIG.temperature}`
    ];
    alert('System Logs:\n\n' + logs.join('\n'));
});

// Update session message count
function updateSessionStats() {
    const sessionMsgCount = document.getElementById('sessionMsgCount');
    if (sessionMsgCount) {
        sessionMsgCount.textContent = `${STATE.messages.length} messages`;
    }

    const totalTokens = document.getElementById('totalTokens');
    if (totalTokens) {
        let tokens = 0;
        STATE.messages.forEach(msg => {
            tokens += estimateTokens(msg.content);
        });
        totalTokens.textContent = tokens.toLocaleString();
    }
}

// Override addMessage to track stats
const originalAddMessage = addMessage;
addMessage = function (role, content, reasoning = null, imageUrl = null) {
    const result = originalAddMessage(role, content, reasoning, imageUrl);
    updateSessionStats();
    return result;
};

// Initialize session stats
updateSessionStats();

// Load saved accent color
const savedAccent = localStorage.getItem('accentColor');
if (savedAccent) {
    document.documentElement.style.setProperty('--accent-primary', savedAccent);
    document.querySelectorAll('.color-option').forEach(o => {
        o.classList.toggle('active', o.dataset.color === savedAccent);
    });
}
