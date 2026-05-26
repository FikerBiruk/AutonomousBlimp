"""
need to INSTALL these stuff for it to work.

sudo apt-get update
sudo apt-get install -y python3-opencv python3-pip
pip3 install pupil-apriltags numpy

"""

import cv2
import numpy as np
from pupil_apriltags import Detector
import time
from typing import List, Tuple, Dict

class AprilTagDetector:
    def __init__(self, camera_id: int = 0, tag_size: float = 0.05):

        # apriltag detection
        self.detector = Detector(
            families="tag36h11",
            nthreads=2, 
            quad_decimate=2.0, 
            quad_sigma=0.0,
            refine_edges=1,
            decode_sharpening=0.25,
            debug=0
        )
        self.tag_size = tag_size
        self.camera = cv2.VideoCapture(camera_id)
        self.setup_camera()
        
    def setup_camera(self):
        """Configure camera for optimal performance on Pi Zero 2W"""

        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1) 
        
    def detect_tags(self, frame) -> List[Dict]:
        """
        Detect April tags in a frame.
        
        Args:
            frame: Input image frame
            
        Returns:
            List of detected tags with their properties
        """

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect tags
        detections = self.detector.detect(gray, estimate_tag_pose=True, 
                                         camera_params=[320, 240, 320, 240],
                                         tag_size=self.tag_size)
        
        tags_info = []
        for detection in detections:
            tag_info = {
                'id': detection.tag_id,
                'center': (detection.center[0], detection.center[1]),
                'corners': detection.corners,
                'pose_R': detection.pose_R,  # Rotation matrix
                'pose_t': detection.pose_t,  # Translation vector
                'pose_err': detection.pose_err  # Pose estimation error
            }
            tags_info.append(tag_info)
            
        return tags_info
    
    def draw_detections(self, frame, tags_info) -> np.ndarray:
        """
        Draw detected tags on the frame.
        
        Args:
            frame: Input image frame
            tags_info: List of detected tags
            
        Returns:
            Annotated frame
        """
        for tag in tags_info:
            # Draw corners
            corners = tag['corners'].astype(int)
            cv2.polylines(frame, [corners], True, (0, 255, 0), 2)
            
            # Draw center
            center = tag['center']
            cv2.circle(frame, (int(center[0]), int(center[1])), 5, (0, 0, 255), -1)
            
            # Draw tag ID
            cv2.putText(frame, f"ID: {tag['id']}", 
                       (int(center[0]) - 20, int(center[1]) - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
        return frame
    
    def run(self, display: bool = True):
        """
        Run continuous April tag detection.
        
        Args:
            display: Whether to display video with detections
        """
        print("Starting April tag detection. Press 'q' to quit.")
        
        try:
            frame_count = 0
            start_time = time.time()
            
            while True:
                ret, frame = self.camera.read()
                if not ret:
                    print("Failed to read frame")
                    break
                
                # Detect tags
                tags_info = self.detect_tags(frame)
                
                # Draw detections
                if display:
                    frame = self.draw_detections(frame, tags_info)
                    cv2.imshow('April Tag Detection', frame)
                
                # Print detection info
                if tags_info:
                    print(f"Frame {frame_count}: Detected {len(tags_info)} tags")
                    for tag in tags_info:
                        print(f"  Tag ID: {tag['id']}, Center: {tag['center']}")
                
                frame_count += 1
                
                # Calculate FPS every 30 frames
                if frame_count % 30 == 0:
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed
                    print(f"FPS: {fps:.2f}")
                
                # Exit on 'q' key
                if display and cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Release resources"""
        self.camera.release()
        cv2.destroyAllWindows()
        print("April tag detection stopped")


if __name__ == "__main__":
    detector = AprilTagDetector(camera_id=0, tag_size=0.05)
    detector.run(display=True)
