// Enhanced Chatroom JavaScript with Modern Features
const sessionId = 'session_' + Date.now();
let editingMessageId = null;
let selectedMessageId = null;
let selectedBubble = null;
let currentTheme = localStorage.getItem('theme') || 'light';
let autoScroll = localStorage.getItem('autoScroll') !== 'false';
let soundEnabled = localStorage.getItem('soundEnabled') === 'true';
let autoRead = localStorage.getItem('autoRead') === 'true';
let fontSize = parseInt(localStorage.getItem('fontSize')) || 14;

const t2speech = window.speechSynthesis;
let voices;
let selectedVoice;
let speechRate = 1.2;

const SpeechRecognition = window.SpeechRecognition;
const recognition = new SpeechRecognition();
recognition.continuous = true;
recognition.lang = "en-US";
recognition.maxAlternatives = 10;
let contsRecogFlag = false;
let utterance = '';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeTheme();
    initializeSettings();
    initializeEventListeners();
    document.getElementById('welcomeTime').innerHTML += getCurrentTime();
    const d = new Date();
    document.getElementById('start-marker').innerHTML = `<p>-----</p><p>${d.toDateString()}</p><p>-----</p>`;
    document.getElementById('chatInput').focus();
    
    // Set font size
    document.documentElement.style.setProperty('--base-font-size', `${fontSize}px`);
    document.documentElement.style.fontSize = `${fontSize}px`;
    document.getElementById('fontSizeSlider').value = fontSize;
    document.getElementById('fontSizeValue').textContent = `${fontSize}px`;
});

const playArea = document.getElementById('main-box');
function launchGame() {
    const gamebox = document.getElementById('mini-game');
    if (gamebox.style.display == 'none') {
        gamebox.style.display = 'flex';
        generate();
        // playArea.onclick = (event) => uncover(event);
    } else {
        gamebox.style.display = 'none';
        playArea.innerHTML = '';
        playArea.removeEventListener('click', uncover);
    }
}

function getAdjacent(cell) {
    const around = [];
    if (cell % 10 == 1) {
        // left edge
        around.push(...[cell-10, cell-10+1, cell+1, cell+10, cell+10+1]);
    }
    else if (cell % 10 == 0) {
        // right edge
        around.push(...[cell-10-1, cell-10, cell-1, cell+10-1, cell+10]);
    }
    else {
        around.push(...[cell-10-1, cell-10, cell-10+1, cell-1, cell+1, cell+10-1, cell+10, cell+10+1]);
    }
    const final = around.filter(num => num > 0 && num < 101);
    return final;
}

function assignClues(cell) {
    const around = getAdjacent(cell);
    for (let curr_cell of around) {
        if (curr_cell > 0 && curr_cell < 101) {
            const child = document.querySelector(`#main-box :nth-child(${curr_cell})`);
            if (child.dataset.txt == '') {
                child.dataset.txt = '1';
            } 
            else if (child.dataset.txt != 'X'){
                const ctr = parseInt(child.dataset.txt);
                child.dataset.txt = ctr + 1;
            }
        }
    }
}

const visited = [];
function generate() {
    playArea.innerHTML = '';
    win_condition = 100;
    visited.length = 0;
    for (let i=0; i<100; i++) {
        const cell = document.createElement('p');
        cell.dataset.txt = '';
        cell.dataset.id = i+1;
        playArea.appendChild(cell);
    }

    // let mine_ctr = 10;
    const diffSelect = document.getElementById('difficulty');
    let mine_ctr = diffSelect.value;
    const flagCount = document.getElementById('flag-count');
    flagCount.innerText = 'Flags: ' + mine_ctr;
    
    while (mine_ctr > 0) {
        const num = Math.floor(Math.random()*100) + 1;
        const curr_child = document.querySelector(`#main-box :nth-child(${num})`);
        if (curr_child.dataset.txt != 'X') {
            curr_child.dataset.txt = 'X';
            assignClues(num);
            mine_ctr -= 1;
        }
    }

    playArea.onclick = (event) => uncover(event);
    playArea.oncontextmenu = (event) => setFlag(event);
}

function flagMode() {
    const state = document.getElementById('flag-state');
    const flagButton = document.getElementById('flag-toggle');
    if (state.checked) {
        state.checked = false;
        flagButton.style.background = 'white';
    } else {
        state.checked = true;
        flagButton.style.background = 'green';
    }
}

