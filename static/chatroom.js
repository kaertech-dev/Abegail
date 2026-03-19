// Enhanced Chatroom JavaScript with Modern Features
const sessionId = 'session_' + Date.now();
let editingMessageId = null;
let selectedMessageId = null;
let selectedBubble = null;
let currentTheme = localStorage.getItem('theme') || 'light';
let autoScroll = localStorage.getItem('autoScroll') !== 'false';
let soundEnabled = localStorage.getItem('soundEnabled') === 'true';
let fontSize = parseInt(localStorage.getItem('fontSize')) || 14;

const t2speech = window.speechSynthesis;
let voices = t2speech.getVoices();
let selectedVoice;
let speechRate = 0.9;

const SpeechRecognition = window.SpeechRecognition;
const recognition = new SpeechRecognition();
recognition.lang = "en-US";
recognition.continuous = true;
recognition.maxAlternatives = 50;
let sttFlag = false;
let utterance = '';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeTheme();
    initializeSettings();
    initializeEventListeners();
    document.getElementById('welcomeTime').innerHTML += getCurrentTime();
    document.getElementById('messageInput').focus();
    
    // Set font size
    document.documentElement.style.setProperty('--base-font-size', `${fontSize}px`);
    document.getElementById('fontSizeSlider').value = fontSize;
    document.getElementById('fontSizeValue').textContent = `${fontSize}px`;
});

function getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
}

