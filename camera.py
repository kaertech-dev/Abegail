import cv2

face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

class VideoCamera:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.toggleBox = True

    def isOpened(self):
        return self.cap.isOpened()
    
    def open(self):
        self.cap = cv2.VideoCapture(0)
        print('Capturing started.')
    
    def release(self):
        self.cap.release()
        print('Capturing stopped.')
    
    def toggleFaceBox(self, status=True):
        # if self.toggleBox == True:
        #     self.toggleBox = False
        # else:
        #     self.toggleBox = True
        self.toggleBox = status

    def get_frame(self):
        success, frame = self.cap.read()
        if not success:
            return None
        
        if self.toggleBox:
            # grayscale for easier detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            for (x, y, w, h) in faces:
                # draw detection boxes
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        _, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes()

def main():
    face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame.")
            break
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
       
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        cv2.imshow('Face Detection', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

# def load_known_faces():
#     for filename in os.listdir(app.config['UPLOAD_FOLDER']):
#         if filename.endswith(tuple(ALLOWED_EXTENSIONS)):
#             image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#             image = face_recognition.load_image_file(image_path)
#             encodings = face_recognition.face_encodings(image)
#             if encodings:
#                 known_face_encodings.append(encodings[0])
#                 name = os.path.splitext(filename)[0]
#                 known_face_names.append(name)

# def generate_frames():
#     video_capture = cv2.VideoCapture(0)
#     while True:
#         ret, frame = video_capture.read()
#         small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
#         rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
#         face_locations = face_recognition.face_locations(rgb_small_frame)
#         face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
#         # ... (face matching and drawing rectangles)
#         ret, buffer = cv2.imencode('.jpg', frame)
#         yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# if __name__ == "__main__":
#     main()