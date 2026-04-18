"""
face_mesh.py
Thin wrapper around MediaPipe FaceMesh.
Runs face detection and returns normalized landmarks.

Optimisation: processes every Nth frame (default: 2) to halve CPU load.
MediaPipe's model runs at ~30fps; we only need 15fps for smooth control.
"""
import cv2
import mediapipe as mp
import numpy as np
from typing import Optional

class FaceMesh:
    def __init__(self, process_every_n: int = 2):
        """
        process_every_n: skip frames to reduce CPU usage
            1 = process every frame (30fps on most webcams)
            2 = process every other frame (15fps) ← default, recommended
        """
        self._mp = mp.solutions.face_mesh
        self._mesh = self._mp.FaceMesh(
            max_num_faces       = 1,           # we only track one user
            refine_landmarks    = True,        # enables iris landmarks (468-477)
            min_detection_confidence = 0.5,
            min_tracking_confidence  = 0.5,
        )
        self._draw = mp.solutions.drawing_utils
        self._spec = self._mp.FACEMESH_TESSELATION

        self._process_every = process_every_n
        self._frame_idx     = 0
        self._last_landmarks: Optional[list] = None

    def process(self, bgr_frame: np.ndarray) -> tuple[Optional[list], np.ndarray]:
        """
        Process one webcam frame.

        Returns:
            landmarks: list of 478 [x, y, z] points, or None if no face found
            annotated: BGR frame with face mesh overlay drawn on it
        """
        self._frame_idx += 1

        # Skip frames for performance
        if self._frame_idx % self._process_every != 0:
            return self._last_landmarks, bgr_frame

        # MediaPipe expects RGB
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self._mesh.process(rgb)

        annotated = bgr_frame.copy()

        if not results.multi_face_landmarks:
            self._last_landmarks = None
            return None, annotated

        face = results.multi_face_landmarks[0]

        # Draw mesh overlay on annotated frame
        self._draw.draw_landmarks(
            image            = annotated,
            landmark_list    = face,
            connections      = self._mp.FACEMESH_TESSELATION,
            landmark_drawing_spec = None,
            connection_drawing_spec = self._draw.DrawingSpec(
                color=(0, 200, 120), thickness=1, circle_radius=0)
        )

        # Draw iris circles
        h, w = bgr_frame.shape[:2]
        for idx in [468, 469, 470, 471, 472,   # left iris
                    473, 474, 475, 476, 477]:   # right iris
            if idx < len(face.landmark):
                lm = face.landmark[idx]
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(annotated, (cx, cy), 3, (0, 120, 255), -1)

        # Convert landmarks to flat list of [x, y, z]
        landmarks = [[lm.x, lm.y, lm.z] for lm in face.landmark]
        self._last_landmarks = landmarks

        return landmarks, annotated

    def close(self):
        self._mesh.close()