function initializeTheme() {
    const theme = localStorage.getItem('theme') || 'light';
    if (theme === 'dark' || (theme === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.setAttribute('data-theme', 'dark');
        document.getElementById('themeToggle').innerHTML = '<i class="fas fa-sun"></i>';
    } else {
        document.documentElement.setAttribute('data-theme', 'light');
        document.getElementById('themeToggle').innerHTML = '<i class="fas fa-moon"></i>';
    }
    document.getElementById('themeSelect').value = theme;
}

function initializeSettings() {
    // Load saved settings
    const savedAutoScroll = localStorage.getItem('autoScroll');
    if (savedAutoScroll !== null) {
        document.getElementById('autoScrollToggle').checked = savedAutoScroll === 'true';
        autoScroll = savedAutoScroll === 'true';
    }
    
    const savedSound = localStorage.getItem('soundEnabled');
    if (savedSound !== null) {
        document.getElementById('soundToggle').checked = savedSound === 'true';
        soundEnabled = savedSound === 'true';
    }
}

function initializeEventListeners() {
    // Theme toggle
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);
    document.getElementById('themeSelect').addEventListener('change', (e) => {
        const theme = e.target.value;
        localStorage.setItem('theme', theme);
        initializeTheme();
    });

    // File upload, trigger after selection
    document.getElementById('file-input').addEventListener('change', uploadFile);
    document.getElementById('cancel-send').addEventListener('click', cancelFile);
    document.getElementById("send-file").addEventListener('click', () => {
        const file_input = document.getElementById('file-input');
        let formData = new FormData();
        formData.append('file',file_input.files[0]);
        
        fetch('/api/upload', {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
                console.log("Submitted file. ", data);
                cancelFile();
            })
            .catch(error => console.error('Error:', error));
        
    });
    
    // Settings panel
    document.getElementById('settingsToggle').addEventListener('click', toggleSettings);
    document.getElementById('settingsClose').addEventListener('click', toggleSettings);
    
    // Search
    document.getElementById('searchToggle').addEventListener('click', toggleSearch);
    document.getElementById('searchClose').addEventListener('click', toggleSearch);
    document.getElementById('searchInput').addEventListener('input', handleSearch);
    
    // Settings controls
    document.getElementById('autoScrollToggle').addEventListener('change', (e) => {
        autoScroll = e.target.checked;
        localStorage.setItem('autoScroll', autoScroll);
    });
    
    document.getElementById('soundToggle').addEventListener('change', (e) => {
        soundEnabled = e.target.checked;
        localStorage.setItem('soundEnabled', soundEnabled);
    });
    
    document.getElementById('fontSizeSlider').addEventListener('input', (e) => {
        fontSize = parseInt(e.target.value);
        document.documentElement.style.setProperty('--base-font-size', `${fontSize}px`);
        document.getElementById('fontSizeValue').textContent = `${fontSize}px`;
        localStorage.setItem('fontSize', fontSize);
    });

    document.getElementById('rateSlider').addEventListener('input', (e) => {
        speechRate = parseFloat(e.target.value);
        document.getElementById('rateValue').textContent = `${speechRate}`;
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);
    
    // Right-click context menu
    document.addEventListener('contextmenu', (e) => {
        const messageBubble = e.target.closest('.bubble');
        if (messageBubble) {
            if (selectedBubble) {
                selectedBubble.style.border = 'none';
                selectedBubble = null;
            }
            e.preventDefault();
            messageBubble.style.border = "1px solid var(--main-contrast)";
            showContextMenu(e, messageBubble);
        }
    });
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const newTheme = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    document.getElementById('themeToggle').innerHTML = newTheme === 'dark' 
        ? '<i class="fas fa-sun"></i>' 
        : '<i class="fas fa-moon"></i>';
    playSound('click');
}

function toggleSettings() {
    const panel = document.getElementById('settingsPanel');
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    playSound('click');
}

function toggleSearch() {
    const searchBar = document.getElementById('searchBar');
    const isVisible = searchBar.style.display !== 'none';
    searchBar.style.display = isVisible ? 'none' : 'flex';
    if (!isVisible) {
        document.getElementById('searchInput').focus();
    } else {
        document.getElementById('searchInput').value = '';
        clearSearchResults();
    }
    playSound('click');
}

function handleSearch(e) {
    const query = e.target.value.toLowerCase().trim();
    if (query.length < 2) {
        clearSearchResults();
        return;
    }
    
    const messages = document.querySelectorAll('.message-bubble');
    const results = [];
    
    messages.forEach((msg, index) => {
        const bubble = msg.querySelector('.bubble');
        if (bubble && bubble.textContent.toLowerCase().includes(query)) {
            results.push({
                index,
                text: bubble.textContent.substring(0, 100),
                element: msg
            });
        }
    });
    
    displaySearchResults(results, query);
}

function displaySearchResults(results, query) {
    const resultsContainer = document.getElementById('searchResults');
    resultsContainer.innerHTML = '';
    
    if (results.length === 0) {
        resultsContainer.innerHTML = '<div class="search-result-item">No results found</div>';
        resultsContainer.classList.add('show');
        return;
    }
    
    results.forEach((result, idx) => {
        const item = document.createElement('div');
        item.className = 'search-result-item';
        item.textContent = `${idx + 1}. ${result.text}...`;
        item.addEventListener('click', () => {
            scrollToMessage(result.element);
            result.element.classList.add('highlight');
            setTimeout(() => result.element.classList.remove('highlight'), 2000);
            toggleSearch();
        });
        resultsContainer.appendChild(item);
    });
    
    resultsContainer.classList.add('show');
}

function clearSearchResults() {
    const resultsContainer = document.getElementById('searchResults');
    resultsContainer.innerHTML = '';
    resultsContainer.classList.remove('show');
}

function scrollToMessage(element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function handleKeyboardShortcuts(e) {
    // Ctrl+F or Cmd+F: Search
    if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
        e.preventDefault();
        toggleSearch();
        return;
    }
    
    // Esc: Close modals
    if (e.key === 'Escape') {
        document.getElementById('searchBar').style.display = 'none';
        document.getElementById('settingsPanel').style.display = 'none';
        hideContextMenu();
        document.getElementById('messageInput').focus();
    }
    
    // Ctrl+K or Cmd+K: Focus input
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        document.getElementById('messageInput').focus();
    }
}

function slideTo(pagename) {
    const centerSlider = document.getElementById('center-piece');
    const webcam = document.getElementById('pageWebcam');
    const aichat = document.getElementById('chatMessages');
    const chart = document.getElementById('pageChart');

    if (pagename == 'webcam') {
        aichat.style.display = 'none';
        chart.style.display = 'none';
        webcam.style.display = 'flex';
    }
    else if (pagename == 'chatroom') {
        chart.style.display = 'none';
        webcam.style.display = 'none';
        aichat.style.display = 'block';
    }
    else if (pagename == 'chart') {
        webcam.style.display = 'none';
        aichat.style.display = 'none';
        chart.style.display = 'block';
    }
}