function endGame(color) {
    const all_child = playArea.querySelectorAll('p');
    const flagCount = document.getElementById('flag-count');

    playArea.onclick = null;

    for (let cell of all_child) {
        if (cell.dataset.txt == 'X') {
            if (cell.classList.contains('flagged')) {
                cell.classList.add('victory');
            } else {
                cell.classList.add(color);
            }
        }
        else {
            cell.classList.add('opened');
        }
        cell.innerText = cell.dataset.txt;
    }

    if (color == 'defeat') {
        flagCount.innerText = 'Game Over';
    }
    else if (color == 'victory') {
        flagCount.innerText = 'You Win!!';
    }
}

function openAdjacent(cell_num) {
    const adjacentList = getAdjacent(cell_num);
    for (let num of adjacentList) {
        if (!visited.includes(num)) {
            visited.push(num);
            const curr_cell = playArea.querySelector(`#main-box :nth-child(${num})`);
            if (curr_cell.dataset.txt == '' && curr_cell.classList.length == 0) {
                curr_cell.classList.add('opened');
                curr_cell.innerText = curr_cell.dataset.txt;
                let new_adj = getAdjacent(num).filter(numb => !visited.includes(numb));
                adjacentList.push(...new_adj);
            }
            else if (curr_cell.dataset.txt != 'X') {
                curr_cell.classList.add('opened');
                curr_cell.innerText = curr_cell.dataset.txt;
            }
        }
    }
}

function setFlag(e) {
    const target = e.target.closest('p');
    if (target == null) return;
    e.preventDefault();

    const flagCtr = document.getElementById('flag-count');
    const num = flagCtr.innerText.match(/\d+/);
    let flag_count = parseInt(num[0]);
    
    if ((target.classList.length == 0) && flag_count > 0) {
        target.classList.add('flagged');
        flag_count -= 1;
        flagCtr.innerText = 'Flags: ' + flag_count;
    }
    else if (target.classList.contains('flagged')) {
        target.classList.remove('flagged');
        flag_count += 1;
        flagCtr.innerText = 'Flags: ' + flag_count;
    }
}

function uncover(e) {
    const target = e.target.closest('p');
    if (target == null) return;

    if (target.classList.length == 0) {
        target.classList.add('opened');
        target.innerText = target.dataset.txt;
        if (target.dataset.txt == 'X') {
            endGame('defeat');
        }
        else if (target.dataset.txt == '') {
            openAdjacent(parseInt(target.dataset.id));
        }
    }

    const opened = playArea.querySelectorAll('p.opened').length;
    const flagged = playArea.querySelectorAll('p.flagged').length;
    // console.log(opened, flagged);
    if (opened + flagged == 100) {
        endGame('victory');
    }
}

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

    const savedAutoRead = localStorage.getItem('autoRead');
    if (savedAutoRead !== null) {
        document.getElementById('autoreadToggle').checked = savedAutoRead === 'true';
        autoRead = savedAutoRead === 'true';
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

    document.getElementById('autoreadToggle').addEventListener('change', (e) => {
        autoRead = e.target.checked;
        localStorage.setItem('autoRead', autoRead);
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

    const chatInput = document.getElementById("chatInput");
    chatInput.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        document.getElementById("input-help").style.display = 'flex';
        document.addEventListener('click', hideHelp);
    });
}

function hideHelp(e) {
    if (!e.target.closest('.input-help') && !e.target.closest('.help-entry')) {
        document.getElementById("input-help").style.display = 'none';
        document.removeEventListener('click', hideHelp);
    }
}

function autoComplete(format) {
    document.getElementById("chatInput").value = format;
    document.getElementById("input-help").style.display = 'none';
    document.removeEventListener('click', hideHelp);
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
    const icon = document.getElementById('settingsToggle').querySelector('i');

    if (panel.style.display == 'none') {
        panel.style.display = 'block';
        icon.style.transform = 'translateY(0.5px) rotate(180deg)';
    }
    else {
        panel.style.display = 'none';
        icon.style.transform = '';
    }
    playSound('click');
}

function hideSearch(e) {
    const searchBar = document.getElementById('searchBar');
    const searchButton = document.getElementById("searchToggle");
    if (!e.target.closest('#searchBar') && !e.target.closest('#searchToggle')) {
        document.getElementById('searchInput').value = '';
        clearSearchResults();
        searchBar.style.display = 'none';

        document.removeEventListener('click', hideSearch);
        searchButton.querySelector('.fa-times').style.display = 'none';
        searchButton.querySelector('.fa-search').style.display = '';
    }
}

