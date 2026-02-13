// Enhanced Chatroom JavaScript with Modern Features
const sessionId = 'session_' + Date.now();
let editingMessageId = null;
let selectedMessageId = null;
let currentTheme = localStorage.getItem('theme') || 'light';
let autoScroll = localStorage.getItem('autoScroll') !== 'false';
let soundEnabled = localStorage.getItem('soundEnabled') === 'true';
let fontSize = parseInt(localStorage.getItem('fontSize')) || 14;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeTheme();
    initializeSettings();
    initializeEventListeners();
    document.getElementById('welcomeTime').textContent = getCurrentTime();
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
    
    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);
    
    // Close context menu on click outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.context-menu') && !e.target.closest('.message-bubble')) {
            hideContextMenu();
        }
    });
    
    // Right-click context menu
    document.addEventListener('contextmenu', (e) => {
        const messageBubble = e.target.closest('.message-bubble');
        if (messageBubble) {
            e.preventDefault();
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
    searchBar.style.display = isVisible ? 'none' : 'block';
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

function showContextMenu(e, messageBubble) {
    const menu = document.getElementById('contextMenu');
    selectedMessageId = messageBubble.dataset.messageId;
    
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
}

function hideContextMenu() {
    document.getElementById('contextMenu').style.display = 'none';
    selectedMessageId = null;
}

function copyMessage() {
    if (!selectedMessageId) return;
    
    const messageBubble = document.querySelector(`[data-message-id="${selectedMessageId}"]`);
    if (messageBubble) {
        const bubble = messageBubble.querySelector('.bubble');
        const text = bubble.textContent.trim();
        
        navigator.clipboard.writeText(text).then(() => {
            showNotification('Message copied to clipboard!');
            playSound('success');
        }).catch(() => {
            showNotification('Failed to copy message', 'error');
        });
    }
    
    hideContextMenu();
}

async function downloadCSV(filename) {
    // if (!selectedMessageId) return;
    // const messageBubble = document.querySelector(`[data-message-id="${selectedMessageId}"]`);
    
    try{
        const base_path = "http://192.168.1.53:8080/api/download/" + filename;
        const url = URL.parse(base_path);
        const a = document.createElement('a');
        a.href = url;
        a.download = `attendance.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        showNotification("Downloading csv...");
        playSound('success');
    } catch (error) {
        console.error('Export error:', error);
        showNotification('Failed to download csv', 'error');
    }
    
    hideContextMenu();
}

function reactToMessage() {
    if (!selectedMessageId) return;
    
    const reactions = ['👍', '❤️', '😊', '🎉', '👏'];
    const reaction = reactions[Math.floor(Math.random() * reactions.length)];
    showNotification(`Reacted with ${reaction}!`);
    playSound('success');
    hideContextMenu();
}

function deleteMessage() {
    if (!selectedMessageId) return;
    
    if (confirm('Are you sure you want to delete this message?')) {
        const messageBubble = document.querySelector(`[data-message-id="${selectedMessageId}"]`);
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

function textToSpeech(text) {
    if (!selectedMessageId) return;
    
    const messageBubble = document.querySelector(`[data-message-id="${selectedMessageId}"]`);
    if (messageBubble) {
        const bubble = messageBubble.querySelector('.bubble');
        const text = bubble.textContent.trim();
        // insert function to read
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

    let idx = message.indexOf(".csv") + 4;
    let filename;
    let csvButton = '';
    if (idx > 3 && isUser == false) {
        filename = message.substring(0, idx);
        message = message.substring(idx);
        csvButton = `
            <div class="csv-action">
                <button type="button" class="download-csv" onclick="downloadCSV('${filename}')" title="download csv">Download csv file</button>
            </div>
        `;
    }
    else if (metadata.csv) {
        csvButton = `
            <div class="csv-action">
                <button type="button" class="download-csv" onclick="downloadCSV('${metadata.csv}')" title="download csv">Download csv file</button>
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
                <div class="timestamp">${metadata.timestamp || getCurrentTime()} ${badges}</div>
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
        } else {
            addMessage(data.message, false, data);
            updateStatus('Ready', 'ready');
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