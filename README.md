# Maze Solver

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)

Interactive maze generation, solving, and visualization with support for loading mazes from images.

## Features

- **3 Pathfinding Algorithms**: DFS, Bidirectional DFS, BFS (shortest path)
- **Image Maze Loading**: Import PNG/JPG/BMP mazes with auto-preprocessing
- **Interactive Visualization**: Real-time pygame UI with 100 FPS target
- **Zoom & Pan**: Mouse wheel zoom, middle/right-click drag pan
- **Crop Mode**: Select region of interest from photos (photo-editor style)
- **Flexible Start/End**: Click, drag, or auto-detect border openings

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

## Controls

### Navigation

| Key | Action |
|-----|--------|
| `SPACE` | Pause/Resume solving (or confirm selection) |
| `↑` / `↓` | Speed up / Slow down animation |
| `S` | Single step (when paused) |
| `V` | Toggle visited cells overlay |

### Algorithm

| Key | Action |
|-----|--------|
| `1` | DFS (fast, any path) |
| `2` | Bidirectional DFS (~2x faster) |
| `3` | BFS (guaranteed shortest) |

### View (Grid Mode)

| Key | Action |
|-----|--------|
| Mouse Wheel | Zoom in/out |
| MMB / RMB Drag | Pan |
| `0` | Reset zoom & pan |
| `Home` | Center view |

### Image Mode

| Key | Action |
|-----|--------|
| `I` | Load maze image (PNG/JPG/BMP) |
| `TAB` | Toggle between original image & grid view |
| Click | Set start point (1st), end point (2nd) |
| Drag | Select start→end in one motion |
| `C` | Enter crop mode (original view only) |
| `SPACE` | Confirm crop / Confirm selection & solve |
| `ESC` | Cancel crop / Exit |
| `Ctrl+I` | Invert maze colors (white paths ↔ black walls) |
| `S` | Save solution as PNG |

### General

| Key | Action |
|-----|--------|
| `R` | New random maze (or back to generated from image mode) |
| `F` / `F11` | Toggle fullscreen |
| `ESC` / `Q` / `X` | Quit |

## Image Maze Workflow

1. **Load Image** — Press `I`, select maze image (photo of paper maze, screenshot, etc.)
2. **Select Region (Optional)** — Press `C` to enter crop mode, drag rectangle, press `SPACE` to confirm
3. **Set Start/End** —
   - *Original view*: Click start, click end — or drag from start to end
   - *Grid view* (`TAB`): Click/drag on downsampled grid
   - *Auto*: Border openings auto-detected as suggestions
4. **Solve** — Press `SPACE` to run selected algorithm
5. **Save** — Press `S` to export solution image

## Algorithms

| Algorithm | Type | Path Guarantee | Time Complexity | Best For |
|-----------|------|----------------|-----------------|----------|
| DFS | Depth-First | Any path | O(V+E) | Speed, simple mazes |
| Bidirectional DFS | Bi-Directional | Any path | O(V+E) ~2x faster | Large mazes |
| BFS | Breadth-First | **Shortest** | O(V+E) | Optimal path needed |

## Configuration (`config.py`)

| Category | Key Settings |
|----------|--------------|
| **Maze** | `MAZE_WIDTH`, `MAZE_HEIGHT`, `MAZE_COMPLEXITY` (0.0=perfect) |
| **Visualization** | `START_FULLSCREEN`, `UI_HEIGHT`, `FPS`, `CELL_SIZE_MIN` |
| **Solver** | `DEFAULT_ALGORITHM` (0/1/2), `INITIAL_DELAY_MS`, `AUTO_STEP`, `SHOW_VISITED` |
| **Colors** | `COLORS` dict (generated), `IMAGE_COLORS` dict (image mode) |
| **Image** | `IMAGE_MAX_DIM` (downsample limit), `INVERT_MAZE_COLORS` |

## Project Structure

```
.
├── main.py              # Entry point (python main.py)
├── visualize.py         # Pygame visualization & UI (940 lines)
├── maze_solver.py       # Algorithms: DFS, Bi-DFS, BFS + generators + benchmark
├── image_maze.py        # Image → maze pipeline (OpenCV + PIL)
├── config.py            # All tunable settings
├── requirements.txt     # Dependencies
├── .gitignore           # Git ignores
└── README.md            # This file
```

## Development

Run benchmarks:

```bash
python maze_solver.py
```
