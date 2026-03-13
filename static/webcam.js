const SpeechRecognition = window.SpeechRecognition;
const recognition = new SpeechRecognition();
recognition.lang = "fil-PH";
recognition.continuous = true;
recognition.maxAlternatives = 50;
let sttFlag = false;

const feedStatus = document.getElementById("feedStatus");
const feedIcon = document.getElementById("toggleFeed");
const videoFeed = document.getElementById("live-feed");

const moreSettings = document.getElementById("more-settings");
const meetingPanel = document.getElementById("meeting-view");
let meetingFaceRec= false;
let namesArray = [];

const gallery = document.getElementById("right-panel");
const shotsContent = document.getElementById("shotsContent");
const facesContent = document.getElementById("facesContent");

const toggleRecognition = document.getElementById("toggleRecognition");
const recogStatus = document.getElementById("recogStatus");

const takeShot = document.getElementById("takeShot");
const flash = document.getElementById("flash");

const addFace = document.getElementById("addFace");
const ellipseOverlay = document.getElementById("registerOverlay");
const controlOverlay = document.getElementById("confirmBox");
const captureButton = document.getElementById("registerCapture");
const takeCancel = document.getElementById("retakeFace");
const submitFace = document.getElementById("submitFace");
const nameInput = document.getElementById("nameField");

// Toggle for speech recognition
const speechButton = document.getElementById("recordSpeech");
function startRecord() {
    if (sttFlag == false) {
        speechButton.innerHTML = '<i class="fa-solid fa-stop"></i>';
        speechButton.title = "Stop speech recognition";
        recognition.start();
        sttFlag = true;
        // console.log("Start speaking...");
    }
    else {
        recognition.stop();
        sttFlag = false;
        // console.log("Speech recognition stopped.")
        speechButton.innerHTML = '<i class="fa-solid fa-microphone"></i>';
        speechButton.title = "Start speech recognition";
    }
}

// Fires when recognition has a valid output
recognition.addEventListener('result', (event) => {
    const stt_result = event.results[event.resultIndex];
    const transcript = stt_result[0].transcript;
    // const confidence = stt_result[0].confidence;
    // console.log(`Transcript: ${transcript} (Confidence: ${Math.round(confidence * 100)}%)`);
    if (transcript.includes('start face recognition')) {
        startFaceRecog();
        meetingFaceRec = true;
    }
    else if (transcript.includes('stop face recognition')) {
        stopFaceRecog();
        meetingFaceRec = false;
    }

    const full_text = document.getElementById("meeting-transcript");
    current_text = full_text.innerText;
    full_text.innerText = current_text + "\n\n" + transcript;
    meetingPanel.scrollTop = meetingPanel.scrollHeight;

    fetch('/webcam/meeting', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            speech2text: transcript,
            // faceRecog: meetingFaceRec,
        })
    })
    .then(response => response.json())
    .then(data => {
        // console.log("Detected faces:", data.names);
    })
    .catch(error => console.error('Error:', error));
});

recognition.onerror = (event) => {
    console.log("Error - Speech Recognition:", event.error);
}

// recognition.onspeechend = () => {
//     setTimeout(() => {}, 3000);
//     recognition.stop();
//     sttFlag = false;
//     console.log("Speech recognition stopped.");
//     speechButton.innerHTML = '<i class="fa-solid fa-microphone"></i>';
// };

// Starts/stops capturing directly from OpenCV
function toggleFeed() {
    if (feedStatus.checked == true) {
        feedStatus.checked = false;
        feedIcon.innerHTML = '<i class="fa-solid fa-video"></i>';
        feedIcon.title = "Enable video feed";
        videoFeed.style.height = '0';
        ellipseOverlay.style.display = 'none';
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
            addFace.disabled = addFace.disabled ? false : true;
        }, 5000);
    })
    .catch(error => console.error('Error:', error));
};

// Screenshot with visual feedback
takeShot.addEventListener('click', () => {
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
        if (data.img_src) {
            shotsHTML = shotsContent.innerHTML;
            img_title = "title='" + data.img_src.slice(8) + "'/>";
            shotsContent.innerHTML = "<img src='/screenshots/" + data.img_src + "' alt='screenshot taken through the webcam' " + img_title + shotsHTML;
        }
    })
    .catch(error => console.error('Error:', error));
});

// Show/hide meeting transcript
const centerBox = document.getElementById("center-box");
const mainControls = document.getElementById("main-controls");
function showMeeting() {
    moreSettings.style.display = 'none';
    if (meetingPanel.style.display == 'none') {
        centerBox.style.width = '1000px';
        mainControls.style = 'grid-template-columns: 1fr 1fr 1fr 1fr;';
        speechButton.style.display = 'block';
        meetingPanel.style.display = 'flex';
        meetingFlag = true;
    }
    else {
        meetingFlag = false;
        meetingPanel.style.display = 'none';
        speechButton.style.display = 'none';
        mainControls.style = 'grid-template-columns: 1fr 1fr 1fr;';
        centerBox.style.width = '640px';
    }
}

// function clickOutside(event) {
//     if (gallery.style.display == 'block' && !event.target.closest('#right-panel')) {
//         console.log('clicked outside');
//         gallery.style.display = 'none';
//         // document.removeEventListener('click', clickOutside);
//     }
//     else if (gallery.contains(event.target)) {
//         console.log('clicked inside');
//     }
// }

// Expand/collapse more options
const optionBurger = document.getElementById("settingsButton");
function showSettings() {
    if (moreSettings.style.display == 'none') {
        moreSettings.style.display = 'flex';
        optionBurger.style.transform = 'rotate(-360deg)';
        document.getElementById("joinMeeting").style.transform = 'translateX(0)';
        document.getElementById("addFace").style.transform = 'translateX(0)';
        document.getElementById("showGallery").style.transform = 'translateX(0)';
    }
    else if (moreSettings.style.display == 'flex') {
        optionBurger.style.transform = 'rotate(0)';
        document.getElementById("joinMeeting").style.transform = 'translateX(70%)';
        document.getElementById("addFace").style.transform = 'translateX(70%)';
        document.getElementById("showGallery").style.transform = 'translateX(70%)';
        setTimeout(function(){
            moreSettings.style.display = 'none';
        }, 150);
    }
}

// Show/hide gallery (right panel)
function showGallery() {
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
    toggleRecognition.style.background = 'rgb(63 129 63)';
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

// Shows/hides the overlay for face registration
function toggleOverlay() {
    moreSettings.style.display = 'none';
    if (ellipseOverlay.style.display == 'none') {
        ellipseOverlay.style.display = 'block';
        controlOverlay.style.display = 'none';
    }
    else if (ellipseOverlay.style.display == 'block') {
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
            controlOverlay.style.display = 'none';
            if (data.img_src) {
                facesHTML = facesContent.innerHTML;
                img_alt = "' alt='" + data.img_src.slice(13) + "'/>";
                facesContent.innerHTML = "<img src='/screenshots/" + data.img_src + img_alt + facesHTML;
            }
        })
        .catch(error => console.error('Error:', error));
    }
    else {
        nameInput.focus();
    }
});