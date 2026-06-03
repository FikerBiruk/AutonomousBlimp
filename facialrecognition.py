"""
facialrecognition.py

Runs on your laptop. Receives frames from a Raspberry Pi Zero 2 W over TCP,
performs face detection/recognition locally, and displays the video.

Requirements:
    pip install opencv-python face_recognition numpy

Before running:
1. Put known face images in a folder named "known_faces".
   Example:
       known_faces/alice.jpg
       known_faces/bob.jpg

2. Start a frame-sending client on the Pi that connects to this laptop.
3. Run:
       python facialrecognition.py
"""

import os
import cv2
import pickle
import socket
import struct
import face_recognition

HOST = "0.0.0.0"
PORT = 9999

known_encodings = []
known_names = []

if os.path.isdir("known_faces"):
    for filename in os.listdir("known_faces"):
        path = os.path.join("known_faces", filename)

        try:
            image = face_recognition.load_image_file(path)
            encodings = face_recognition.face_encodings(image)

            if encodings:
                known_encodings.append(encodings[0])
                known_names.append(os.path.splitext(filename)[0])
                print(f"Loaded: {filename}")
        except Exception as e:
            print(f"Failed to load {filename}: {e}")

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(1)

print(f"Waiting for Pi connection on {HOST}:{PORT} ...")

conn, addr = server.accept()
print(f"Connected from {addr}")

payload_size = struct.calcsize("Q")
data = b""

while True:
    while len(data) < payload_size:
        packet = conn.recv(4096)
        if not packet:
            raise ConnectionError("Connection lost")
        data += packet

    packed_size = data[:payload_size]
    data = data[payload_size:]
    frame_size = struct.unpack("Q", packed_size)[0]

    while len(data) < frame_size:
        packet = conn.recv(4096)
        if not packet:
            raise ConnectionError("Connection lost")
        data += packet

    frame_data = data[:frame_size]
    data = data[frame_size:]

    frame = pickle.loads(frame_data)

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb)
    face_encodings = face_recognition.face_encodings(
        rgb,
        face_locations
    )

    for (top, right, bottom, left), face_encoding in zip(
        face_locations,
        face_encodings
    ):
        name = "Unknown"

        if known_encodings:
            matches = face_recognition.compare_faces(
                known_encodings,
                face_encoding
            )

            if True in matches:
                name = known_names[matches.index(True)]

        cv2.rectangle(
            frame,
            (left, top),
            (right, bottom),
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            name,
            (left, top - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2
        )

    cv2.imshow("Facial Recognition", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

conn.close()
server.close()
cv2.destroyAllWindows()