function toggleSearch() {
    const searchBar = document.getElementById('searchBar');
    const searchButton = document.getElementById("searchToggle");

    if (searchBar.style.display == 'none') {
        searchBar.style.display = 'flex';
        searchButton.querySelector('.fa-search').style.display = 'none';
        searchButton.querySelector('.fa-times').style.display = '';
        document.getElementById('searchInput').focus();
        document.addEventListener('click', hideSearch);
    }
    else if (searchBar.style.display == 'flex') {
        document.getElementById('searchInput').value = '';
        clearSearchResults();
        searchBar.style.display = 'none';
        
        document.removeEventListener('click', hideSearch);
        searchButton.querySelector('.fa-times').style.display = 'none';
        searchButton.querySelector('.fa-search').style.display = '';
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
    // Handler function when user clicks outside of chat options
    if (!e.target.closest('#chatOptions') && !e.target.closest('#more-inputs')) {
        hideMoreInputs();
    }
}

function hideMoreInputs() {
    const optionsButton = document.getElementById("chatOptions");
    const icon = optionsButton.querySelector('i');
    icon.style.transform = '';
    document.getElementById("more-inputs").style.display = 'none';

    document.removeEventListener('click', clickOutInput);
}

function showMoreInputs() {
    const optionsButton = document.getElementById("chatOptions");
    const icon = optionsButton.querySelector('i');
    
    const moreInputs = document.getElementById("more-inputs");
    if (moreInputs.style.display === 'none') {
        moreInputs.style.display = 'flex';
        icon.style.transform = 'rotate(135deg)';

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
        showNotification("Saved transcript.");
    })
    .catch(error => console.error('Error:', error));
}

function clearTranscript() {
    const full_text = document.getElementById("meeting-transcript");
    full_text.style.animation = 'slideOutLeft 1s ease-in';
    full_text.innerText = 'Meeting transcript appears here. Try saying "Hey Abigail".';
    showNotification("Cleared transcript");
    setTimeout(function () {
        full_text.style.animation = null;
    }, 2000);
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
        meetingPanel.style.display = 'none';
        videoUI.style.display = 'none';
        mainGrid.classList.remove('webcamON');
        chatUI.classList.remove('reduced');

        document.getElementById("openWebcam").innerHTML = '<i class="fa-solid fa-video"></i>';
        document.getElementById("openWebcam").style = 'background: ""; color: ""';
        document.getElementById("cam-options").style.display = 'none';
    }
}

function clickOut(e) {
    // Handler function when user clicks outside of context menu
    if (!e.target.closest('.context-menu') && e.target.closest('.bubble') !== selectedBubble) {
        hideContextMenu();
    }
}

function showContextMenu(e, messageBubble) {
    const menu = document.getElementById('contextMenu');
    selectedBubble = messageBubble;

    const ttsButton = document.getElementById("ttsButton");
    if (t2speech.speaking) {
        ttsButton.innerHTML = `<i class="fa-solid fa-stop"></i> Stop Reading`;
    }
    else {
        ttsButton.innerHTML = `<i class="fa fa-volume-up"></i> Read Aloud`;
    }
    
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
        // selectedBubble.style.border = "none";
        selectedBubble.style.border = "";
        selectedBubble = null;
    }
    document.removeEventListener('click', clickOut);
}

function copyMessage() {
    if (!selectedBubble) return;
    
    const insideText = selectedBubble.textContent;
    if (insideText) {
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
            messageBubble.style.animation = 'slideOutRight 0.3s ease';
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
    formData.append('file', file_input.files[0]);
    
    fetch('/api/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification("Submitted file.");
            cancelFile();
        }
        else {
            console.error('Error:', data.error);
            showNotification(`Error: ${data.error}`);
            cancelFile();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification(`Error: ${error}`);
        cancelFile();
    });
}

function cancelFile() {
    const fileStatus = document.getElementById("attached-file");
    fileStatus.innerText = '';
    document.getElementById("status-file").style.display = 'none';

    const fileInput = document.getElementById("file-input");
    fileInput.value = '';

    document.getElementById("statusText").style.display = 'block';
}