function clickOut(e) {
    if (!e.target.closest('.context-menu') && e.target.closest('.bubble') !== selectedBubble) {
        hideContextMenu();
    }
}

function showContextMenu(e, messageBubble) {
    const menu = document.getElementById('contextMenu');
    // selectedMessageId = messageBubble.dataset.messageId;
    selectedBubble = messageBubble;
    
    menu.style.display = 'block';
    menu.style.left = `${e.pageX}px`;
    menu.style.top = `${e.pageY}px`;
    
    // Adjust if menu goes off screen
    setTimeout(() => {
        const rect = menu.getBoundingClientRect();
        if (rect.right > window.innerWidth) {
            menu.style.left = `${e.pageX - rect.width}px`;
        }
        if (rect.bottom > window.innerHeight) {
            menu.style.top = `${e.pageY - rect.height}px`;
        }
    }, 0);

    document.addEventListener('click', clickOut);
}

function hideContextMenu() {
    document.getElementById('contextMenu').style.display = 'none';
    selectedMessageId = null;
    selectedBubble.style.border = "none";
    selectedBubble = null;
    document.removeEventListener('click', clickOut);
}

function copyMessage() {
    if (!selectedBubble) return;
    
    // const messageBubble = document.querySelector(`[data-message-id="${selectedMessageId}"]`);
    const insideText = selectedBubble.textContent;
    if (insideText) {
        // const bubble = messageBubble.querySelector('.bubble');
        // const text = bubble.textContent.trim();
        
        navigator.clipboard.writeText(insideText.trim()).then(() => {
            showNotification('Message copied to clipboard!');
            playSound('success');
        }).catch(() => {
            showNotification('Failed to copy message', 'error');
        });
    }
    
    hideContextMenu();
}

function showReacts() {
    const reactItems = document.getElementById("react-items");
    reactItems.style.display = 'flex';
}

function reactToMessage(reaction) {
    if (!selectedBubble) return;
    
    // const reactions = ['👍', '❤️', '😊', '🎉', '👏'];
    // const reaction = reactions[Math.floor(Math.random() * reactions.length)];
    const reactItems = document.getElementById("react-items");
    const chatReact = selectedBubble.nextElementSibling.querySelector("#chatReact");
    let reactList = chatReact.innerText;
    let position = reactList.indexOf(reaction);
    if (position == -1) {
        chatReact.innerText += reaction;
    }
    else {
        const reactArray = reactList.split(reaction);
        let count = parseInt(reactArray[1][0]);
        if (isNaN(count)) {
            chatReact.innerText = reactArray[0] + reaction + '2' + reactArray[1];
        }
        else {
            count += 1;
            chatReact.innerText = reactArray[0] + reaction + count + reactArray[1].substring(1);
        }
    }
    // console.log(reaction);
    showNotification(`Reacted with ${reaction}!`);
    playSound('success');
    reactItems.style.display = 'none';
    hideContextMenu();
}

function deleteMessage() {
    if (!selectedBubble) return;
    
    if (confirm('Are you sure you want to delete this message?')) {
        // const messageBubble = document.querySelector(`[data-message-id="${selectedMessageId}"]`);
        const messageBubble = selectedBubble.closest(".message-bubble")
        if (messageBubble) {
            messageBubble.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => messageBubble.remove(), 300);
            playSound('delete');
        }
    }
    
    hideContextMenu();
}

