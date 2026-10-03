from flask import Flask, Response
import cv2
import time

app = Flask(__name__)

# --- INITIALIZE CAMERA ---
print("Initializing Camera Pipeline...")
camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
success, _ = camera.read()

if not success:
    print("V4L2 failed. Attempting libcamera pipeline for newer Pi OS...")
    camera.release()
    pipeline = "libcamerasrc ! video/x-raw, width=640, height=480, framerate=15/1 ! videoconvert ! appsink"
    camera = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

if camera.isOpened():
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    camera.set(cv2.CAP_PROP_FPS, 15)
else:
    print("CRITICAL WARNING: Camera not found!")

# --- VIDEO STREAM GENERATOR ---
def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            time.sleep(0.1)
            continue
            
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        
        # Yield MJPEG frame
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# --- FLASK ROUTE ---
@app.route('/video_feed')
def video_feed():
    # Adding CORS headers so the ESP32 webpage is allowed to load this video
    response = Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

if __name__ == '__main__':
    # Run on Port 5000, accessible to anyone on the ESP32 network
    print("Starting Live Video Stream on Port 5000...")
    app.run(host='0.0.0.0', port=5000, threaded=True)