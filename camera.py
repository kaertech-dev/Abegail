import cv2
import os
import time
# import numpy as np
# from deepface import DeepFace
# from deepface.modules.streaming import search_identity, grab_facial_areas, extract_facial_areas, perform_facial_recognition

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

IDENTIFIED_IMG_SIZE = 112
TEXT_COLOR = (255, 255, 255)
FREEZE_DURATION = 30 * 2

#video feed dimensions = 640 x 480
BASE_PATH = 'c:/Users/ai/OneDrive/Documents/project_abegail/Abegail/mcp-server-demo/mcp-server-demo/'
FACE_RECOG_PATH = 'c:/Users/ai/OneDrive/Documents/project_abegail/Abegail/mcp-server-demo/mcp-server-demo/known_faces/'
GENERIC_PATH = 'c:/Users/ai/OneDrive/Documents/project_abegail/Abegail/mcp-server-demo/mcp-server-demo/webcam/'

face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

# DeepFace.build_model(model_name="VGG-Face", task="facial_recognition")
# _ = search_identity(
#     detected_face=np.zeros([224, 224, 3]),
#     db_path=FACE_RECOG_PATH,
#     detector_backend='opencv',
#     distance_metric='euclidean',
#     model_name='VGG-Face',
# )

class VideoCamera:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)

        self.faces_coordinates = []

        self.toggleBox = True
        self.screenshot = False
        self.freeze = False
        self.freezed_img = None
        self.image_name = GENERIC_PATH
        # self.freeze_ctr = FREEZE_DURATION
        # self.sspath = GENERIC_PATH
        # self.count = 0

    def isOpened(self):
        return self.cap.isOpened()
    
    def open(self):
        self.cap = cv2.VideoCapture(0)
        print('Capturing started.')
    
    def release(self):
        self.cap.release()
        print('Capturing stopped.')
    
    def toggleFaceBox(self, status=True):
        self.toggleBox = status

    def takeScreenshot(self, nameInput = ''):
        self.screenshot = True
        if nameInput:
            self.image_name = FACE_RECOG_PATH + f"{nameInput}.jpg"
        else:
            img_id = str(time.time()).split('.')
            self.image_name = GENERIC_PATH + f"img_{img_id[0]}.jpg"
            print(self.image_name)
        
    def command(self, cmd_dict: dict):
        if "videoToggle" in cmd_dict:
            pass
        elif "takeScreenshot" in cmd_dict:
            pass
        elif "faceRecog" in cmd_dict:
            pass
        elif "freezeFrame" in cmd_dict:
            pass
        elif "submitName" in cmd_dict:
            pass

    def get_frame(self):
        success, frame = self.cap.read()
        if not success:
            return None
        
        # raw_img = frame.copy()
        
        # self.faces_coordinates = grab_facial_areas(img=raw_img, detector_backend='opencv', anti_spoofing=False)
        # self.detected_faces = extract_facial_areas(img=raw_img, faces_coordinates=self.faces_coordinates)

        # img = raw_img.copy()
        # img = perform_facial_recognition(
        #     img=img,
        #     faces_coordinates=self.faces_coordinates,
        #     detected_faces=self.detected_faces,
        #     db_path=FACE_RECOG_PATH,
        #     detector_backend='opencv',
        #     distance_metric='euclidean',
        #     model_name='VGG-Face',
        # )

        if self.freeze:
            if self.freezed_img is None:
                self.freezed_img = frame.copy()
            frame = self.freezed_img
        else:
            self.freezed_img = None
        
        # img = frame if self.freezed_img is not None else self.freezed_img

        if self.screenshot:
            # image_name = self.sspath + f"img_{datetime.now()}.jpg"
            # img = frame if not self.freeze else self.freezed_img
            cv2.imwrite(self.image_name, frame)
            self.screenshot = False
            self.image_name = GENERIC_PATH

        # if self.toggleBox:
        #     cv2.ellipse(frame, (320,240), (95,130), 0, 0, 360, 255, 2)
        
        # if self.toggleBox:
        #     # grayscale for easier detection
        #     gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        #     faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        #     for (x, y, w, h) in faces:
        #         # draw detection boxes
        #         cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        #     cv2.ellipse(frame, (320,240), (95,130), 0, 0, 360, 255, 2)
        
        img = frame if not self.freeze else self.freezed_img
        _, jpeg = cv2.imencode('.jpg', img)
        # _, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes()
