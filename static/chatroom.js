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
    document.getElementById('chatInput').focus();
    
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
    
    // Settings panel
    document.getElementById('settingsToggle').addEventListener('click', toggleSettings);
    document.getElementById('settingsClose').addEventListener('click', toggleSettings);
    
    // Search
    document.getElementById('searchToggle').addEventListener('click', toggleSearch);
    // document.getElementById('searchClose').addEventListener('click', toggleSearch);
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
        document.documentElement.style.fontSize = fontSize;
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
    const searchButton = document.getElementById("searchToggle");

    if (searchBar.style.display === 'none') {
        searchBar.style.display = 'flex';
        searchButton.innerHTML = '<i class="fas fa-times"></i>';
        document.getElementById('searchInput').focus();
    }
    else if (searchBar.style.display === 'flex') {
        document.getElementById('searchInput').value = '';
        clearSearchResults();
        searchBar.style.display = 'none';
        searchButton.innerHTML = '<i class="fas fa-search"></i>';
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
        document.getElementById('right-panel').style.display = 'none';
        document.getElementById('more-inputs').style.display = 'none';
        hideContextMenu();
        document.getElementById('chatInput').focus();
    }
    
    // Ctrl+K or Cmd+K: Focus input
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        document.getElementById('chatInput').focus();
    }
}

function clickOutInput(e) {
    if (!e.target.closest('#chatOptions') && !e.target.closest('#more-inputs')) {
        document.getElementById("more-inputs").style.display = 'none';
        const optionsButton = document.getElementById("chatOptions");
        const icon = optionsButton.children[0];
        icon.style.transform = '';

        document.removeEventListener('click', clickOutInput);
    }
}

function showMoreInputs() {
    const optionsButton = document.getElementById("chatOptions");
    const icon = optionsButton.children[0];
    
    const moreInputs = document.getElementById("more-inputs");
    if (moreInputs.style.display === 'none') {
        moreInputs.style.display = 'flex';
        icon.style.transform = 'rotate(45deg)';

        document.addEventListener('click', clickOutInput);
    }
    else if (moreInputs.style.display === 'flex') {
        moreInputs.style.display = 'none';
        icon.style.transform = '';

        document.removeEventListener('click', clickOutInput);
    }
}

function saveTranscript() {
    const full_text = document.getElementById("meeting-transcript").innerText.trim();

    fetch('/webcam/meeting', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            speech2text: full_text
        })
    })
    .then(response => response.json())
    .then(data => {
        // console.log("Saved transcript.");
        showNotification("Saved transcript.");
    })
    .catch(error => console.error('Error:', error));
}

function clearTranscript() {
    const full_text = document.getElementById("meeting-transcript");
    full_text.innerText = 'Meeting transcript appears here.';
    showNotification("Cleared transcript");
}

const mainGrid = document.getElementById("center-box");
function toggleWebcam() {
    const videoUI = document.getElementById("main-video-ui");
    const chatUI = document.getElementById("chat-messages");

    if (videoUI.style.display == 'none') {
        mainGrid.classList.add('webcamON');
        chatUI.classList.add('reduced');
        setTimeout(() => {
            videoUI.style.display = 'flex';
        }, 500);

        document.getElementById("openWebcam").innerHTML = '<i class="fas fa-times"></i>';
        document.getElementById("openWebcam").style = 'background: var(--bad-button); color: white;'
    }
    else if (videoUI.style.display == 'flex') {
        videoUI.style.display = 'none';
        mainGrid.classList.remove('webcamON');
        chatUI.classList.remove('reduced');

        document.getElementById("openWebcam").innerHTML = '<i class="fa-solid fa-video"></i>';
        document.getElementById("openWebcam").style = 'background: ""; color: ""';
        document.getElementById("cam-options").style.display = 'none';
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
    document.getElementById("react-items").style.display = 'none';
    selectedMessageId = null;
    if (selectedBubble) {
        selectedBubble.style.border = "none";
        selectedBubble = null;
    }
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
    showMoreInputs();
    const fileInput = document.getElementById("file-input");
    fileInput.click();
}

function uploadFile() {
    const fileInput = document.getElementById("file-input");
    const filename = fileInput.files[0].name;

    document.getElementById("statusText").style.display = 'none';

    const fileStatus = document.getElementById("attached-file");
    fileStatus.innerText = `File attached: ${filename}`;
    document.getElementById("status-file").style.display = 'flex';
}

function submitFile() {
    const file_input = document.getElementById('file-input');
    let formData = new FormData();
    formData.append('file',file_input.files[0]);
    
    fetch('/api/upload', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            // console.log("Submitted file.", data);
            showNotification("Submitted file.");
            cancelFile();
        })
        .catch(error => console.error('Error:', error));
}

