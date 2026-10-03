import time
import serial
import threading
import queue
import numpy as np

# Packet constants matching ESP32 firmware
SYNC_BYTE_1 = 0xA5
SYNC_BYTE_2 = 0x5A
PACKET_SIZE = 5

class SerialEMGStreamer:
    """
    Manages a thread-safe background serial receiver that continuously reads
    and parses binary packets streamed from the ESP32 dev module.
    
    Includes an integrated 'Simulation Mode' to generate realistic, real-time 
    analog samples when no physical ESP32 hardware is connected.
    """
    def __init__(self, port=None, baudrate=115200, sample_queue=None):
        self.port = port
        self.baudrate = baudrate
        self.sample_queue = sample_queue if sample_queue is not None else queue.Queue(maxsize=5000)
        
        self.running = False
        self.thread = None
        self.ser = None
        
        # Simulation parameters
        self.simulation_mode = (port is None or port.lower() == "simulation")
        self.sim_is_als = False
        self.sim_muscle = "Masseter"
        
    def start(self):
        """Starts the background reading thread."""
        if self.running:
            return
        
        self.running = True
        if self.simulation_mode:
            self.thread = threading.Thread(target=self._run_simulation, daemon=True)
            print("Starting SerialEMGStreamer in DEMO SIMULATION MODE...")
        else:
            self.thread = threading.Thread(target=self._run_serial, daemon=True)
            print(f"Starting SerialEMGStreamer on port {self.port} at {self.baudrate} baud...")
            
        self.thread.start()
        
    def stop(self):
        """Stops the background reading thread and closes serial connections."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
            
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None
        print("SerialEMGStreamer stopped.")
        
    def _run_serial(self):
        """
        Main worker thread for serial communication. Uses binary packet alignment.
        """
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1.0)
            self.ser.reset_input_buffer()
        except Exception as e:
            print(f"Serial Connection Error on {self.port}: {e}")
            # Fall back to simulation if hardware connection fails
            print("Switching automatically to DEMO SIMULATION MODE...")
            self.simulation_mode = True
            self._run_simulation()
            return

        # Packet parser state machine
        buffer = bytearray()
        
        while self.running:
            try:
                if self.ser.in_waiting > 0:
                    # Read available bytes
                    data = self.ser.read(self.ser.in_waiting)
                    buffer.extend(data)
                    
                    # Parse buffer for packets
                    while len(buffer) >= PACKET_SIZE:
                        # Find the sync pattern
                        sync_idx = -1
                        for i in range(len(buffer) - 1):
                            if buffer[i] == SYNC_BYTE_1 and buffer[i+1] == SYNC_BYTE_2:
                                sync_idx = i
                                break
                                
                        if sync_idx == -1:
                            # Sync pattern not found, discard all but the last byte to maintain alignment window
                            buffer = buffer[-1:]
                            break
                        
                        # Discard bytes before the sync pattern
                        if sync_idx > 0:
                            buffer = buffer[sync_idx:]
                            
                        # Ensure we have a full packet remaining
                        if len(buffer) < PACKET_SIZE:
                            break
                            
                        # Extract 5-byte packet
                        packet = buffer[:PACKET_SIZE]
                        high_byte = packet[2]
                        low_byte = packet[3]
                        checksum = packet[4]
                        
                        # Verify 8-bit checksum
                        calculated_checksum = (SYNC_BYTE_1 + SYNC_BYTE_2 + high_byte + low_byte) & 0xFF
                        
                        if calculated_checksum == checksum:
                            # Valid packet: reconstruct 12-bit value
                            adc_val = (high_byte << 8) | low_byte
                            
                            # Push to thread-safe queue (discard oldest sample if full)
                            try:
                                self.sample_queue.put_nowait(adc_val)
                            except queue.Full:
                                try:
                                    self.sample_queue.get_nowait()
                                    self.sample_queue.put_nowait(adc_val)
                                except Exception:
                                    pass
                            
                            # Slide buffer past the parsed packet
                            buffer = buffer[PACKET_SIZE:]
                        else:
                            # Bad checksum: discard the sync header and slide forward 1 byte
                            buffer = buffer[1:]
                            
            except Exception as e:
                print(f"Error reading serial: {e}")
                time.sleep(0.1)
                
    def _run_simulation(self):
        """
        Main worker thread for biological simulation.
        Generates physiologically realistic sEMG streams on the fly at 1000 Hz.
        """
        # Timing state
        t = 0.0
        dt = 0.001  # 1 ms interval
        
        while self.running:
            # Generate realistic muscle baseline + speech activation wave
            # Speech activation peaks periodically
            mod_cycle = t % 5.0
            
            # Silent speech trigger envelope
            envelope = 0.05
            if 1.0 <= mod_cycle < 1.8 or 2.2 <= mod_cycle < 3.0 or 3.4 <= mod_cycle < 4.2:
                # Active speech burst
                envelope = np.sin(np.pi * (mod_cycle - int(mod_cycle)) / 0.8) ** 2
                envelope = max(0.1, envelope)
                
            # Base high-frequency muscle activation
            # Frequency centered around 100-250 Hz
            freq_comp1 = np.sin(2 * np.pi * 125.0 * t)
            freq_comp2 = np.sin(2 * np.pi * 190.0 * t)
            raw_emg = (freq_comp1 + freq_comp2) * np.random.normal(0, 0.4)
            
            # Scale based on pathology
            if self.sim_is_als:
                # Atrophy reduces standard amplitude
                raw_emg *= 0.35 * envelope
                
                # Add Fasciculations: sharp spastic burst random firings
                if np.random.random() < 0.004:  # Intermittent spikes
                    raw_emg += np.random.uniform(1.2, 2.5) * np.sin(2 * np.pi * 210.0 * t)
                    
                # Model fatiguability
                fatigue_factor = 1.0 - (0.4 * (mod_cycle / 5.0))
                raw_emg *= fatigue_factor
            else:
                raw_emg *= 1.2 * envelope
                fatigue_factor = 1.0 - (0.05 * (mod_cycle / 5.0))
                raw_emg *= fatigue_factor
                
            # Mains noise (50Hz hum)
            mains_noise = 0.15 * np.sin(2 * np.pi * 50.0 * t)
            mains_noise += 0.03 * np.sin(2 * np.pi * 150.0 * t)
            
            # Baseline offset (1850 VDC level on ESP32 ADC)
            adc_val = 1850.0 + (raw_emg + mains_noise) * 450.0
            adc_val = int(np.clip(adc_val, 0, 4095))
            
            # Push simulated sample to queue
            try:
                self.sample_queue.put_nowait(adc_val)
            except queue.Full:
                try:
                    self.sample_queue.get_nowait()
                    self.sample_queue.put_nowait(adc_val)
                except Exception:
                    pass
                    
            # Incremental timer
            t += dt
            
            # Maintain exact 1000 Hz loop rate (1 ms delay)
            time.sleep(0.001)

    def set_simulation_profile(self, is_als=False, muscle_name="Masseter"):
        """Configures the current biological profile of the real-time simulation."""
        self.sim_is_als = is_als
        self.sim_muscle = muscle_name
        label = "ALS Patient" if is_als else "Healthy Control"
        print(f"Simulator configured to stream: {muscle_name} [{label}]")
