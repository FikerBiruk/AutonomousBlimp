"""
pisender.py

Runs on a Raspberry Pi Zero 2 W with Camera Module 3.
Captures frames using Picamera2 and sends them to a laptop
running facialrecognition.py.

Install:
    sudo apt update
    sudo apt install python3-picamera2
    pip install opencv-python numpy

Edit LAPTOP_IP below before running.

Run:
    python3 pisender.py
"""

from picamera2 import Picamera2
import socket
import pickle
import struct
import cv2
import time

LAPTOP_IP = "172.20.10.13"   ##########################
PORT = 9999

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

print(f"Connecting to {LAPTOP_IP}:{PORT}...")

while True:
    try:
        client.connect((LAPTOP_IP, PORT))
        break
    except Exception:
        print("Waiting for laptop server...")
        time.sleep(2)

picam2 = Picamera2()

config = picam2.create_preview_configuration(
    main={"size": (640, 480)}
)

picam2.configure(config)
picam2.start()

print("Camera started. Streaming frames...")

try:
    while True:
        frame = picam2.capture_array()

        if frame.shape[2] == 4:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        data = pickle.dumps(frame, protocol=pickle.HIGHEST_PROTOCOL)
        message = struct.pack("Q", len(data)) + data

        client.sendall(message)

except KeyboardInterrupt:
    print("Stopping...")

finally:
    client.close()
    picam2.stop()
