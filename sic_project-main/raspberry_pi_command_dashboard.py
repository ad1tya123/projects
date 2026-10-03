from flask import Flask, Response, render_template_string, jsonify
import cv2
import paho.mqtt.client as mqtt
import json

# --- CONFIGURATION ---
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
TOPIC_CONTROL = "factory/rover/control"
TOPIC_MODE = "factory/rover/mode"
TOPIC_STATUS = "factory/rover/status"

# Global state to pass MQTT data to the web UI
system_state = {
    "mode": "AUTO",
    "alert": "All Clear",
    "distance": 0.0
}

# --- MQTT SETUP ---
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT. Subscribing to telemetry...")
    client.subscribe(TOPIC_STATUS)

def on_message(client, userdata, msg):
    global system_state
    try:
        payload = json.loads(msg.payload.decode())
        system_state["mode"] = payload.get("mode", system_state["mode"])
        system_state["alert"] = payload.get("alert", "All Clear")
        system_state["distance"] = round(payload.get("distance", 0.0), 1)
        print(f"Update: {system_state['alert']} | {system_state['distance']}cm")
    except Exception as e:
        pass

app = Flask(__name__)
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

camera = cv2.VideoCapture(0)

# --- FLASK ROUTES ---
def generate_frames():
    while True:
        success, frame = camera.read()
        if not success: break
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/status')
def get_status():
    """Endpoint for the browser to fetch live telemetry dynamically"""
    return jsonify(system_state)

@app.route('/command/<action>')
def command(action):
    if action in ["FORWARD", "REVERSE", "LEFT", "RIGHT", "STOP"]:
        mqtt_client.publish(TOPIC_CONTROL, action)
    elif action in ["AUTO", "MANUAL"]:
        mqtt_client.publish(TOPIC_MODE, action)
    return "OK", 200

# --- HTML / JS FRONTEND ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>AGV Command Center</title>
    <style>
        body { background-color: #121212; color: white; font-family: 'Segoe UI', Tahoma, sans-serif; text-align: center; margin: 0; padding: 0; }
        .camera-container { width: 95%; max-width: 600px; margin: 0 auto; border: 3px solid #333; border-radius: 8px; overflow: hidden; background: #000; }
        .camera-container img { width: 100%; height: auto; display: block; }
        
        /* Dynamic Alert Banner */
        #alert-banner { padding: 15px; font-size: 20px; font-weight: bold; margin-bottom: 10px; background-color: #4CAF50; transition: 0.3s; }
        
        /* Controls */
        .controls { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; max-width: 300px; margin: 20px auto; }
        .btn { background: #333; color: white; border: none; padding: 20px; font-size: 24px; border-radius: 10px; cursor: pointer; user-select: none;}
        .btn:active { background: #00d2ff; }
        .btn-stop { background: #d32f2f; } .btn-stop:active { background: #ff5252; }
        .mode-container { margin: 20px auto; display: flex; justify-content: center; gap: 15px; }
        .mode-btn { padding: 15px 30px; font-size: 16px; font-weight: bold; border-radius: 5px; border: none; cursor: pointer; background: #555; color: white;}
    </style>
</head>
<body>
    <div id="alert-banner">System Normal | Mode: AUTO</div>
    
    <div class="camera-container">
        <img src="{{ url_for('video_feed') }}" alt="Live Camera">
    </div>

    <div class="mode-container">
        <button class="mode-btn" onclick="sendCmd('MANUAL')">MANUAL</button>
        <button class="mode-btn" onclick="sendCmd('AUTO')">AUTO</button>
    </div>

    <div class="controls">
        <div></div>
        <button class="btn" onmousedown="sendCmd('FORWARD')" onmouseup="sendCmd('STOP')" ontouchstart="sendCmd('FORWARD')" ontouchend="sendCmd('STOP')">▲</button>
        <div></div>
        <button class="btn" onmousedown="sendCmd('LEFT')" onmouseup="sendCmd('STOP')" ontouchstart="sendCmd('LEFT')" ontouchend="sendCmd('STOP')">◀</button>
        <button class="btn btn-stop" onclick="sendCmd('STOP')">■</button>
        <button class="btn" onmousedown="sendCmd('RIGHT')" onmouseup="sendCmd('STOP')" ontouchstart="sendCmd('RIGHT')" ontouchend="sendCmd('STOP')">▶</button>
        <div></div>
        <button class="btn" onmousedown="sendCmd('REVERSE')" onmouseup="sendCmd('STOP')" ontouchstart="sendCmd('REVERSE')" ontouchend="sendCmd('STOP')">▼</button>
        <div></div>
    </div>

    <script>
        function sendCmd(action) {
            fetch('/command/' + action);
        }

        // Poll the Python backend every 500ms for fresh sensor data
        setInterval(() => {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    const banner = document.getElementById('alert-banner');
                    if (data.alert !== "All Clear") {
                        banner.style.backgroundColor = '#d32f2f'; // Red for danger
                        banner.innerText = "⚠️ " + data.alert + " (" + data.distance + " cm)";
                    } else {
                        banner.style.backgroundColor = '#4CAF50'; // Green for safe
                        banner.innerText = "System Normal | Mode: " + data.mode;
                    }
                })
                .catch(err => console.error("API error", err));
        }, 500);
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)