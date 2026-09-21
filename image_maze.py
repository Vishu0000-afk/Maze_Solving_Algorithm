import numpy as np
from PIL import Image
from typing import List, Tuple, Optional
import cv2


def crop_image(img: np.ndarray, rect: Tuple[int, int, int, int]) -> np.ndarray:
    """Crop numpy image to rect (x, y, w, h) in pixel coordinates."""
    x, y, w, h = rect
    h_img, w_img = img.shape[:2]
    x = max(0, min(x, w_img - 1))
    y = max(0, min(y, h_img - 1))
    w = max(1, min(w, w_img - x))
    h = max(1, min(h, h_img - y))
    return img[y:y+h, x:x+w]


def load_image(path: str) -> np.ndarray:
    """Load image as grayscale numpy array."""
    img = Image.open(path).convert('L')
    return np.array(img)


def preprocess_maze(img: np.ndarray, invert: bool = False) -> np.ndarray:
    """Clean digital maze: threshold + morphological close."""
    _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if invert:
        binary = 255 - binary
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    return binary


def downsample_to_grid(binary: np.ndarray, max_dim: int = 200) -> np.ndarray:
    """Resize to target grid size using area interpolation."""
    h, w = binary.shape
    scale = min(max_dim / w, max_dim / h, 1.0)
    new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
    resized = cv2.resize(binary, (new_w, new_h), interpolation=cv2.INTER_AREA)
    _, grid = cv2.threshold(resized, 127, 255, cv2.THRESH_BINARY)
    return grid


def grid_to_maze(grid: np.ndarray) -> List[List[int]]:
    """Convert 0/255 grid to 0/1 maze (0=path, 1=wall)."""
    return ((grid == 0).astype(int)).tolist()


def find_border_openings(maze: List[List[int]]) -> List[Tuple[int, int]]:
    """Find path cells on maze borders for start/end suggestions."""
    h, w = len(maze), len(maze[0])
    openings = []
    for x in range(w):
        if maze[0][x] == 0:
            openings.append((x, 0))
        if maze[h - 1][x] == 0:
            openings.append((x, h - 1))
    for y in range(h):
        if maze[y][0] == 0:
            openings.append((0, y))
        if maze[y][w - 1] == 0:
            openings.append((w - 1, y))
    return openings


def load_maze_from_image(path: str, max_dim: int = 200, invert: bool = False, 
                          crop_rect: Optional[Tuple[int, int, int, int]] = None) -> Tuple[List[List[int]], Optional[Tuple[int, int]], Optional[Tuple[int, int]]]:
    """Full pipeline: image -> maze grid + suggested start/end."""
    img = load_image(path)
    if crop_rect:
        img = crop_image(img, crop_rect)
    binary = preprocess_maze(img, invert=invert)
    grid = downsample_to_grid(binary, max_dim)
    maze = grid_to_maze(grid)
    openings = find_border_openings(maze)
    start = openings[0] if openings else None
    end = openings[-1] if len(openings) > 1 else (openings[0] if openings else None)
    return maze, start, end