function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        background: ${type === 'error' ? 'var(--danger-color)' : 'var(--success-color)'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        z-index: 10000;
        animation: slideInRight 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function selectFile() {
    const fileInput = document.getElementById("file-input");
    fileInput.click();
}

function uploadFile() {
    const fileInput = document.getElementById("file-input");
    const filename = fileInput.files[0].name;

    const chatInput = document.getElementById("messageInput");
    chatInput.style.width = '50px';

    const sendFile = document.getElementById("send-file");
    sendFile.innerHTML = "Submit the file: " + filename + "?";
    sendFile.style.display = "flex";

    const cancel = document.getElementById("cancel-send");
    cancel.style.display = "flex";
}

function cancelFile() {
    const sendFile = document.getElementById("send-file");
    sendFile.style.display = "none";
    sendFile.innerHTML = '';

    const cancel = document.getElementById("cancel-send");
    cancel.style.display = "none";
}

async function downloadCSV(filename) {
    try{
        window.location.href = "api/download/" + filename;
        showNotification("Downloading csv...");
        playSound('success');
    } catch (error) {
        console.error('Export error:', error);
        showNotification('Failed to download csv', 'error');
    }
    
    hideContextMenu();
}

async function viewChart(csv_source) {
    try {
        window.open("chart/" + csv_source, "_blank");
        playSound('success');
        
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error parsing file to chart data', 'error');
    }
}

function playSound(type) {
    if (!soundEnabled) return;
    
    // Create audio context for simple beep sounds
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    switch(type) {
        case 'click':
            oscillator.frequency.value = 800;
            gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
            oscillator.start();
            oscillator.stop(audioContext.currentTime + 0.1);
            break;
        case 'success':
            oscillator.frequency.value = 600;
            gainNode.gain.setValueAtTime(0.15, audioContext.currentTime);
            oscillator.start();
            oscillator.stop(audioContext.currentTime + 0.15);
            break;
        case 'delete':
            oscillator.frequency.value = 400;
            gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
            oscillator.start();
            oscillator.stop(audioContext.currentTime + 0.1);
            break;
    }
}


const speechButton = document.getElementById("recordSpeech");
function startRecord() {
    if (sttFlag == false) {
        t2speech.cancel();
        speechButton.innerHTML = '<i class="fa-solid fa-stop"></i>';
        recognition.start();
        sttFlag = true;
        console.log("Start speaking...");
    }
    else {
        recognition.stop();
        sttFlag = false;
        console.log("Speech recognition stopped.")
        speechButton.innerHTML = '<i class="fa-solid fa-microphone"></i>';
    }
}

recognition.addEventListener('result', (event) => {
    const stt_result = event.results[event.resultIndex];
    const transcript = stt_result[0].transcript;
    const confidence = stt_result[0].confidence;
    console.log(`Transcript: ${transcript} (Confidence: ${Math.round(confidence * 100)}%)`);

    const chatInput = document.getElementById("messageInput");
    current_text = chatInput.value;
    chatInput.value = current_text + " " + transcript;
});

recognition.onerror = (event) => {
    console.log("STT Error:", event.error);
}

recognition.onspeechend = () => {
    setTimeout(() => {}, 3000);
    recognition.stop();
    console.log("Speech recognition stopped.");
    sendMessage();
};

// let utterance = '';
const voiceList = document.getElementById("voice-list");
function populateVoices() {
    voices = t2speech.getVoices();
    // console.log(voices);
    voiceList.replaceChildren();
    for (let voice of voices) {
        if (voice.lang == 'en-US' || voice.lang == 'en-GB' || voice.lang == 'en-AU') {
            const option = document.createElement("option");
            option.textContent = `${voice.name}`;
            voiceList.appendChild(option);
            if (voice.name == "Microsoft Aria Online (Natural) - English (United States)") {
                selectedVoice = voice;
                // console.log("Default voice: ", voice.name);
            }
        }
        
    }
    voiceList.value = "Microsoft Aria Online (Natural) - English (United States)";
}

t2speech.onvoiceschanged = populateVoices;

voiceList.addEventListener('change', (e) => {
    // console.log("testing: ", e.target.value);
    for (let voice of voices) {
        if (voice.name == e.target.value) {
            selectedVoice = voice;
            console.log("Changed voice to: ", selectedVoice.name);
            break;
        }
    }
});

function speak(text) {
    utterance = new SpeechSynthesisUtterance(text);
    utterance.voice = selectedVoice;
    utterance.rate = speechRate;
    t2speech.speak(utterance);
}

function textToSpeech() {
    // change the selector since chat bubbles with the same name default to the first
    // if (!selectedMessageId) return;
    if (!selectedBubble) return;
    
    // const messageBubble = document.querySelector(`[data-message-id="${selectedMessageId}"]`);
    const messageBubble = selectedBubble;
    if (messageBubble) {
        t2speech.cancel();
        const bubble = messageBubble.querySelector('.bubble');
        const text = bubble.textContent.trim();
        speak(text);
    }
    
    hideContextMenu();
}

function addMessage(message, isUser = false, metadata = {}) {
    const messagesContainer = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message-bubble ${isUser ? 'user' : 'bot'}`;
    messageDiv.dataset.messageId = metadata.id || `msg_${Date.now()}_${Math.random()}`;
    
    const avatarContent = isUser ? '' : '<img src="/static/images/abegail-removebg-preview.png" alt="Abegail" class="avatar-image">';
    const avatarClass = isUser ? 'user-avatar' : 'bot-avatar';
    
    let badges = '';
    if (metadata.edited) {
        badges += '<span class="badge edited">Edited</span>';
    }
    if (metadata.regenerated) {
        badges += '<span class="badge regenerated">Regenerated</span>';
    }
    if (metadata.response_type === 'activity') {
        badges += '<span class="badge company">Company Data</span>';
    } else if (metadata.response_type === 'attendance') {
        badges += '<span class="badge company">Company Data</span>';
    }else if (metadata.response_type === 'general') {
        badges += '<span class="badge general">General</span>';
    }
    
    const editButton = isUser ? `
        <div class="edit-actions">
            <button class="edit-btn" onclick="startEdit('${messageDiv.dataset.messageId}')" title="Edit message">✏️</button>
        </div>
    ` : '';

    const bubbleClass = metadata.edited ? 'bubble edited' : metadata.regenerated ? 'bubble regenerated' : 'bubble';

    let csvButton = '';
    if (metadata.csv && isUser == false) {
        const chartButton = metadata.with_chart ? `<button type="button" class="download-csv" onclick="viewChart('${metadata.csv}')">View chart</button>` : '';
        csvButton = `
            <div class="csv-action">
                <button type="button" class="download-csv" onclick="downloadCSV('${metadata.csv}')" title="download csv">Download csv file</button>
                ${chartButton}
            </div>
        `;
    }
    
    // Render markdown if available
    let messageContent = escapeHtml(message);
    if (typeof marked !== 'undefined') {
        try {
            messageContent = marked.parse(message);
        } catch (e) {
            console.warn('Markdown parsing failed:', e);
        }
    }
    
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="avatar ${avatarClass}">${avatarContent}</div>
            <div style="flex: 1;">
                <div class="${bubbleClass}" data-original="${escapeHtml(message)}">
                    ${messageContent}
                    ${csvButton}
                </div>
                <div class="timestamp">
                    <div class="reactions" id="chatReact"></div>
                    ${metadata.timestamp || getCurrentTime()} ${badges}
                </div>
            </div>
        </div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    
    if (autoScroll) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    playSound('click');
}

function startEdit(messageId) {
    if (editingMessageId) return;
    
    editingMessageId = messageId;
    const messageDiv = document.querySelector(`[data-message-id="${messageId}"]`);
    const bubble = messageDiv.querySelector('.bubble');
    const originalText = bubble.dataset.original;
    
    bubble.innerHTML = `
        <input type="text" class="edit-input" value="${originalText}" id="editInput" />
        <div class="edit-buttons">
            <button class="save-edit" onclick="saveEdit('${messageId}')">✓ Save</button>
            <button class="cancel-edit" onclick="cancelEdit('${messageId}')">✗ Cancel</button>
        </div>
    `;
    
    document.getElementById('editInput').focus();
}

async function saveEdit(messageId) {
    const newMessage = document.getElementById('editInput').value.trim();
    
    if (!newMessage) {
        alert('Message cannot be empty');
        return;
    }
    
    updateStatus('Regenerating response...', 'processing');
    showTypingIndicator();
    
    try {
        const response = await fetch('/api/edit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: sessionId,
                message_id: messageId,
                new_message: newMessage
            })
        });
        
        const data = await response.json();
        hideTypingIndicator();
        
        if (data.success) {
            const messageDiv = document.querySelector(`[data-message-id="${messageId}"]`);
            const bubble = messageDiv.querySelector('.bubble');
            bubble.className = 'bubble edited';
            bubble.dataset.original = newMessage;
            
            let messageContent = escapeHtml(newMessage);
            if (typeof marked !== 'undefined') {
                try {
                    messageContent = marked.parse(newMessage);
                } catch (e) {}
            }
            
            bubble.innerHTML = `
                ${messageContent}
                <div class="edit-actions">
                    <button class="edit-btn" onclick="startEdit('${messageId}')" title="Edit message">✏️</button>
                </div>
            `;
            
            const timestamp = messageDiv.querySelector('.timestamp');
            timestamp.innerHTML = `${data.user_message.timestamp} <span class="badge edited">Edited</span>`;
            
            const nextBubble = messageDiv.nextElementSibling;
            if (nextBubble && nextBubble.classList.contains('bot')) {
                nextBubble.remove();
            }
            
            addMessage(data.bot_response.message, false, data.bot_response);
            updateStatus('Ready', 'ready');
            playSound('success');
        } else {
            alert('Failed to regenerate response');
            cancelEdit(messageId);
        }
    } catch (error) {
        hideTypingIndicator();
        alert('Error editing message: ' + error.message);
        cancelEdit(messageId);
    }
    
    editingMessageId = null;
}

function cancelEdit(messageId) {
    const messageDiv = document.querySelector(`[data-message-id="${messageId}"]`);
    const bubble = messageDiv.querySelector('.bubble');
    const originalText = bubble.dataset.original;
    
    let messageContent = escapeHtml(originalText);
    if (typeof marked !== 'undefined') {
        try {
            messageContent = marked.parse(originalText);
        } catch (e) {}
    }
    
    bubble.innerHTML = `
        ${messageContent}
        <div class="edit-actions">
            <button class="edit-btn" onclick="startEdit('${messageId}')" title="Edit message">✏️</button>
        </div>
    `;
    
    editingMessageId = null;
}

function showTypingIndicator() {
    const messagesContainer = document.getElementById('chatMessages');
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message-bubble bot';
    typingDiv.id = 'typingIndicator';
    typingDiv.innerHTML = `
        <div class="message-content">
            <div class="avatar bot-avatar"><img src="/static/images/abegail-removebg-preview.png" alt="Abegail" class="avatar-image"></div>
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    messagesContainer.appendChild(typingDiv);
    if (autoScroll) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

function hideTypingIndicator() {
    const typingIndicator = document.getElementById('typingIndicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

function updateStatus(text, status = 'ready') {
    document.getElementById('statusText').textContent = text;
    const indicator = document.getElementById('statusIndicator');
    indicator.className = `status-indicator ${status}`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function sendMessage() {
    if (sttFlag) {
        recognition.stop();
        sttFlag = false;
        console.log("Speech recognition stopped.")
        speechButton.innerHTML = '<i class="fa-solid fa-microphone"></i>';
    }
    
    t2speech.cancel();
    const input = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    const message = input.value.trim();
    
    if (!message) return;
    
    const msgId = `msg_${Date.now()}_${Math.random()}`;
    addMessage(message, true, { id: msgId, timestamp: getCurrentTime() });
    input.value = '';
    
    sendButton.disabled = true;
    input.disabled = true;
    updateStatus('Processing...', 'processing');
    showTypingIndicator();
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            })
        });
        
        const data = await response.json();
        hideTypingIndicator();
        
        if (data.error) {
            addMessage(data.message || 'An error occurred', false, { ...data, response_type: 'error' });
            updateStatus('Error', 'error');
        }
        // else if (data.redirect) {
        //     addMessage(data.message, false, data);
        //     updateStatus('Ready', 'ready');
        //     window.open("webcam", "_blank");
        // }
        else {
            addMessage(data.message, false, data);
            updateStatus('Ready', 'ready');
            setTimeout(function() {
                speak(data.message);
            }, 1000);
            // speak(data.message);
        }
        
    } catch (error) {
        hideTypingIndicator();
        addMessage('Sorry, there was an error connecting to the server. Please try again.', false, { response_type: 'error' });
        updateStatus('Error', 'error');
        console.error('Error:', error);
    } finally {
        sendButton.disabled = false;
        input.disabled = false;
        input.focus();
    }
}

