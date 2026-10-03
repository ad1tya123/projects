/**
 * ESP32 sEMG High-Speed Streamer
 * 
 * This firmware samples an analog input pin connected to the Bioamp Candy EMG amplifier
 * at exactly 1000 Hz (1 ms sampling interval) and streams the raw 12-bit ADC values over
 * USB Serial using a robust, lightweight binary framing protocol.
 * 
 * Hardware Connection:
 * - Bioamp Candy Out -> ESP32 GPIO 36 (VP) or any ADC1 pin (e.g., GPIO 34, 35, 39, 36)
 * - Bioamp Candy VCC -> ESP32 3.3V
 * - Bioamp Candy GND -> ESP32 GND
 */

#define EMG_PIN 36            // Analog Pin (GPIO 36 is ADC1_CH0 / VP on ESP32)
#define SAMPLING_RATE_HZ 1000
#define SAMPLE_INTERVAL_US (1000000 / SAMPLING_RATE_HZ) // 1000 microseconds

// Packet sync bytes
#define SYNC_BYTE_1 0xA5
#define SYNC_BYTE_2 0x5A

unsigned long next_sample_time_us = 0;

void setup() {
  // Set up high-speed Serial communication
  Serial.begin(115200);
  
  // Configure analog input resolution and attenuation
  analogReadResolution(12);           // 12-bit ADC (0 - 4095)
  analogSetPinAttenuation(EMG_PIN, ADC_11db); // 0V to ~3.1V range
  
  pinMode(EMG_PIN, INPUT);
  
  // Wait for serial port to stabilize
  delay(1000);
  
  // Initialize the next sample timing benchmark
  next_sample_time_us = micros();
}

void loop() {
  unsigned long current_time_us = micros();
  
  // Check if it's time to take the next sample
  if ((long)(current_time_us - next_sample_time_us) >= 0) {
    // Schedule next sample exactly 1000 us after the previous scheduled sample
    next_sample_time_us += SAMPLE_INTERVAL_US;
    
    // 1. Read raw EMG ADC value (12-bit)
    uint16_t emg_val = analogRead(EMG_PIN);
    
    // 2. Prepare binary packet
    uint8_t high_byte = (uint8_t)((emg_val >> 8) & 0xFF);
    uint8_t low_byte = (uint8_t)(emg_val & 0xFF);
    
    // Calculate 8-bit checksum
    uint8_t checksum = (SYNC_BYTE_1 + SYNC_BYTE_2 + high_byte + low_byte) & 0xFF;
    
    // 3. Send packet (5 bytes total)
    Serial.write(SYNC_BYTE_1);
    Serial.write(SYNC_BYTE_2);
    Serial.write(high_byte);
    Serial.write(low_byte);
    Serial.write(checksum);
  }
}
