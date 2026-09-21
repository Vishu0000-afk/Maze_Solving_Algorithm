# Maze settings
MAZE_HEIGHT = 50
MAZE_WIDTH = 50
MAZE_COMPLEXITY = 1.0  # 0.0 = perfect maze

# Visualization settings
START_FULLSCREEN = True
UI_HEIGHT = 100
MAZE_PADDING = 20
CELL_SIZE_MIN = 2
FPS = 100

# Solver settings
DEFAULT_ALGORITHM = 2  # 0=DFS, 1=Bi-DFS, 2=BFS
INITIAL_DELAY_MS = 0
AUTO_STEP = True
SHOW_VISITED = True

# Colors (RGB)
COLORS = {
    'bg': (18, 18, 24),
    'wall': (30, 30, 40),
    'path': (45, 45, 60),
    'visited': (66, 135, 245),
    'visited_dim': (40, 80, 160),
    'current': (255, 85, 85),
    'current_bwd': (255, 170, 85),
    'solution': (80, 250, 120),
    'start': (255, 220, 80),
    'end': (255, 100, 150),
    'text': (220, 220, 230),
    'text_dim': (140, 140, 160),
    'ui_bg': (24, 24, 32),
    'button': (55, 55, 75),
    'button_hover': (75, 75, 100),
    'button_active': (90, 180, 90),
}

# Image maze settings
IMAGE_MAX_DIM = 200
INVERT_MAZE_COLORS = True  # True if your images have white paths, black walls

# Image mode color scheme (distinct from generated)
IMAGE_COLORS = {
    'bg': (25, 25, 35),
    'wall': (20, 20, 30),
    'path': (50, 50, 70),
    'visited': (100, 200, 255),
    'visited_dim': (60, 120, 180),
    'current': (255, 100, 100),
    'current_bwd': (255, 180, 100),
    'solution': (100, 255, 150),
    'start': (255, 240, 100),
    'end': (255, 120, 180),
    'text': (230, 230, 240),
    'text_dim': (150, 150, 170),
    'ui_bg': (30, 30, 40),
    'button': (60, 60, 80),
    'button_hover': (80, 80, 110),
    'button_active': (100, 200, 100),
    'selection': (255, 255, 100),
}