function cancelFile() {
    const fileStatus = document.getElementById("attached-file");
    fileStatus.innerText = '';
    document.getElementById("status-file").style.display = 'none';

    const fileInput = document.getElementById("file-input");
    fileInput.files = null;

    document.getElementById("statusText").style.display = 'block';
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

const speechButton = document.getElementById("recordSpeech"); //one shot mode
function startRecordOneShot() {
    recognition.lang = "en-US";
    t2speech.cancel();
    speechButton.innerHTML = '<i class="fa-solid fa-stop"></i>';
    if (sttFlag == false) {
        recognition.start();
    }
    // console.log("One shot speech recog activated.");
    recognition.addEventListener('result', recogOneShot);
}

const speechButton2 = document.getElementById("start-transcript"); //continuous mode
function startRecord() {
    recognition.lang = "fil-PH";
    if (sttFlag == false) {
        recognition.abort();
        t2speech.cancel();
        speechButton2.innerHTML = '<i class="fa-solid fa-stop"></i>';
        recognition.start();
        sttFlag = true;
        // console.log("Start speaking...");
        recognition.addEventListener('result', recogContinuous);
    }
    else {
        recognition.stop();
        sttFlag = false;
        // console.log("Speech recognition stopped.");
        speechButton2.innerHTML = '<i class="fa-solid fa-microphone"></i>';
        recognition.removeEventListener('result', recogContinuous);
    }
}

const meetingPanel = document.getElementById("meeting-view");

function recogOneShot(event) {
    const stt_result = event.results[event.resultIndex];
    const transcript = stt_result[0].transcript;
    // const confidence = stt_result[0].confidence;
    // console.log(`One shot transcript: ${transcript}`);

    const chatInput = document.getElementById("chatInput");
    let current_text = chatInput.value;
    chatInput.value = current_text + " " + transcript;

    setTimeout(() => {
        sendMessage();
        // console.log("Message sent.");
        if (sttFlag == false) {
            recognition.stop();
        }
        speechButton.innerHTML = '<i class="fa-solid fa-microphone"></i>';
        recognition.removeEventListener('result', recogOneShot);
    }, 1000);
}

function recogContinuous(event) {
    const stt_result = event.results[event.resultIndex];
    const transcript = stt_result[0].transcript;
    // const confidence = stt_result[0].confidence;
    // console.log(`Transcript: ${transcript}`);

    let position = transcript.search(/hey abigail/i);
    if (position != -1) {
        document.getElementById("chatInput").focus();
        recognition.addEventListener('result', recogOneShot);
    }

    const full_text = document.getElementById("meeting-transcript");
    let current_text = full_text.innerText;
    full_text.innerText = current_text + "\n\n" + transcript;
    // meetingPanel.scrollTop = meetingPanel.scrollHeight;
    full_text.scrollTop = full_text.scrollHeight;
}

recognition.onerror = (event) => {
    console.log("STT Error:", event.error);
    recognition.abort();
    speechButton.innerHTML = '<i class="fa-solid fa-microphone"></i>';
    speechButton2.innerHTML = '<i class="fa-solid fa-microphone"></i>';
}

function sendAudio(chunks) {
    const formData = new FormData();
    const audioBlob = new Blob(chunks, {type: "audio/webm"});
    let timestamp = Date.now().toString();
    formData.append('audioRecog', audioBlob, `recording_${timestamp.slice(4)}.webm`);
    
    fetch('/webcam/meeting', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        // console.log("Submitted file. ", data);
        console.log(data.speakerName);
        console.log(data.confidence);
    })
    .catch(error => console.error('Error:', error));
}

const addVoice = document.getElementById("addVoice");
const speakerIDtest = document.getElementById("camMeeting");
let audioFlag = false;
let trainFlag = false;

