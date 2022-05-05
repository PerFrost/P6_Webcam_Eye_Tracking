import math

import cv2 as cv
import numpy as np
from .pupil import Pupil


class Eye(object):
    LEFT_EYE_POINTS = [36, 37, 38, 39, 40, 41]
    RIGHT_EYE_POINTS = [42, 43, 44, 45, 46, 47]

    def __init__(self, original_frame, landmarks, side, calibration):
        self.frame = None
        self.origin = None
        self.center = None
        self.pupil = None
        self.landmark_points = None

        self.analyse(original_frame, landmarks, side, calibration)

    @staticmethod
    def middle_point(p1, p2):
        """
        Computes the middle point between two points.

        Args:
            p1 (dlib.point): First point.
            p2 (dlib.point): Second point.

        Returns:
            The middle point (x,y) between two points.
        """
        x = int((p1.x + p2.x) / 2)
        y = int((p1.y + p2.y) / 2)
        return x, y

    def isolate(self, frame, landmarks, points):
        """
        Isolates an eye to have a frame without other parts of a face.

        Args:
            frame (numpy.ndarray): Frame containing the face.
            landmarks (dlib.full_object_detection): Facial landmarks for the face region.
            points (list): Points of an eye (from the 68 Multi-PIE landmarks).
        """
        region = np.array(
            [(landmarks.part(point).x, landmarks.part(point).y) for point in points]
        )
        region = region.astype(np.int32)
        self.landmark_points = region

        # Apply mask to exclude everything but the eye
        height, width = frame.shape[:2]
        black_frame = np.zeros((height, width), np.uint8)
        mask = np.full((height, width), 255, np.uint8)
        cv.fillPoly(mask, [region], (0, 0, 0))
        eye = cv.bitwise_not(black_frame, frame.copy(), mask=mask)

        # Cropping the eye
        margin = 5
        min_x = np.min(region[:, 0]) - margin
        max_x = np.max(region[:, 0]) + margin
        min_y = np.min(region[:, 1]) - margin
        max_y = np.max(region[:, 1]) + margin

        self.frame = eye[min_y:max_y, min_x:max_x]
        self.origin = (min_x, min_y)

        height, width = self.frame.shape[:2]
        self.center = (width / 2, height / 2)

    def blinking_ratio(self, landmarks, points):
        """
        Calculates a ratio that can indicate whether an eye is closed or not.
        It is the division of the width of the eye by its height.

        Args:
            landmarks (dlib.full_object_detection): Facial landmarks for the face region.
            points (list): Points of an eye (from the 68 Multi-PIE landmarks).

        Returns:
            A computed ratio.
        """
        left = (landmarks.part(points[0]).x, landmarks.part(points[0]).y)
        right = (landmarks.part(points[3]).x, landmarks.part(points[3]).y)
        top = self.middle_point(landmarks.part(points[1]), landmarks.part(points[2]))
        bottom = self.middle_point(landmarks.part(points[5]), landmarks.part(points[4]))

        eye_width = math.hypot((left[0] - right[0]), (left[1] - right[1]))
        eye_height = math.hypot((top[0] - bottom[0]), (top[1] - bottom[1]))

        try:
            ratio = eye_width / eye_height
        except ZeroDivisionError:
            ratio = None

        return ratio

    def analyse(self, original_frame, landmarks, side, calibration):
        """
        Detects and isolates the eye in a new frame. Sends the data to the calibration,
        and initialises Pupil object.

        Args:
            original_frame (numpy.ndarray): Frame passed by the user.
            landmarks (dlib.full_object_detection): Facial landmarks for the face region.
            side: Indicates whether it's the left eye (0) or the right eye (1).
            calibration (calibration.Calibration): Manages the binarisation threshold value.
        """
        if side == 0:
            points = self.LEFT_EYE_POINTS
        elif side == 1:
            points = self.RIGHT_EYE_POINTS
        else:
            return

        self.blinking = self.blinking_ratio(landmarks, points)
        self.isolate(original_frame, landmarks, points)

        if not calibration.is_complete():
            calibration.evaluate(self.frame, side)

        threshold = calibration.threshold(side)
        self.pupil = Pupil(self.frame, threshold)
