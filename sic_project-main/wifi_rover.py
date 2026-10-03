import subprocess
import time

SSID = "ESP32_Rover"
PASSWORD = "123"   # Change if your ESP32 password is different

def run(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip()

print("Disconnecting from current Wi-Fi...")
run("nmcli device disconnect wlan0")

time.sleep(2)

print("Turning Wi-Fi ON...")
run("nmcli radio wifi on")

print("Scanning for ESP32_Rover...")
run("nmcli device wifi rescan")
time.sleep(3)

stdout, _ = run("nmcli -t -f SSID device wifi list")

if SSID in stdout.splitlines():
    print("ESP32_Rover found. Connecting...")

    out, err = run(
        f'nmcli device wifi connect "{SSID}" password "{PASSWORD}"'
    )

    print(out)
    if err:
        print(err)
else:
    print("ESP32_Rover not found.")
