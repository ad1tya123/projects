#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// --- NETWORK CREDENTIALS ---
const char* ssid = "SIC COE";
const char* password = "Samsung@2025";
const char* mqtt_server = "broker.emqx.io";
const int mqtt_port = 1883;

// --- MQTT TOPICS ---
const char* topic_status  = "factory/rover/status";
const char* topic_control = "factory/rover/control";
const char* topic_mode    = "factory/rover/mode";

// --- HARDWARE PIN CONFIGURATION ---
const int MOTOR_L_PWM = 12;
const int MOTOR_L_IN1 = 13;
const int MOTOR_L_IN2 = 14;
const int MOTOR_R_PWM = 25;
const int MOTOR_R_IN3 = 26;
const int MOTOR_R_IN4 = 27;

const int IR_LEFT_PIN  = 34;
const int IR_RIGHT_PIN = 35;

// Ultrasonic 1 (Front - Obstacle Detection)
const int ULTRA_F_TRIG = 33;
const int ULTRA_F_ECHO = 23;

// Ultrasonic 2 (Rear - Reverse Assist)
const int ULTRA_R_TRIG = 5;
const int ULTRA_R_ECHO = 18;

// Gas Sensor & Alarm
const int GAS_SENSOR_PIN = 4;
const int BUZZER_PIN = 19;

// --- SYSTEM STATES ---
enum RoverState { STATE_MANUAL, STATE_AUTO };
RoverState currentState = STATE_MANUAL;
String currentManualCmd = "STOP";

// --- SENSOR VARIABLES & FLAGS ---
float frontDist = 999.0;
float rearDist = 999.0;
const float STOP_DISTANCE = 20.0; // cm

bool obstacleAheadFlag = false;
bool objectBehindFlag = false;
bool gasAlertFlag = false;

unsigned long lastSensorTime = 0;
const unsigned long SENSOR_INTERVAL = 100; // Read sensors every 100ms

// --- OBJECT INITIALIZATION ---
WiFiClient espClient;
PubSubClient client(espClient);
LiquidCrystal_I2C lcd(0x27, 16, 2);

// --- PROTOTYPES ---
void setupWifi();
void mqttCallback(char* topic, byte* message, unsigned int length);
void reconnectMqtt();
void driveMotors(int leftSpeed, int rightSpeed);
void stopMotors();
void runLineFollowing();
float getDistance(int trigPin, int echoPin);
void publishStatus(String alert, float dist);

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);
  lcd.init();
  lcd.backlight();
  lcd.print("Booting System..");

  setupWifi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(mqttCallback);

  pinMode(MOTOR_L_PWM, OUTPUT); pinMode(MOTOR_L_IN1, OUTPUT); pinMode(MOTOR_L_IN2, OUTPUT);
  pinMode(MOTOR_R_PWM, OUTPUT); pinMode(MOTOR_R_IN3, OUTPUT); pinMode(MOTOR_R_IN4, OUTPUT);
  pinMode(IR_LEFT_PIN, INPUT);  pinMode(IR_RIGHT_PIN, INPUT);
  pinMode(ULTRA_F_TRIG, OUTPUT); pinMode(ULTRA_F_ECHO, INPUT);
  pinMode(ULTRA_R_TRIG, OUTPUT); pinMode(ULTRA_R_ECHO, INPUT);
  
  pinMode(GAS_SENSOR_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  lcd.clear();
  lcd.print("System Ready");
  publishStatus("All Clear", 0.0);
}

