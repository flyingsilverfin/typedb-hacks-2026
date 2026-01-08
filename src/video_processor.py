"""Video processing module for extracting frames from video files."""

import base64
import io
from dataclasses import dataclass
from pathlib import Path

import cv2


@dataclass
class FrameData:
    """Container for extracted frame data."""
    frame_number: int
    timestamp_sec: float
    image_base64: str
    width: int
    height: int


class VideoProcessor:
    """Extract frames from video files for vision analysis."""

    def __init__(self, frames_per_second: float = 1.0, max_frames: int = 10):
        """
        Initialize video processor.

        Args:
            frames_per_second: How many frames to extract per second of video
            max_frames: Maximum number of frames to extract
        """
        self.frames_per_second = frames_per_second
        self.max_frames = max_frames

    def extract_frames(self, video_path: str | Path) -> list[FrameData]:
        """
        Extract frames from a video file.

        Args:
            video_path: Path to the video file

        Returns:
            List of FrameData objects containing base64-encoded frames

        Raises:
            FileNotFoundError: If video file doesn't exist
            ValueError: If video cannot be opened or processed
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration_sec = total_frames / fps if fps > 0 else 0

            # Calculate frame interval
            frame_interval = int(fps / self.frames_per_second) if self.frames_per_second > 0 else int(fps)
            frame_interval = max(1, frame_interval)

            frames: list[FrameData] = []
            frame_number = 0

            while len(frames) < self.max_frames:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                ret, frame = cap.read()

                if not ret:
                    break

                # Convert frame to base64 JPEG
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                image_base64 = base64.standard_b64encode(buffer).decode('utf-8')

                timestamp_sec = frame_number / fps if fps > 0 else 0

                frames.append(FrameData(
                    frame_number=frame_number,
                    timestamp_sec=timestamp_sec,
                    image_base64=image_base64,
                    width=frame.shape[1],
                    height=frame.shape[0]
                ))

                frame_number += frame_interval

                if frame_number >= total_frames:
                    break

            return frames

        finally:
            cap.release()

    def extract_single_frame(self, video_path: str | Path, timestamp_sec: float = 0) -> FrameData | None:
        """
        Extract a single frame at a specific timestamp.

        Args:
            video_path: Path to the video file
            timestamp_sec: Timestamp in seconds to extract frame from

        Returns:
            FrameData object or None if extraction fails
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_number = int(timestamp_sec * fps)

            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()

            if not ret:
                return None

            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            image_base64 = base64.standard_b64encode(buffer).decode('utf-8')

            return FrameData(
                frame_number=frame_number,
                timestamp_sec=timestamp_sec,
                image_base64=image_base64,
                width=frame.shape[1],
                height=frame.shape[0]
            )

        finally:
            cap.release()

    @staticmethod
    def get_video_info(video_path: str | Path) -> dict:
        """
        Get metadata about a video file.

        Returns:
            Dictionary with fps, total_frames, duration_sec, width, height
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            return {
                "fps": fps,
                "total_frames": total_frames,
                "duration_sec": total_frames / fps if fps > 0 else 0,
                "width": width,
                "height": height
            }

        finally:
            cap.release()