async function downloadCSV(filename) {
    try {
        // window.location.href = "api/download/" + filename;
        window.open("api/download/" + filename, "_blank");
        showNotification("Downloading csv...");
        playSound('success');
    } catch (error) {
        // console.error('Export error:', error);
        showNotification('Failed to download csv', 'error');
    }
    
    hideContextMenu();
}

async function viewChart(csv_source) {
    try {
        // window.open("chart/" + csv_source, "_blank");
        let chartValues = await parseCsv(csv_source);
        if (!chartValues.data) {
            console.log("Error creating chart");
        }
        else {
            const config = chartConfig(chartValues.name, chartValues.data, chartValues.labels);
            openLightbox(config);
        }
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
let oneshotRecogFlag = false;
function startRecordOneShot() {
    // recognition.lang = "en-US";
    t2speech.cancel();
    if (oneshotRecogFlag == false && contsRecogFlag == false) {
        t2speech.cancel();
        speechButton.innerHTML = '<i class="fa-solid fa-stop"></i>';
        document.getElementById('chatInput').focus();
        recognition.start();
        oneshotRecogFlag = true;
        recognition.addEventListener('result', recogOneShot);
    }
    else if (oneshotRecogFlag == true && contsRecogFlag == false) {
        recognition.stop();
        oneshotRecogFlag = false;
        speechButton.innerHTML = '<i class="fa-solid fa-microphone"></i>';
        recognition.removeEventListener('result', recogOneShot);
    }
    
}

const speechButton2 = document.getElementById("start-transcript"); //continuous mode
function startRecord() {
    // recognition.lang = "fil-PH";
    if (contsRecogFlag == false) {
        recognition.abort();
        t2speech.cancel();
        speechButton2.innerHTML = '<i class="fa-solid fa-stop"></i>';
        recognition.start();
        contsRecogFlag = true;
        recognition.addEventListener('result', recogContinuous);
    }
    else {
        recognition.stop();
        contsRecogFlag = false;
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
        if (contsRecogFlag == false) {
            sendMessage();
            recognition.stop();
            hideMoreInputs();
        }
        else if (contsRecogFlag == true) {
            // let full_transcript = document.getElementById("meeting-transcript").innerText;
            // sendTranscript(full_transcript, chatInput.value);
            sendMessage(true);
        }
        speechButton.innerHTML = '<i class="fa-solid fa-microphone"></i>';
        recognition.removeEventListener('result', recogOneShot);
    }, 1000);
}

function recogContinuous(event) {
    const stt_result = event.results[event.resultIndex];
    let transcript = stt_result[0].transcript;
    // const confidence = stt_result[0].confidence;
    // console.log(`Transcript: ${transcript}`);

    let position = transcript.search(/hey abigail/i);
    if (position != -1) {
        document.getElementById("chatInput").focus();
        playSound('click');
        recognition.addEventListener('result', recogOneShot);
    }

    const full_text = document.getElementById("meeting-transcript");
    let current_text = full_text.innerText;
    full_text.innerText = current_text + "\n\n" + transcript;
    full_text.scrollTop = full_text.scrollHeight;
}

recognition.onerror = (event) => {
    console.log("STT Error:", event.error);
    recognition.abort();
    speechButton.innerHTML = '<i class="fa-solid fa-microphone"></i>';
    speechButton2.innerHTML = '<i class="fa-solid fa-microphone"></i>';
}

recognition.onend = () => {
    console.log("Speech recognition service disconnected.");
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

if (navigator.mediaDevices == null) {
    console.log("URL not secured so mediaDevices is undefined.");
    addVoice.disabled = true;
    speechButton.disabled = true;
    speechButton2.disabled = true;
}
else if (navigator.mediaDevices.getUserMedia) {
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
    voiceList.replaceChildren();
    for (let [i, voice] of voices.entries()) {
        if (voice.lang == 'en-US' || voice.lang == 'en-GB' || voice.lang == 'en-AU') {
            const option = document.createElement("option");
            option.textContent = `${voice.name}`;
            option.value = i;
            voiceList.add(option);
            if (voice.name == "Microsoft Ana Online (Natural) - English (United States)") {
                selectedVoice = i;
            }
        }
        
    }
    voiceList.value = selectedVoice;
}

t2speech.onvoiceschanged = populateVoices;

voiceList.addEventListener('change', (e) => {
    selectedVoice = voiceList.value;
});

function speak(text) {
    utterance = new SpeechSynthesisUtterance(text);
    utterance.voice = voices[selectedVoice];
    utterance.rate = speechRate;
    t2speech.speak(utterance);
}

function textToSpeech() {
    if (!selectedBubble) return;
    
    const messageBubble = selectedBubble;
    if (messageBubble) {
        if (t2speech.speaking) {
            t2speech.cancel();
        }
        else {
            const text = messageBubble.textContent.trim();
            speak(text);
        }
    }
    
    hideContextMenu();
}

let curr_chart_id = 0;
function addMessage_plain(message, isUser = false, metadata = {}) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message-bubble ${isUser ? 'user' : 'bot'}`;
    messageDiv.dataset.messageId = metadata.id || `msg_${Date.now()}_${Math.random()}`;

    const avatarContent = '<img src="/static/images/abigail-removebg-preview.png" alt="Abigail" class="avatar-image">';
    const avatarClass = 'bot-avatar';

    const bubbleClass = 'bubble';
    
    // Render markdown if available
    let messageContent = escapeHtml(message);
    if (typeof marked !== 'undefined') {
        try {
            messageContent = marked.parse(message);
        } catch (e) {
            console.warn('Markdown parsing failed:', e);
        }
    }

    let chart_viewer = '';
    if (metadata.response_type === 'chart' && isUser == false) {
        const chartNodes = document.querySelectorAll('canvas');
        const chart_id = chartNodes.length - 1;
        curr_chart_id = chart_id;
        chart_viewer = `
<div style="height: 200px; max-width: 100%; background: white; margin-top: 10px;">
    <canvas id="myChart_${chart_id}"></canvas>
</div>`;
    }

    let csvButton = '';
    const fileArray = [];
    if (metadata.csv){
        fileArray.push(...metadata.csv.split(" "));
        // console.log(fileArray);
        for (let entry of fileArray) {
            // console.log(entry);
            if (messageContent.search(entry) != -1) {
                let new_button = `
                <div class="csv-action">
                    <button type="button" class="download-csv" onclick="downloadCSV('${entry}')" title="download csv">Download csv file</button>
                </div>`;
                messageContent = messageContent.replace(entry, new_button);
            }
            else {
                const chartButton = metadata.with_chart ? `<button type="button" class="download-csv" onclick="viewChart('${metadata.csv}')">View chart</button>` : '';
                csvButton += `
                    <div class="csv-action">
                        <button type="button" class="download-csv" onclick="downloadCSV('${metadata.csv}')" title="download csv">${metadata.csv}</button>
                        ${chartButton}
                    </div>
                `;
            }
        }
    }
    
    messageDiv.innerHTML = `
        <div class="message-content">
            <div style="flex: 1; margin-left: 90px">
                <div class="${bubbleClass}">
                    ${messageContent}
                    ${csvButton}
                    ${chart_viewer}
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

function addMessage(message, isUser = false, metadata = {}) {
    const messagesContainer = document.getElementById('chat-messages');

    // get last date marker
    const marker_list = document.getElementsByClassName('date-marker');
    let latest_marker_date = marker_list[marker_list.length-1].children[1].innerText;
    const curr_d = new Date();
    if (latest_marker_date != curr_d.toDateString()){
        const newMarker = document.createElement('div');
        newMarker.className = 'date-marker';
        newMarker.innerHTML = `<p>-----</p><p>${curr_d.toDateString()}</p><p>-----</p>`;
        messagesContainer.appendChild(newMarker);
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message-bubble ${isUser ? 'user' : 'bot'}`;
    messageDiv.dataset.messageId = metadata.id || `msg_${Date.now()}_${Math.random()}`;
    
    const avatarContent = isUser ? '<i class="fa-solid fa-circle-user"></i>' : '<img src="/static/images/abigail-removebg-preview.png" alt="Abigail" class="avatar-image">';
    const avatarClass = isUser ? 'user-avatar' : 'bot-avatar';
    
    let badges = '';
    if (metadata.response_type === 'activity') {
        badges = '<span class="badge activity">Activity</span>';
    }else if (metadata.response_type === 'attendance') {
        badges = '<span class="badge attendance">Attendance</span>';
    }else if (metadata.response_type === 'KTS') {
        badges = '<span class="badge kts">Traceability</span>';
    }else if (metadata.response_type === 'general') {
        badges = '<span class="badge general">General</span>';
    }else if (metadata.response_type) {
        badges = `<span class="badge others">${metadata.response_type}</span>`;
    }

    const bubbleClass = 'bubble';
    
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

    let chart_viewer = '';
    if (metadata.response_type === 'chart' && isUser == false) {
        const chartNodes = document.querySelectorAll('canvas');
        const chart_id = chartNodes.length - 1;
        curr_chart_id = chart_id;
        chart_viewer = `
<div style="height: 200px; max-width: 100%; background: white; margin-top: 10px;">
    <canvas id="myChart_${chart_id}"></canvas>
</div>`;
    }

    let csvButton = '';
    const fileArray = [];
    if (metadata.csv){
        fileArray.push(...metadata.csv.split(" "));
        // console.log(fileArray);
    }
    
    if (metadata.csv && fileArray.length == 1 && isUser == false) {
        const chartButton = metadata.with_chart ? `<button type="button" class="download-csv" onclick="viewChart('${metadata.csv}')">View chart</button>` : '';
        csvButton = `
            <div class="csv-action">
                <button type="button" class="download-csv" onclick="downloadCSV('${metadata.csv}')" title="download csv">Download csv file</button>
                ${chartButton}
            </div>
        `;
    }
    else if (metadata.csv && fileArray.length > 1 && isUser == false) {
        for (let entry of fileArray) {
            console.log(entry);
            if (entry != '') {
                let new_button = `
                <div class="csv-action">
                    <button type="button" class="download-csv" onclick="downloadCSV('${entry}')" title="download csv">Download csv file</button>
                </div>`;
                messageContent = messageContent.replace(entry, new_button);
            }
            // else {
            //     messageContent = messageContent.replace("<p> placeholder </p>", '');
            // }
        }
    }
    
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="avatar ${avatarClass}">${avatarContent}</div>
            <div style="flex: 1;">
                <div class="${bubbleClass}">
                    ${messageContent}
                    ${csvButton}
                    ${chart_viewer}
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

function showTypingIndicator(step='') {
    const messagesContainer = document.getElementById('chat-messages');
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message-bubble bot';
    typingDiv.id = 'typingIndicator';
    typingDiv.innerHTML = `
        <div class="message-content">
            <div class="avatar bot-avatar"><img src="/static/images/abigail-removebg-preview.png" alt="Abigail" class="avatar-image"></div>
            <div class="typing-indicator">
                <p>${step}</p>
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

async function sendMessage(withTranscript = false) {
    const input = document.getElementById('chatInput');
    const sendButton = document.getElementById('chatSend');
    let message = input.value.trim();

    const fileInput = document.getElementById("file-input");
    let filename = '';

    if (!message && fileInput.value == '') return;

    if (fileInput.value != '') {
        submitFile();
        filename = fileInput.files[0].name;
        message = `**Uploaded file: ${filename}**\n\n\n` + message;
    }
    
    const msgId = `msg_${Date.now()}_${Math.random()}`;
    addMessage(message, true, { id: msgId, timestamp: getCurrentTime() });
    input.value = '';
    
    sendButton.disabled = true;
    input.disabled = true;
    updateStatus('Processing...', 'processing');
    showTypingIndicator();

    if (withTranscript == true) {
        let full_transcript = document.getElementById("meeting-transcript").innerText;
        message = `Conversation context: ${full_transcript} User Query: ${message}`;
        // console.log('Message sent (WITH transcript)');
    }
    // else {
    //     console.log('Message sent (no transcript)');
    // }
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId,
                fileAttached: filename
            })
        });
        
        const data = await response.json();
        hideTypingIndicator();
        
        if (data.error) {
            addMessage(data.message || 'An error occurred', false, { ...data, response_type: 'error' });
            updateStatus('Error', 'error');
        }
        else {
            addMessage(data.message, false, data);
            updateStatus('Ready', 'ready');
            if (autoRead) {
                setTimeout(function() {
                    speak(data.message);
                }, 1000);
            }

            if (data.response_type === 'chart') {
                let chartValues = await parseCsv(message);
                if (!chartValues.data) {
                    console.log("Error creating chart");
                }
                else{
                    createChart(chartValues.name, chartValues.data, chartValues.labels);
                }
            }
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

async function New_sendMessage(withTranscript = false) {
    const input = document.getElementById('chatInput');
    const sendButton = document.getElementById('chatSend');
    let message = input.value.trim();

    const fileInput = document.getElementById("file-input");
    let filename = '';

    if (!message && fileInput.value == '') return;

    let final_message = ''
    if (fileInput.value != '') {
        submitFile();
        filename = fileInput.files[0].name;
        final_message = `**Uploaded file: ${filename}**\n\n\n` + message;
    }
    else {
        final_message = message
    }
    
    const msgId = `msg_${Date.now()}_${Math.random()}`;
    addMessage(final_message, true, { id: msgId, timestamp: getCurrentTime() });
    input.value = '';
    
    sendButton.disabled = true;
    input.disabled = true;
    updateStatus('Processing...', 'processing');
    showTypingIndicator('Analyzing query');

    if (withTranscript == true) {
        let full_transcript = document.getElementById("meeting-transcript").innerText;
        message = `Conversation context: ${full_transcript} User Query: ${message}`;
        // console.log('Message sent (WITH transcript)');
    }

    let next_flag = false;
    try {
        // Analyzing Query Step
        // const response_1 = await fetch('/api/chat/1', {
        //     method: 'POST',
        //     headers: {
        //         'Content-Type': 'application/json',
        //     },
        //     body: JSON.stringify({
        //         message: message,
        //         session_id: sessionId,
        //         fileAttached: filename
        //     })
        // });
        
        // const data_1 = await response_1.json();
        // hideTypingIndicator();
        
        // if (data_1.error) {
        //     addMessage_plain(data_1.message || 'An error occurred', false, { ...data_1, response_type: 'error' });
        //     return;
        // }

        // if (data_1.response_type === 'chart') {
        //     let chartValues = await parseCsv(message);
        //     if (!chartValues.data) {
        //         console.log("Error creating chart");
        //     }
        //     else{
        //         createChart(chartValues.name, chartValues.data, chartValues.labels);
        //     }
        // }

        // if (data_1.response_type != 'summary') {
        //     // addMessage_plain(data_1.message, false, data_1);
        //     next_flag = true;
        //     showTypingIndicator('Retrieving data');
        // }
        // else {
        //     next_flag = false;
        //     addMessage_plain(data_1.message, false, data_1);
        //     updateStatus('Ready', 'ready');
        // }

        // if (next_flag == false) {
        //     sendButton.disabled = false;
        //     input.disabled = false;
        //     input.focus();
        //     return;
        // };

        const response_2 = await fetch('/api/chat/2', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            })
        });
        
        const data_2 = await response_2.json(); //array of results
        hideTypingIndicator();
        
        if (data_2.error) {
            addMessage_plain(data_2.error || 'An error occurred', false, { ...data_2, response_type: 'error' });
            next_flag = false;
            // updateStatus('Error', 'error');
        }
        else {
            for (let result of data_2.message_list){
                if (result.message || result.csv) {
                    addMessage_plain(result.message, false, result);
                }
            }
            showTypingIndicator('Generating response');
            next_flag = true;
        }

        if (next_flag == false) {
            sendButton.disabled = false;
            input.disabled = false;
            input.focus();
            return;
        };

        const response_3 = await fetch('/api/chat/3', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            })
        });
        
        const data_3 = await response_3.json();
        hideTypingIndicator();
        
        if (data_3.error) {
            addMessage(data_3.message || 'An error occurred', false, { ...data_3, response_type: 'error' });
            updateStatus('Error', 'error');
        }
        else {
            addMessage(data_3.message, false, data_3);
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
        
        const messagesContainer = document.getElementById('chat-messages');
        messagesContainer.innerHTML = `
            <div class="message-bubble bot">
                <div class="message-content">
                    <div class="avatar bot-avatar"><img src="/static/images/abigail-removebg-preview.png" alt="Abigail" class="avatar-image"></div>
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
        // sendMessage();
        New_sendMessage();
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
                exportText += `${isUser ? 'You' : 'Abigail'}: `;
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
        // Wait 2 seconds before enabling/disabling the buttons
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
        showNotification("Screenshot taken.");
        flash.style.display = 'none';
        if (data.img_src) {
            shotsHTML = shotsContent.innerHTML;
            img_title = "title='" + data.img_src.slice(8) + "'/>";
            shotsContent.innerHTML = "<img src='/screenshots/" + data.img_src + "' alt='screenshot taken through the webcam' " + img_title + shotsHTML;
        }
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
    hideSettings();
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
    // Handler function when user clicks outside of cam options
    if (!e.target.closest("#cam-options") && !e.target.closest("#camOptions")) {
        hideSettings();
    }
}

function hideSettings() {
    moreSettings.style.display = 'none';
    document.removeEventListener('click', clickOutCam);
}

function showSettings() {
    if (moreSettings.style.display == 'none') {
        moreSettings.style.display = 'flex';
        document.addEventListener('click', clickOutCam);
    }
    else if (moreSettings.style.display == 'flex') {
        hideSettings();
    }
}

// Show/hide gallery (right panel)
const gallery = document.getElementById("right-panel");
const shotsContent = document.getElementById("shotsContent");
const facesContent = document.getElementById("facesContent");
let loadedFlag = false;
function loadImages() {
    const shotsChildren = shotsContent.querySelectorAll('img');
    for (let sc of shotsChildren) {
        sc.src = sc.dataset.source;
        // console.log(sc.src);
    }

    const facesChildren = facesContent.querySelectorAll('img');
    for (let fc of facesChildren) {
        fc.src = fc.dataset.source;
        // console.log(fc.src);
    }
}

function showGallery() {
    if (loadedFlag == false) {
        loadImages();
        loadedFlag = true;
    }

    moreSettings.style.display = 'none';
    if (gallery.style.display == 'none') {
        gallery.style.display = 'block';
    }
    else if (gallery.style.display == 'block') {
        gallery.style.display = 'none';
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

// Swipe event handler on touch devices
let touchStartX = 0;
let touchEndX = 0;

function initialTouch(e) {
    touchStartX = e.touches[0].pageX;
}

function finalTouch(e) {
    touchEndX = e.changedTouches[0].pageX;
}

function swipeLeft() {
    if (touchEndX < touchStartX) {
        meetingPanel.style.display = 'none';
    }
}

function toggleMeeting() {
    hideSettings();
    if (meetingPanel.style.display == 'none') {
        meetingPanel.style.display = 'flex';
        document.addEventListener('touchstart', initialTouch);
        document.addEventListener('touchmove', finalTouch);
        document.addEventListener('touchend', swipeLeft);
    }
    else if (meetingPanel.style.display == 'flex') {
        meetingPanel.style.display = 'none';
        document.removeEventListener('touchstart', initialTouch);
        document.removeEventListener('touchmove', finalTouch);
        document.removeEventListener('touchend', swipeLeft);
    }
}

function startFaceRecog() {
    recogStatus.checked = true;
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
    hideSettings();
    if (recogStatus.checked == true) {
        stopFaceRecog();
    }
    else if (recogStatus.checked == false) {
        startFaceRecog();
    }
};

function parseCsv(filename) {
    return fetch(`/chart/${filename}`, {})
    .then(response => response.json())
    .then(data => {
        const chartObject = {};
        chartObject.labels = data.labels;
        chartObject.data = data.data;
        chartObject.name = data.name;
        return chartObject;
    })
    .catch(error => console.error('Error:', error));
}

let myChartBox = null;
function openLightbox(config) {
    const lightbox = document.getElementById("chart-lightbox");
    const chart_space = lightbox.querySelector('canvas');
    if (myChartBox) {
        myChartBox.destroy();
    }

    myChartBox = new Chart(
        chart_space,
        config
    );

    lightbox.style.display = 'flex';
}

document.addEventListener('click', (e) => {
    const curr_chart = e.target.closest('canvas');
    if (curr_chart != null && curr_chart.id !== 'lightbox') {
        const chart_id = parseInt(curr_chart.id.slice(8));
        // console.log("Selected Node:", myChart[chart_id]);
        const config = myChart[chart_id].config._config
        openLightbox(config);
    }
});

function exitLightbox() {
    const lightbox = document.getElementById("chart-lightbox");
    lightbox.style.display = 'none';
}

function chartConfig(chartName, chartData, labels) {
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
    // how to use time object as labels? then force 24 ticks
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
                    ticks: {stepSize: 1},
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

    return config;
}

function createChart(chartName, chartData, labels) {
    // console.log("Creating chart...");
    const config = chartConfig(chartName, chartData, labels);
    let chart_space = document.querySelector(`#myChart_${curr_chart_id}`);

    myChart.push(new Chart(
        chart_space,
        config
    ));
}