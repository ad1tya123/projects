import cv2
import paho.mqtt.client as mqtt
import base64
import time
import numpy as np

# --- CONFIGURATION ---
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
TOPIC_VIDEO = "factory/rover/video"
TARGET_FPS = 8  # Keep this low (5-10) so the public broker doesn't ban you!

# --- MQTT SETUP ---
try:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
except AttributeError:
    client = mqtt.Client()

print("Connecting to EMQX Broker...")
try:
    client.connect_async(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
except Exception as e:
    print(f"MQTT Startup Warning: {e}")

# --- CAMERA SETUP ---
print("Initializing Camera Pipeline...")
# Try standard V4L2 first
camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
success, _ = camera.read()

if not success:
    print("V4L2 failed. Attempting libcamera pipeline...")
    camera.release()
    pipeline = "libcamerasrc ! video/x-raw, width=640, height=480, framerate=15/1 ! videoconvert ! appsink"
    camera = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

# Force a lower resolution to keep MQTT payloads small (< 50KB)
if camera.isOpened():
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
else:
    print("CRITICAL WARNING: Camera not found!")

# --- MAIN LOOP ---
print(f"Streaming Video over MQTT to topic '{TOPIC_VIDEO}'...")
try:
    while True:
        start_time = time.time()
        success, frame = camera.read()
        
        if success:
            # Compress the image heavily (JPEG quality 40)
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 40]
            ret, buffer = cv2.imencode('.jpg', frame, encode_param)
            
            # Convert binary image data to a Base64 String
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            
            # Publish to the broker
            client.publish(TOPIC_VIDEO, jpg_as_text, qos=0)
        
        # Throttle the loop to achieve the target FPS
        elapsed = time.time() - start_time
        sleep_time = (1.0 / TARGET_FPS) - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)

except KeyboardInterrupt:
    print("\nStopping Camera Stream...")
finally:
    camera.release()
    client.loop_stop()
    client.disconnect()