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

# Global State for Telemetry HUD
system_state = {
    "mode": "MANUAL",
    "alert": "All Clear",
    "distance": 0.0
}

# --- MQTT CALLBACKS ---
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
    except Exception as e:
        pass

# Initialize Flask and MQTT
app = Flask(__name__)
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

print("Connecting to MQTT Broker...")
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

# Initialize Camera
camera = cv2.VideoCapture(0)

# --- FLASK ROUTES ---
def generate_frames():
    """Captures frames from OpenCV and converts them to a web stream."""
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            # Encode frame to JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            # Yield multipart stream for the browser
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    """Serves the main HTML dashboard."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/video_feed')
def video_feed():
    """Route for the HTML image tag to stream the video."""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/command/<action>')
def command(action):
    """API route triggered by HTML buttons to send MQTT messages."""
    if action in ["FORWARD", "REVERSE", "LEFT", "RIGHT", "STOP"]:
        mqtt_client.publish(TOPIC_CONTROL, action)
        print(f"Published: {action}")
    elif action in ["AUTO", "MANUAL"]:
        mqtt_client.publish(TOPIC_MODE, action)
        print(f"Mode Switched to: {action}")
    return "OK", 200

@app.route('/api/status')
def get_status():
    """API route for the frontend to poll live telemetry."""
    return jsonify(system_state)

# --- HTML FRONTEND TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>AGV Command Center</title>
    <style>
        :root {
            --bg-dark: #0f172a;
            --panel-bg: #1e293b;
            --accent-blue: #38bdf8;
            --accent-green: #10b981;
            --alert-red: #ef4444;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }
        
        body { 
            background-color: var(--bg-dark); 
            color: var(--text-main); 
            font-family: 'Segoe UI', system-ui, sans-serif; 
            text-align: center; 
            margin: 0; 
            padding: 0; 
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
        }
        
        /* Heads Up Display (HUD) Banner */
        #hud-banner {
            width: 100%;
            padding: 15px 20px;
            background-color: var(--panel-bg);
            border-bottom: 2px solid var(--accent-green);
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-sizing: border-box;
            font-weight: 600;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
            transition: border-color 0.3s ease;
        }
        
        .hud-stat { display: flex; flex-direction: column; text-align: left; }
        .hud-label { font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px;}
        .hud-value { font-size: 1.25rem; margin-top: 2px; }
        #alert-text { font-weight: bold; color: var(--accent-green); }

        /* Camera Feed */
        .camera-container { 
            width: 95%; 
            max-width: 640px; 
            margin: 20px auto; 
            border: 2px solid #334155; 
            border-radius: 12px; 
            overflow: hidden; 
            background: #000;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
            position: relative;
        }
        .camera-container img { width: 100%; height: auto; display: block; aspect-ratio: 4/3; object-fit: cover;}
        .rec-dot {
            position: absolute; top: 15px; right: 15px;
            width: 12px; height: 12px; background: red;
            border-radius: 50%; animation: blink 1.5s infinite;
        }
        @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.2; } 100% { opacity: 1; } }

        /* Mode Toggles */
        .mode-container { margin: 10px auto 20px auto; display: flex; gap: 15px; background: var(--panel-bg); padding: 8px; border-radius: 50px;}
        .mode-btn { 
            padding: 12px 24px; font-size: 14px; font-weight: bold; border-radius: 40px; 
            border: none; cursor: pointer; transition: 0.2s; letter-spacing: 1px; color: var(--text-main);
        }
        .mode-manual { background: transparent; border: 1px solid #475569; }
        .mode-auto { background: transparent; border: 1px solid #475569; }
        .active-mode { background: var(--accent-blue); border-color: var(--accent-blue); box-shadow: 0 0 15px rgba(56, 189, 248, 0.4);}

        /* Control Pad Layout */
        .controls { 
            display: grid; 
            grid-template-columns: repeat(3, 70px); 
            grid-template-rows: repeat(3, 70px); 
            gap: 15px; 
            justify-content: center;
            margin-bottom: 40px;
        }
        
        .btn { 
            background: var(--panel-bg); color: var(--text-main); border: 2px solid #334155; 
            font-size: 24px; border-radius: 16px; cursor: pointer; transition: all 0.1s; 
            user-select: none; display: flex; align-items: center; justify-content: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .btn:active { background: var(--accent-blue); border-color: var(--accent-blue); transform: translateY(4px); box-shadow: none;}
        .btn-up { grid-column: 2; grid-row: 1; }
        .btn-left { grid-column: 1; grid-row: 2; }
        .btn-stop { grid-column: 2; grid-row: 2; border-color: var(--alert-red); color: var(--alert-red); }
        .btn-stop:active { background: var(--alert-red); color: white; }
        .btn-right { grid-column: 3; grid-row: 2; }
        .btn-down { grid-column: 2; grid-row: 3; }
    </style>
</head>
<body>
    
    <!-- HUD Banner -->
    <div id="hud-banner">
        <div class="hud-stat">
            <span class="hud-label">System Status</span>
            <span class="hud-value" id="alert-text">All Clear</span>
        </div>
        <div class="hud-stat" style="text-align: right;">
            <span class="hud-label">Proximity</span>
            <span class="hud-value"><span id="dist-text">0.0</span> cm</span>
        </div>
    </div>

    <!-- Live Video Feed -->
    <div class="camera-container">
        <div class="rec-dot"></div>
        <img src="/video_feed" alt="Live Camera Stream">
    </div>

    <!-- Mode Toggles -->
    <div class="mode-container">
        <button id="btn-manual" class="mode-btn active-mode" onclick="userSetMode('MANUAL')">MANUAL</button>
        <button id="btn-auto" class="mode-btn" onclick="userSetMode('AUTO')">AUTO</button>
    </div>

    <!-- Directional Pad -->
    <div class="controls">
        <button class="btn btn-up" onmousedown="sendCmd('FORWARD')" onmouseup="sendCmd('STOP')" onmouseleave="sendCmd('STOP')" ontouchstart="event.preventDefault(); sendCmd('FORWARD')" ontouchend="event.preventDefault(); sendCmd('STOP')">▲</button>
        <button class="btn btn-left" onmousedown="sendCmd('LEFT')" onmouseup="sendCmd('STOP')" onmouseleave="sendCmd('STOP')" ontouchstart="event.preventDefault(); sendCmd('LEFT')" ontouchend="event.preventDefault(); sendCmd('STOP')">◀</button>
        <button class="btn btn-stop" onmousedown="sendCmd('STOP')" ontouchstart="event.preventDefault(); sendCmd('STOP')">■</button>
        <button class="btn btn-right" onmousedown="sendCmd('RIGHT')" onmouseup="sendCmd('STOP')" onmouseleave="sendCmd('STOP')" ontouchstart="event.preventDefault(); sendCmd('RIGHT')" ontouchend="event.preventDefault(); sendCmd('STOP')">▶</button>
        <button class="btn btn-down" onmousedown="sendCmd('REVERSE')" onmouseup="sendCmd('STOP')" onmouseleave="sendCmd('STOP')" ontouchstart="event.preventDefault(); sendCmd('REVERSE')" ontouchend="event.preventDefault(); sendCmd('STOP')">▼</button>
    </div>

    <script>
        // Send command to Python backend
        function sendCmd(action) {
            fetch('/command/' + action).catch(e => console.error(e));
        }

        // Handle user actively clicking the mode button
        function userSetMode(mode) {
            sendCmd(mode);
            updateUIMode(mode); // Optimistic UI update
        }

        // Handle UI Mode switching visually (NO NETWORK CALLS HERE)
        function updateUIMode(mode) {
            document.getElementById('btn-manual').classList.remove('active-mode');
            document.getElementById('btn-auto').classList.remove('active-mode');
            if (mode === 'MANUAL') {
                document.getElementById('btn-manual').classList.add('active-mode');
            } else {
                document.getElementById('btn-auto').classList.add('active-mode');
            }
        }

        // Live Telemetry Polling (Every 500ms)
        setInterval(() => {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    // Update Distance
                    document.getElementById('dist-text').innerText = data.distance;
                    
                    // Update Alerts & Colors
                    const banner = document.getElementById('hud-banner');
                    const alertText = document.getElementById('alert-text');
                    
                    if (data.alert !== "All Clear") {
                        banner.style.borderBottomColor = "var(--alert-red)";
                        alertText.style.color = "var(--alert-red)";
                        alertText.innerText = "⚠️ " + data.alert;
                    } else {
                        banner.style.borderBottomColor = "var(--accent-green)";
                        alertText.style.color = "var(--accent-green)";
                        alertText.innerText = "All Clear";
                    }

                    // Keep Mode Buttons Sync'd with hardware VISUALLY ONLY. 
                    // This fixes the infinite loop bug!
                    updateUIMode(data.mode); 
                })
                .catch(err => console.error("Telemetry API error", err));
        }, 500);
        
        // Prevent default context menu on long press (mobile)
        window.oncontextmenu = function(event) {
             event.preventDefault();
             event.stopPropagation();
             return false;
        };
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    # Run the server on all network interfaces (0.0.0.0) at port 5000
    app.run(host='0.0.0.0', port=5000, threaded=True)