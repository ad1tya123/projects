#include <WiFi.h>
#include <WebServer.h>

// Set your Rover's Wi-Fi Name and Password
const char* ssid = "ESP32_Rover";
const char* password = "password123"; // Must be at least 8 characters         

WebServer server(80);

// Motor Pins (Updated for your hardware setup)
const int leftMotorForward = 26;  
const int leftMotorBackward = 27; 
const int rightMotorForward = 14; 
const int rightMotorBackward = 32;

// The HTML & CSS for the Webpage (Stored in ESP32 memory)
const char* html_page = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
  <title>ESP32 Rover</title>
  <style>
    body { font-family: Arial; text-align: center; margin-top: 50px; background-color: #222; color: white; }
    .btn { background-color: #4CAF50; border: none; color: white; padding: 20px; font-size: 25px; margin: 10px; border-radius: 15px; width: 100px; height: 100px; touch-action: manipulation; }
    .btn:active { background-color: #45a049; }
    .btn-stop { background-color: #f44336; }
    .btn-stop:active { background-color: #da190b; }
    .row { display: flex; justify-content: center; }
  </style>
  <script>
    function sendCommand(cmd) {
      fetch('/' + cmd);
    }
  </script>
</head>
<body>
  <h1>Rover Control</h1>
  <div class="row">
    <button class="btn" onclick="sendCommand('forward')">▲</button>
  </div>
  <div class="row">
    <button class="btn" onclick="sendCommand('left')">◀</button>
    <button class="btn btn-stop" onclick="sendCommand('stop')">X</button>
    <button class="btn" onclick="sendCommand('right')">▶</button>
  </div>
  <div class="row">
    <button class="btn" onclick="sendCommand('backward')">▼</button>
  </div>
</body>
</html>
)rawliteral";

void setup() {
  Serial.begin(115200);

  pinMode(leftMotorForward, OUTPUT);
  pinMode(leftMotorBackward, OUTPUT);
  pinMode(rightMotorForward, OUTPUT);
  pinMode(rightMotorBackward, OUTPUT);
  stopMotors();

  // Start the ESP32 Access Point
  Serial.println("Starting Wi-Fi Access Point...");
  WiFi.softAP(ssid, password);
  IPAddress IP = WiFi.softAPIP();
  Serial.print("AP IP address: ");
  Serial.println(IP);

  // Setup Web Server Routes
  server.on("/", []() { server.send(200, "text/html", html_page); });
  
  server.on("/forward", []() { 
    digitalWrite(leftMotorForward, HIGH); digitalWrite(leftMotorBackward, LOW);
    digitalWrite(rightMotorForward, HIGH); digitalWrite(rightMotorBackward, LOW);
    server.send(200, "text/plain", "Moving Forward"); 
  });
  
  server.on("/backward", []() { 
    digitalWrite(leftMotorForward, LOW); digitalWrite(leftMotorBackward, HIGH);
    digitalWrite(rightMotorForward, LOW); digitalWrite(rightMotorBackward, HIGH);
    server.send(200, "text/plain", "Moving Backward"); 
  });
  
  server.on("/left", []() { // Tank turn left
    digitalWrite(leftMotorForward, LOW); digitalWrite(leftMotorBackward, HIGH);
    digitalWrite(rightMotorForward, HIGH); digitalWrite(rightMotorBackward, LOW);
    server.send(200, "text/plain", "Turning Left"); 
  });
  
  server.on("/right", []() { // Tank turn right
    digitalWrite(leftMotorForward, HIGH); digitalWrite(leftMotorBackward, LOW);
    digitalWrite(rightMotorForward, LOW); digitalWrite(rightMotorBackward, HIGH);
    server.send(200, "text/plain", "Turning Right"); 
  });
  
  server.on("/stop", []() { stopMotors(); server.send(200, "text/plain", "Stopped"); });

  server.begin();
}

void loop() {
  server.handleClient();
}

void stopMotors() {
  digitalWrite(leftMotorForward, LOW);
  digitalWrite(leftMotorBackward, LOW);
  digitalWrite(rightMotorForward, LOW);
  digitalWrite(rightMotorBackward, LOW);
}