if (navigator.mediaDevices.getUserMedia) {
    // console.log("The mediaDevices.getUserMedia() method is supported.");
    const constraints = {audio: true};
    let chunks = [];

    let onSuccess = function (stream) {
        const options = {mimeType: "audio/webm; codecs=opus", audioBitsPerSecond: 128000, };
        const mediaRecorder = new MediaRecorder(stream, options);

        addVoice.onclick = function () {
            trainFlag = true;
            if (audioFlag == false) {
                mediaRecorder.start();
                // console.log("Recording started.");
                audioFlag = true;
            }
            else if (audioFlag == true) {
                mediaRecorder.stop();
                // console.log("Recording stopped.");
                audioFlag = false;
            }
        };

        mediaRecorder.onstop = function (e) {
            if (trainFlag === true) {
                const clipName = prompt("Enter your name", "unnamed");
                const formData = new FormData();
                const audioBlob = new Blob(chunks, {type: "audio/webm"});
                chunks = [];
                formData.append('audioTrain', audioBlob, `${clipName}.webm`);
                
                fetch('/webcam/meeting', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    // console.log("Submitted file. ", data);
                })
                .catch(error => console.error('Error:', error));
            }
            else if (trainFlag === false) {
                sendAudio(chunks);
                chunks = [];
            }
            
        };

        mediaRecorder.ondataavailable = function (e) {
            chunks.push(e.data);
        };
    };

    let onError = function (err) {
        console.log("The following error occured:", err);
    };

    navigator.mediaDevices.getUserMedia(constraints).then(onSuccess, onError);
}
else {
    console.log("getUserMedia() not supported on your browser.");
}

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
            // console.log("Changed voice to: ", selectedVoice.name);
            showNotification(`Changed voice to: ${selectedVoice.name}`);
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
        // const bubble = messageBubble.querySelector('.bubble');
        const text = messageBubble.textContent.trim();
        speak(text);
    }
    
    hideContextMenu();
}

function addMessage(message, isUser = false, metadata = {}) {
    const messagesContainer = document.getElementById('chat-messages');
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

    let msgFooter = isUser ? `
        ${metadata.timestamp || getCurrentTime()} ${badges}
        <div class="reactions" id="chatReact"></div>
    ` : `
        <div class="reactions" id="chatReact"></div>
        ${metadata.timestamp || getCurrentTime()} ${badges}
    `;
    
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="avatar ${avatarClass}">${avatarContent}</div>
            <div style="flex: 1;">
                <div class="${bubbleClass}" data-original="${escapeHtml(message)}">
                    ${messageContent}
                    ${csvButton}
                </div>
                <div class="timestamp">
                    ${msgFooter}
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
    const messagesContainer = document.getElementById('chat-messages');
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
    // if (sttFlag) {
    //     recognition.stop();
    //     sttFlag = false;
    //     console.log("Speech recognition stopped.");
    //     speechButton.innerHTML = '<i class="fa-solid fa-microphone"></i>';
    // }
    
    t2speech.cancel();
    const input = document.getElementById('chatInput');
    const sendButton = document.getElementById('chatSend');
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
        
        const messagesContainer = document.getElementById('chat-messages');
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
const takeShot = document.getElementById("camScreenshot");
const toggleRecognition = document.getElementById("toggleRecognition");
const recogStatus = document.getElementById("recogStatus");

function toggleFeed() {
    if (feedStatus.checked == true) {
        feedStatus.checked = false;
        feedIcon.innerHTML = '<i class="fa-solid fa-video"></i>';
        feedIcon.title = "Enable video feed";
        videoFeed.style.opacity = '0';
    }
    else if (feedStatus.checked == false) {
        feedStatus.checked = true;
        feedIcon.innerHTML = '<i class="fa-solid fa-video-slash"></i>';
        feedIcon.title = "Disable video feed";
        videoFeed.style.opacity = '1';
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
        // Wait 3 seconds before enabling/disabling the buttons
        setTimeout(function(){
            takeShot.disabled = feedStatus.checked ? false : true;
            toggleRecognition.disabled = feedStatus.checked ? false : true;
        }, 2000);
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
        // console.log("Screenshot taken.");
        showNotification("Screenshot taken.");
        flash.style.display = 'none';
        // if (data.img_src) {
            // shotsHTML = shotsContent.innerHTML;
            // img_title = "title='" + data.img_src.slice(8) + "'/>";
            // shotsContent.innerHTML = "<img src='/screenshots/" + data.img_src + "' alt='screenshot taken through the webcam' " + img_title + shotsHTML;
        // }
    })
    .catch(error => console.error('Error:', error));
}

const ellipseOverlay = document.getElementById("registerOverlay");
const controlOverlay = document.getElementById("confirmBox");
const captureButton = document.getElementById("registerCapture");
const takeCancel = document.getElementById("retakeFace");
const submitFace = document.getElementById("submitFace");
const nameInput = document.getElementById("nameField");