void loop() {
  if (!client.connected()) reconnectMqtt();
  client.loop();

  // 1. Read distances every 100ms to avoid blocking the main loop
  if (millis() - lastSensorTime >= SENSOR_INTERVAL) {
    frontDist = getDistance(ULTRA_F_TRIG, ULTRA_F_ECHO);
    delay(10); // Prevent ultrasonic wave cross-talk
    rearDist = getDistance(ULTRA_R_TRIG, ULTRA_R_ECHO);
    lastSensorTime = millis();
    
    // Evaluate Front Obstacles
    if (frontDist > 0 && frontDist <= STOP_DISTANCE) {
      if (!obstacleAheadFlag) {
        obstacleAheadFlag = true;
        publishStatus("Obstacle Ahead", frontDist);
        lcd.clear(); lcd.print("FRONT OBSTACLE!"); lcd.setCursor(0,1); lcd.print(frontDist); lcd.print(" cm");
      }
    } else if (obstacleAheadFlag) {
      obstacleAheadFlag = false; // Obstacle cleared, resume normal operation
      publishStatus("All Clear", frontDist);
      lcd.clear(); lcd.print(currentState == STATE_AUTO ? "Mode: AUTO" : "Mode: MANUAL");
    }

    // Evaluate Rear Obstacles (Only relevant if reversing in manual)
    if (currentManualCmd == "REVERSE" && currentState == STATE_MANUAL) {
      if (rearDist > 0 && rearDist <= STOP_DISTANCE) {
        if (!objectBehindFlag) {
          objectBehindFlag = true;
          publishStatus("Object Behind", rearDist);
          lcd.clear(); lcd.print("REAR OBSTACLE!"); lcd.setCursor(0,1); lcd.print(rearDist); lcd.print(" cm");
        }
      } else if (objectBehindFlag) {
        objectBehindFlag = false;
        publishStatus("All Clear", rearDist);
        lcd.clear(); lcd.print("Mode: MANUAL");
      }
    }
    
    // Evaluate Gas Detection
    // Note: Most MQ sensor modules output LOW when gas/smoke is detected
    int gasState = digitalRead(GAS_SENSOR_PIN); 
    if (gasState == LOW) { 
      if (!gasAlertFlag) {
        gasAlertFlag = true;
        digitalWrite(BUZZER_PIN, HIGH); // Sound the alarm!
        publishStatus("GAS LEAK DETECTED", frontDist);
        lcd.clear(); lcd.print("HAZARD: GAS!"); lcd.setCursor(0,1); lcd.print("Evacuate Area");
      }
    } else if (gasAlertFlag) {
      gasAlertFlag = false;
      digitalWrite(BUZZER_PIN, LOW); // Turn off the alarm
      publishStatus("All Clear", frontDist);
      lcd.clear(); lcd.print(currentState == STATE_AUTO ? "Mode: AUTO" : "Mode: MANUAL");
    }
  }

  // 2. Motor Execution Logic (Safety Overrides applied here)
  if (currentState == STATE_AUTO) {
    if (obstacleAheadFlag) {
      stopMotors(); // Halt until front clears
    } else {
      runLineFollowing(); // Safe to proceed
    }
  } 
  else if (currentState == STATE_MANUAL) {
    if (currentManualCmd == "FORWARD" && obstacleAheadFlag) {
      stopMotors(); // Prevent crashing forward
    } 
    else if (currentManualCmd == "REVERSE" && objectBehindFlag) {
      stopMotors(); // Prevent crashing backward
    } 
    else {
      // Execute commanded direction
      if (currentManualCmd == "FORWARD") driveMotors(200, 200);
      else if (currentManualCmd == "REVERSE") driveMotors(-200, -200);
      else if (currentManualCmd == "LEFT") driveMotors(-150, 150);
      else if (currentManualCmd == "RIGHT") driveMotors(150, -150);
      else stopMotors();
    }
  }
}

// Helper to send JSON updates to the Pi
void publishStatus(String alert, float dist) {
  String modeStr = (currentState == STATE_AUTO) ? "AUTO" : "MANUAL";
  String payload = "{\"mode\":\"" + modeStr + "\", \"alert\":\"" + alert + "\", \"distance\":" + String(dist) + "}";
  client.publish(topic_status, payload.c_str());
}

// Non-blocking distance calculation (Timeout at 20ms to prevent loop freezing)
float getDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  long duration = pulseIn(echoPin, HIGH, 20000); // 20,000us timeout (~3.4 meters max)
  if (duration == 0) return 999.0;
  return (duration * 0.0343) / 2;
}

void runLineFollowing() {
  int leftIR = digitalRead(IR_LEFT_PIN);
  int rightIR = digitalRead(IR_RIGHT_PIN);

  if (leftIR == 0 && rightIR == 0) driveMotors(180, 180);
  else if (leftIR == 1 && rightIR == 0) driveMotors(60, 180);
  else if (leftIR == 0 && rightIR == 1) driveMotors(180, 60);
  else stopMotors();
}

void mqttCallback(char* topic, byte* message, unsigned int length) {
  String msg = "";
  for (int i = 0; i < length; i++) msg += (char)message[i];

  if (String(topic) == topic_mode) {
    if (msg == "MANUAL") { currentState = STATE_MANUAL; currentManualCmd = "STOP"; stopMotors(); }
    else if (msg == "AUTO") { currentState = STATE_AUTO; publishStatus("All Clear", 0.0); }
  }

  if (currentState == STATE_MANUAL && String(topic) == topic_control) {
    currentManualCmd = msg;
  }
}

void driveMotors(int leftSpeed, int rightSpeed) {
  digitalWrite(MOTOR_L_IN1, leftSpeed >= 0 ? HIGH : LOW);
  digitalWrite(MOTOR_L_IN2, leftSpeed >= 0 ? LOW : HIGH);
  digitalWrite(MOTOR_R_IN3, rightSpeed >= 0 ? HIGH : LOW);
  digitalWrite(MOTOR_R_IN4, rightSpeed >= 0 ? LOW : HIGH);
  analogWrite(MOTOR_L_PWM, abs(leftSpeed));
  analogWrite(MOTOR_R_PWM, abs(rightSpeed));
}

void stopMotors() {
  analogWrite(MOTOR_L_PWM, 0); analogWrite(MOTOR_R_PWM, 0);
}

void setupWifi() {
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) delay(500);
}

void reconnectMqtt() {
  while (!client.connected()) {
    String clientId = "AGV-ESP32-" + String(random(0, 0xffff), HEX);
    if (client.connect(clientId.c_str())) {
      client.subscribe(topic_control);
      client.subscribe(topic_mode);
    } else delay(2000);
  }
}