async function clearChat() {
    if (!confirm('Are you sure you want to clear the chat history?')) {
        return;
    }
    
    try {
        await fetch('/api/clear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: sessionId
            })
        });
        
        const messagesContainer = document.getElementById('chatMessages');
        messagesContainer.innerHTML = `
            <div class="message-bubble bot">
                <div class="message-content">
                    <div class="avatar bot-avatar"><img src="/static/images/abegail-removebg-preview.png" alt="Abegail" class="avatar-image"></div>
                    <div>
                        <div class="bubble">Chat cleared! How can I help you?</div>
                        <div class="timestamp">${getCurrentTime()}</div>
                    </div>
                </div>
            </div>
        `;
        updateStatus('Ready', 'ready');
        playSound('success');
        
    } catch (error) {
        console.error('Error clearing chat:', error);
        showNotification('Failed to clear chat', 'error');
    }
}

function handleKeyPress(event) {
    if (event.key === 'Enter' && !editingMessageId) {
        if (event.shiftKey) {
            // Allow new line with Shift+Enter
            return;
        }
        event.preventDefault();
        sendMessage();
    }
}

async function exportChat() {
    try {
        const messages = document.querySelectorAll('.message-bubble');
        let exportText = 'Chat Export - ' + new Date().toLocaleString() + '\n';
        exportText += '='.repeat(50) + '\n\n';
        
        messages.forEach((msg) => {
            const isUser = msg.classList.contains('user');
            const bubble = msg.querySelector('.bubble');
            const timestamp = msg.querySelector('.timestamp');
            
            if (bubble) {
                exportText += `[${timestamp?.textContent || 'Unknown'}] `;
                exportText += `${isUser ? 'You' : 'Abegail'}: `;
                exportText += bubble.textContent.trim() + '\n\n';
            }
        });
        
        const blob = new Blob([exportText], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `chat-export-${Date.now()}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        showNotification('Chat exported successfully!');
        playSound('success');
    } catch (error) {
        console.error('Export error:', error);
        showNotification('Failed to export chat', 'error');
    }
}

// Starts/stops capturing directly from OpenCV
const feedStatus = document.getElementById("feedStatus");
const feedIcon = document.getElementById("toggleFeed");
const videoFeed = document.getElementById("live-feed");
const toggleRecognition = document.getElementById("toggleRecognition");
const recogStatus = document.getElementById("recogStatus");

function toggleFeed() {
    if (feedStatus.checked == true) {
        feedStatus.checked = false;
        feedIcon.innerHTML = '<i class="fa-solid fa-video"></i>';
        feedIcon.title = "Enable video feed";
        videoFeed.style.height = '0';
        // ellipseOverlay.style.display = 'none';
    }
    else if (feedStatus.checked == false) {
        feedStatus.checked = true;
        feedIcon.innerHTML = '<i class="fa-solid fa-video-slash"></i>';
        feedIcon.title = "Disable video feed";
        videoFeed.style.height = '480px';
    }
    
    fetch('/webcam_update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            videoToggle: feedStatus.checked
        })
    })
    .then(response => response.json())
    .then(data => {
        // console.log("Video feed:", feedStatus.checked);
        // Wait 5 seconds before enabling/disabling the buttons
        setTimeout(function(){
            takeShot.disabled = takeShot.disabled ? false : true;
            toggleRecognition.disabled = toggleRecognition.disabled ? false : true;
            // addFace.disabled = addFace.disabled ? false : true;
        }, 5000);
    })
    .catch(error => console.error('Error:', error));
};

// Screenshot with visual feedback
function screenShot() {
    const flash = document.getElementById("flash");
    flash.style.display = 'flex';
    fetch('/webcam_update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            takeScreenshot: true
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log("Screenshot taken.");
        flash.style.display = 'none';
        // if (data.img_src) {
            // shotsHTML = shotsContent.innerHTML;
            // img_title = "title='" + data.img_src.slice(8) + "'/>";
            // shotsContent.innerHTML = "<img src='/screenshots/" + data.img_src + "' alt='screenshot taken through the webcam' " + img_title + shotsHTML;
        // }
    })
    .catch(error => console.error('Error:', error));
}

function startFaceRecog() {
    recogStatus.checked = true;
    console.log("Face Recognition start.");
    toggleRecognition.style.background = 'rgb(177 63 63)';
    toggleRecognition.title = 'Disable facial recognition';

    fetch('/webcam_update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            faceRecog: true
        })
    })
    .then(response => response.json())
    .then(data => {
        // console.log("Detected faces:", data.names);
    })
    .catch(error => console.error('Error:', error));
}

function stopFaceRecog() {
    recogStatus.checked = false;
    toggleRecognition.style.background = 'rgba(197, 197, 197, 0.6)';
    toggleRecognition.title = 'Enable facial recognition';
    meetingFaceRec = false;

    fetch('/webcam_update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            faceRecog: false
        })
    })
    .then(response => response.json())
    .then(data => {
        // console.log("Detected faces:", data.names);
    })
    .catch(error => console.error('Error:', error));
}

// Toggle for face recognition
function toggleRecog() {
    if (recogStatus.checked == true) {
        stopFaceRecog();
    }
    else if (recogStatus.checked == false) {
        startFaceRecog();
    }
};

const fileDrop = document.getElementById("file_dropdown");
let myChart = null;
function populateDropdown() {
    const response = fetch('/getcharts');

    fetch('/getcharts')
    .then(response => response.json())
    .then(data => {
        const list = data.charts;
        list.forEach(element => {
            const option = document.createElement("option");
            option.textContent = `${element}`;
            option.value = element;
            fileDrop.appendChild(option);
        });
    })
    .catch(error => console.error('Error:', error));
}

populateDropdown();

function parseCsv(filename) {
    return fetch(`/chart/${filename}`, {})
    .then(response => response.json())
    .then(data => {
        let labels = data.labels;
        let chartData = data.data;
        let chartName = data.name;
        return new Array(chartName, chartData, labels);
    })
    .catch(error => console.error('Error:', error));
}

fileDrop.addEventListener('change', async () => {
    const filename = fileDrop.value;
    if (myChart) {
        myChart.destroy();
    }
    let valuesArray = await parseCsv(filename);
    console.log("array:", valuesArray);
    const chartName = valuesArray[0];
    const chartData = valuesArray[1];
    const labels = valuesArray[2];
    if (!chartData) {
        console.log("Error creating chart");
    }
    else{
        createChart(chartName, chartData, labels);
    }
});

function createChart(chartName, chartData, labels) {
    // console.log("Creating chart...");
    const data = {
        labels: labels,
        datasets: [{
            label: chartName,
            fill: false,
            backgroundColor: 'rgb(58, 124, 27, 0.8)',
            borderColor: 'rgb(58, 124, 27)',
            borderWidth: 1,
            axis: 'y',
            data: chartData, 
        }],
    };

    const config = {
        type: 'bar',
        data: data,
        options: { 
            maintainAspectRatio: false,
            grouped: false,
            indexAxis: 'y',
            scales: {
                y: {
                    title: {text: 'Date', display: true},
                },
                x: {
                    title: {text: 'Timestamp', display: true}, 
                    reverse: false, min: 0, max: 24,
                    ticks: {maxTicksLimit: 25},
                    grid: {
                        color: function(context) {
                            if (context.tick.value == 7 || context.tick.value == 16) {
                                return 'rgb(190, 40, 40)';
                            }
                            else if (context.tick.value == 8 || context.tick.value == 17) {
                                return 'rgb(40, 40, 190)';
                            }
                            else if (context.tick.value == 9 || context.tick.value == 18) {
                                return 'rgb(40, 190, 40)';
                            }
                            else if (context.tick.value == 10 || context.tick.value == 19) {
                                return 'rgb(240, 240, 40)';
                            }
                            return 'rgb(40, 40, 40, 0.5)';
                        },
                        lineWidth: function(context) {
                            if (context.tick.value >= 7 && context.tick.value <= 10) {
                                return 2;
                            }
                            else if (context.tick.value >= 16 && context.tick.value <= 19) {
                                return 2;
                            }
                            return 1;
                        },
                    },
                }, 
            },
        }
    };

    myChart = new Chart(
        document.getElementById('myChart'),
        config
    );
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        from {
            opacity: 1;
            transform: translateX(0);
        }
        to {
            opacity: 0;
            transform: translateX(100%);
        }
    }
    
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);