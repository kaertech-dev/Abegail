// function fetchStatus() {
//     fetch('/webcam_get')
//         .then(response => response.json())
//         .then(data => {
//             toggleBox.checked = data.status;
//             console.log("Checkbox:", toggleBox.checked);
//         })
//         .catch(error => console.error('Error fetching status:', error));
// }

// fetchStatus();

// const toggleBox = document.getElementById("toggleBox");
// toggleBox.addEventListener('change', function () {
//     fetch('/webcam_update', {
//         method: 'POST',
//         headers: {
//             'Content-Type': 'application/json',
//         },
//         body: JSON.stringify({
//             change_state: toggleBox.checked
//         })
//     })
//         .then(response => response.json())
//         .then(data => {
//             console.log("Face detect:", toggleBox.checked);
//         })
//         .catch(error => console.error('Error:', error));
// });

const feedStatus = document.getElementById("feedStatus");
const feedIcon = document.getElementById("toggleFeed");
const videoFeed = document.getElementById("live-feed");
function toggleFeed() {
    if (feedStatus.checked == true) {
        feedStatus.checked = false;
        videoFeed.style.opacity = '0';
        feedIcon.innerHTML = '<i class="fa-solid fa-video"></i>';
        feedIcon.title = "Enable video feed";
    }
    else if (feedStatus.checked == false) {
        feedStatus.checked = true;
        videoFeed.style.opacity = '100%';
        feedIcon.innerHTML = '<i class="fa-solid fa-video-slash"></i>';
        feedIcon.title = "Disable video feed";
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
        console.log("Video feed:", feedStatus.checked);
    })
    .catch(error => console.error('Error:', error));
};

const takeShot = document.getElementById("takeShot");
const flash = document.getElementById("flash");
takeShot.addEventListener('click', () => {
    const flash = document.getElementById("flash");
    flash.style.animation = 'visual-flash 0.6s';
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
        flash.style.animation = 'none';
    })
    .catch(error => console.error('Error:', error));
});

const recogStatus = document.getElementById("recogStatus");
const toggleRecognition = document.getElementById("toggleRecognition");
function toggleRecog() {
    if (recogStatus.checked == true) {
        recogStatus.checked = false;
    }
    else if (recogStatus.checked == false) {
        recogStatus.checked = true;
    }
    
    fetch('/webcam_update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            faceRecog: recogStatus.checked
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log("Facial recognition:", recogStatus.checked);
    })
    .catch(error => console.error('Error:', error));
};

const ellipseOverlay = document.getElementById("registerOverlay");
const controlOverlay = document.getElementById("confirmBox");
function toggleOverlay() {
    if (ellipseOverlay.style.display == 'none') {
        ellipseOverlay.style.display = 'block';
        controlOverlay.style.display = 'none';
    }
    else if (ellipseOverlay.style.display == 'block') {
        ellipseOverlay.style.display = 'none';
    }
    // console.log("Overlay:", overlay.style.display);
};

// face registration click
// ellipse overlay on feed
// capture = freeze frame, remove ellipse overlay, new controls overlay
// cancel = remove ellipse, no controls overlay

// submit = unfreeze, remove ellipse, no controls overlay
// retake = unfreeze, add ellipse, no controls overlay

const captureButton = document.getElementById("registerCapture");
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
        console.log("Freeze frame.");
    })
    .catch(error => console.error('Error:', error));
});

// const regCancel = document.getElementById("registerCancel");
// regCancel.addEventListener('click', () => {
//     ellipseOverlay.style.display = 'none';
// });

const takeCancel = document.getElementById("retakeFace");
takeCancel.addEventListener('click', () => {
    // controlOverlay.style.display = 'none';
    // ellipseOverlay.style.display = 'block';
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
        console.log("Unfreeze frame.");
    })
    .catch(error => console.error('Error:', error));
});

const submitFace = document.getElementById("submitFace");
const nameInput = document.getElementById("nameField");
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
        })
        .catch(error => console.error('Error:', error));
    }
    else {
        nameInput.focus();
    }

});