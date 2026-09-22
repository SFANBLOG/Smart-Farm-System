"""视频上传自动抽帧：OpenCV 可用则抽帧，未安装则优雅跳过。"""
from __future__ import annotations
import os

try:
    import cv2
    HAS_CV2 = True
except Exception:
    HAS_CV2 = False


def extract_frames(video_path: str, out_dir: str, max_frames: int = 8) -> list[str]:
    """从视频均匀抽取最多 max_frames 帧，返回图片路径列表。OpenCV 缺失时返回空列表。"""
    if not HAS_CV2 or not os.path.exists(video_path):
        return []
    os.makedirs(out_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if total <= 0:
        cap.release()
        return []
    step = max(1, total // max_frames)
    saved = []
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0 and len(saved) < max_frames:
            p = os.path.join(out_dir, f"frame_{idx:05d}.jpg")
            cv2.imwrite(p, frame)
            saved.append(p)
        idx += 1
    cap.release()
    return saved