// Shows/hides the overlay for face registration
function toggleOverlay() {
    moreSettings.style.display = 'none';
    if (ellipseOverlay.style.display == 'none') {
        ellipseOverlay.style.display = 'flex';
        controlOverlay.style.display = 'none';
    }
    else if (ellipseOverlay.style.display == 'flex') {
        ellipseOverlay.style.display = 'none';
    }
};

// Freezes the frame for the user to review
captureButton.addEventListener('click', () => {
    controlOverlay.style.display = 'flex';
    ellipseOverlay.style.display = 'none';

    fetch('/webcam_update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            freezeFrame: true
        })
    })
    .then(response => response.json())
    .then(data => {
        // console.log("Freeze frame.");
        document.getElementById("cam-controls").style.display = 'none';
    })
    .catch(error => console.error('Error:', error));
});

// Cancel freeze and go back to ellipse overlay
takeCancel.addEventListener('click', () => {
    toggleOverlay();

    fetch('/webcam_update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            freezeFrame: false
        })
    })
    .then(response => response.json())
    .then(data => {
        // console.log("Unfreeze frame.");
        document.getElementById("cam-controls").style.display = 'flex';
    })
    .catch(error => console.error('Error:', error));
});

// Submit image and name, then remove all overlays
submitFace.addEventListener('click', () => {
    if (nameInput.value !== '') {
        fetch('/webcam_update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                submitName: nameInput.value
            })
        })
        .then(response => response.json())
        .then(data => {
            document.getElementById("cam-controls").style.display = 'flex';
            controlOverlay.style.display = 'none';
            // if (data.img_src) {
            //     facesHTML = facesContent.innerHTML;
            //     img_alt = "' alt='" + data.img_src.slice(13) + "'/>";
            //     facesContent.innerHTML = "<img src='/screenshots/" + data.img_src + img_alt + facesHTML;
            // }
        })
        .catch(error => console.error('Error:', error));
    }
    else {
        nameInput.focus();
    }
});

const moreSettings = document.getElementById("cam-options");
function clickOutCam(e) {
    if (!e.target.closest("#cam-options") && !e.target.closest("#camOptions")) {
        moreSettings.style.display = 'none';
        document.removeEventListener('click', clickOutCam);
    }
}

function showSettings() {
    if (moreSettings.style.display == 'none') {
        moreSettings.style.display = 'flex';
        document.addEventListener('click', clickOutCam);
    }
    else if (moreSettings.style.display == 'flex') {
        moreSettings.style.display = 'none';
        document.removeEventListener('click', clickOutCam);
    }
}

// Show/hide gallery (right panel)
const gallery = document.getElementById("right-panel");
const shotsContent = document.getElementById("shotsContent");
const facesContent = document.getElementById("facesContent");
let loadedFlag = false;
function loadImages() {
    
}

function showGallery() {
    if (loadedFlag == false) {
        loadImages();
        loadedFlag = true;
    }

    moreSettings.style.display = 'none';
    if (gallery.style.display == 'none') {
        gallery.style.display = 'block';
        // document.addEventListener('click', clickOutside);
    }
    else if (gallery.style.display == 'block') {
        gallery.style.display = 'none';
        // document.removeEventListener('click', clickOutside);
    }
}

// Change tab on right panel
function switchTab(element, event) {
    const shotsTab = document.getElementById("shotsTab");
    const facesTab = document.getElementById("facesTab");

    if (element.id == 'facesTab') {
        shotsTab.disabled = false;
        shotsContent.style.display = "none";

        facesTab.disabled = true;
        facesContent.style.display = "flex";
    }
    else if (element.id == 'shotsTab') {
        facesTab.disabled = false;
        facesContent.style.display = "none";

        shotsTab.disabled = true;
        shotsContent.style.display = "flex";
    }
}

function toggleMeeting() {
    const meetingPanel = document.getElementById('meeting-view');
    if (meetingPanel.style.display == 'none') {
        meetingPanel.style.display = 'flex';
    }
    else if (meetingPanel.style.display == 'flex') {
        meetingPanel.style.display = 'none';
    }
}

function startFaceRecog() {
    recogStatus.checked = true;
    // console.log("Face Recognition start.");
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
    // const response = fetch('/get_charts');

    fetch('/get_charts')
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
    // console.log("array:", valuesArray);
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
// document.head.appendChild(style);