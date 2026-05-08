import cv2
import os
import time
from typing import List, Tuple, Any
from datetime import datetime, timedelta
import numpy as np
from numpy.typing import NDArray
from deepface import DeepFace
from deepface.modules.streaming import search_identity, grab_facial_areas, extract_facial_areas, highlight_facial_areas

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

BASE_PATH = os.getcwd()
FACE_RECOG_PATH = os.path.join(BASE_PATH, 'known_faces')
GENERIC_PATH = os.path.join(BASE_PATH, 'webcam')

#video feed dimensions = 640 x 480
IDENTIFIED_IMG_SIZE = 112
TEXT_BG = (255, 255, 255)
TEXT_COLOR = (0, 0, 0)

# face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
face_logs = {}

DeepFace.build_model(model_name="VGG-Face", task="facial_recognition")
print("Building face embeddings...")
_ = search_identity(
    detected_face=np.zeros([224, 224, 3]),
    db_path=FACE_RECOG_PATH,
    detector_backend='opencv',
    distance_metric='euclidean',
    model_name='VGG-Face',
)

# ----- main class and methods ----- #
class VideoCamera:
    def __init__(self):
        try:
            self.cap = cv2.VideoCapture(0)
        # self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        # self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        # self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        except Exception as e:
            print(e)

        self.faces_coordinates = []

        self.recogEnable = False
        self.screenshot = False
        self.freeze = False
        self.held_img = None
        self.image_name = GENERIC_PATH

    def isOpened(self):
        return self.cap.isOpened()
    
    def open(self):
        self.cap = cv2.VideoCapture(0)
        print('Capturing started.')
    
    def release(self):
        self.cap.release()
        print('Capturing stopped.')
        
    def command(self, cmd_dict: dict):
        if "videoToggle" in cmd_dict:
            if cmd_dict.get("videoToggle"):
                self.cap = cv2.VideoCapture(0)
                print('Capturing started.')
            else:
                self.cap.release()
                print('Capturing stopped.')
        elif "takeScreenshot" in cmd_dict:
            img_id = str(time.time()).split('.')
            self.image_name = f"webcam/img_{img_id[0]}.jpg"
            self.screenshot = True
            print("[Webcam] Screenshot saved.")
            return self.image_name
        elif "faceRecog" in cmd_dict:
            self.recogEnable = cmd_dict.get("faceRecog")
        elif "freezeFrame" in cmd_dict:
            self.freeze = cmd_dict.get("freezeFrame")
        elif "submitName" in cmd_dict:
            nameInput = cmd_dict.get("submitName")
            self.image_name = f"known_faces/{nameInput}.jpg"
            self.screenshot = True
            self.freeze = False
            print("[Webcam] Face registered with name: ", nameInput)
            return self.image_name

    def get_frame(self):
        success, frame = self.cap.read()
        if not success:
            return None
        
        if self.screenshot:
            img = frame if self.held_img is None else self.held_img
            cv2.imwrite(self.image_name, img)
            self.screenshot = False
            self.image_name = GENERIC_PATH

        if self.freeze:
            if self.held_img is None:
                # Turn off facial recognition first to remove bounding boxes
                self.recogEnable = False
                self.held_img = frame.copy()
            frame = self.held_img
        else:
            self.held_img = None
        
        if self.recogEnable:
            self.faces_coordinates = grab_facial_areas(img=frame, detector_backend='opencv', anti_spoofing=False)
            self.detected_faces = extract_facial_areas(img=frame, faces_coordinates=self.faces_coordinates)
            img = highlight_facial_areas(img=frame, faces_coordinates=self.faces_coordinates, anti_spoofing=False)

            frame = perform_facial_recognition(
                img=frame,
                faces_coordinates=self.faces_coordinates,
                detected_faces=self.detected_faces,
                db_path=FACE_RECOG_PATH,
                detector_backend='opencv',
                distance_metric='euclidean',
                model_name='VGG-Face',
            )
        
        _, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes()

# ---- Other functions ----- #
# Logger function
def detection_logger(nameList: List[str]):
    global face_logs
    curr_time = datetime.now()

    if face_logs == {}:
        pass
    elif curr_time < list(face_logs.keys())[-1] + timedelta(minutes=1):
        return

    face_logs[curr_time] = nameList
    labels = '-'.join(nameList)

    with open('face_detection_logs.txt', 'a') as log_file:
        new_log = f"[{curr_time.strftime("%d/%b/%Y %H:%M:%S")}] - - {labels}\n"
        log_file.write(new_log)

# Modified functions from DeepFace library
def perform_facial_recognition(
    img: NDArray[Any],
    detected_faces: List[NDArray[Any]],
    faces_coordinates: List[Tuple[int, int, int, int, bool, float]],
    db_path: str,
    detector_backend: str,
    distance_metric: str,
    model_name: str,
) -> NDArray[Any]:
    face_names = []
    for idx, (x, y, w, h, is_real, antispoof_score) in enumerate(faces_coordinates):
        detected_face = detected_faces[idx]
        target_label, target_img, confidence = search_identity(
            detected_face=detected_face,
            db_path=db_path,
            detector_backend=detector_backend,
            distance_metric=distance_metric,
            model_name=model_name,
        )
        
        if target_label is None:
            continue

        if target_img is None:
            continue

        # detection_logger(target_label)
        face_names.append(target_label.replace('.jpg', ''))

        img = overlay_identified_face(
            img=img,
            target_img=target_img,
            label=target_label,
            x=x,
            y=y,
            w=w,
            h=h,
            confidence=confidence,
        )
    detection_logger(face_names)

    return img

def overlay_identified_face(
    img: NDArray[Any],
    target_img: NDArray[Any],
    label: str,
    x: int,
    y: int,
    w: int,
    h: int,
    confidence: float,
) -> NDArray[Any]:
    """
    Overlay the identified face onto image itself
    Args:
        img (np.ndarray): image itself
        target_img (np.ndarray): identified face's image
        label (str): name of the identified face
        x (int): x coordinate of the face on the given image
        y (int): y coordinate of the face on the given image
        w (int): w coordinate of the face on the given image
        h (int): h coordinate of the face on the given image
        confidence (float): confidence score of the identified face
    Returns:
        img (np.ndarray): image with overlayed identity
    """

    # show classification label with confidence
    label = f"{label} ({confidence}%)"
    (text_width, text_height) = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]

    rect_topleft = (x + int(w/2) - int(text_width/2) - 2, y + h)
    rect_botright = (x + int(w/2) + int(text_width/2) + 2, y + h + text_height + 4)

    cv2.rectangle(img, rect_topleft, rect_botright, TEXT_BG, cv2.FILLED,)

    cv2.putText(img,
        label,
        (x + int(w/2) - int(text_width/2), y + h + text_height + 2),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, TEXT_COLOR, 1,)
    
    return img