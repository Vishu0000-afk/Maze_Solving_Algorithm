import pygame
import sys
import time
import tkinter as tk
from tkinter import filedialog
from typing import Tuple
from maze_solver import (
    generate_maze,
    dfs_generator,
    bidirectional_dfs_generator,
    bfs_generator,
    find_furthest_cell,
    Point,
    Path,
    SolverState,
)
from image_maze import load_maze_from_image
from config import (
    MAZE_WIDTH, MAZE_HEIGHT, MAZE_COMPLEXITY,
    START_FULLSCREEN, UI_HEIGHT, MAZE_PADDING,
    CELL_SIZE_MIN, FPS,
    DEFAULT_ALGORITHM, INITIAL_DELAY_MS, AUTO_STEP, SHOW_VISITED,
    COLORS, IMAGE_MAX_DIM, IMAGE_COLORS, INVERT_MAZE_COLORS,
)

MAZE_PADDING = 20
UI_HEIGHT = 100

ALGORITHMS = [
    ('1', 'DFS', dfs_generator, COLORS['visited']),
    ('2', 'Bi-DFS', bidirectional_dfs_generator, COLORS['visited']),
    ('3', 'BFS', bfs_generator, COLORS['visited']),
]


class MazeVisualizer:
    def __init__(self, maze_width: int = MAZE_WIDTH, maze_height: int = MAZE_HEIGHT):
        pygame.init()
        flags = pygame.FULLSCREEN if START_FULLSCREEN else 0
        self.screen = pygame.display.set_mode((0, 0), flags)
        pygame.display.set_caption('Maze Solver Visualization')
        info = pygame.display.Info()
        self.screen_width = info.current_w
        self.screen_height = info.current_h
        
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('monospace', 14)
        self.font_big = pygame.font.SysFont('monospace', 18, bold=True)
        self.font_small = pygame.font.SysFont('monospace', 12)
        
        self.maze_width = maze_width
        self.maze_height = maze_height
        self.base_cell_size = 0
        self.maze_offset_x = 0
        self.maze_offset_y = 0
        
        self.maze = []
        self.start = (0, 1)
        self.end = (maze_width - 1, maze_height - 2)
        
        self.solver_gen = None
        self.solver_name = ''
        self.visited = set()
        self.current_pos = (0, 0)
        self.solution_path = []
        self.done = False
        
        self.paused = False
        self.step_delay = INITIAL_DELAY_MS
        self.last_step_time = 0
        self.auto_step = AUTO_STEP
        self.show_visited = SHOW_VISITED
        
        self.algorithm_idx = DEFAULT_ALGORITHM
        self.steps_per_frame = 1
        
        self.solve_start_time = 0
        self.solve_duration_ms = 0
        
        # Zoom/pan state
        self.zoom_level = 1.0
        self.min_zoom = 0.25
        self.max_zoom = 10.0
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        self.dragging = False
        self.drag_start = None
        self.drag_pan_start = (0, 0)
        
        # Image mode state
        self.mode = 'generated'  # 'generated' | 'image_selecting_original' | 'image_selecting' | 'image_cropping' | 'image_solving'
        self.image_surface = None           # Downsampled grid surface
        self.original_image = None          # Full-res original image
        self.original_size = None           # (w, h) of original
        self.image_display_rect = None      # Rect where original image is drawn
        self.click_points = []
        self.selecting_start = True
        self.active_colors = COLORS
        self.invert_maze_colors = INVERT_MAZE_COLORS  # Runtime toggle for maze color inversion
        self.image_path = None              # Store path for reloading
        
        # Drag-to-select state
        self.drag_selecting = False
        self.drag_start_pos = None
        self.drag_end_pos = None
        self.drag_start_maze = None
        self.drag_end_maze = None
        
        # Crop mode state
        self.crop_rect = None           # (x, y, w, h) in original image pixel coords
        self.crop_drag_start = None     # Screen coords (x, y)
        self.crop_drag_end = None       # Screen coords (x, y)
        self.crop_dragging = False      # True during drag
        
        self.generate_new_maze()
    
    @property
    def cell_size(self):
        return max(1, int(self.base_cell_size * self.zoom_level))
    
    def generate_new_maze(self):
        self.mode = 'generated'
        self.active_colors = COLORS
        self.maze_width = MAZE_WIDTH
        self.maze_height = MAZE_HEIGHT
        self.maze = generate_maze(self.maze_width, self.maze_height, MAZE_COMPLEXITY)
        self.start = (0, 1)
        self.end = find_furthest_cell(self.maze, self.start)
        self.recalculate_layout()
        self.restart_solver()
    
    def recalculate_layout(self):
        """Recalc cell size/offsets for current maze dimensions."""
        maze_area_w = self.screen_width - 2 * MAZE_PADDING
        maze_area_h = self.screen_height - MAZE_PADDING * 2 - UI_HEIGHT
        self.base_cell_size = max(CELL_SIZE_MIN, min(
            maze_area_w // self.maze_width, 
            maze_area_h // self.maze_height
        ))
        maze_w_px = self.maze_width * self.base_cell_size
        maze_h_px = self.maze_height * self.base_cell_size
        self.maze_offset_x = (self.screen_width - maze_w_px) // 2
        self.maze_offset_y = MAZE_PADDING
        self.reset_zoom_pan()
    
    def restart_solver(self):
        algo_key, algo_name, algo_func, _ = ALGORITHMS[self.algorithm_idx]
        self.solver_name = algo_name
        self.solver_gen = algo_func(self.maze, self.start, self.end)
        self.visited = set()
        self.current_pos = self.start
        self.solution_path = []
        self.done = False
        self.paused = False
        self.last_step_time = pygame.time.get_ticks()
        self.solve_start_time = pygame.time.get_ticks()
        self.solve_duration_ms = 0
    
    def load_image_maze(self, path: str, invert: bool = None, crop_rect: Tuple[int, int, int, int] = None):
        """Load and preprocess image, enter selection mode."""
        if invert is None:
            invert = self.invert_maze_colors
        try:
            maze, suggested_start, suggested_end = load_maze_from_image(path, IMAGE_MAX_DIM, invert=invert, crop_rect=crop_rect)
            self.mode = 'image_selecting_original'
            self.active_colors = IMAGE_COLORS
            self.maze = maze
            self.maze_width = len(maze[0])
            self.maze_height = len(maze)
            self.click_points = []
            self.selecting_start = True
            self.drag_selecting = False
            self.crop_rect = None
            self.crop_dragging = False
            self.image_path = path  # Store for reload
            
            # Store original image for display (full resolution)
            self.original_image = pygame.image.load(path).convert()
            self.original_size = self.original_image.get_size()
            
            # Store downsampled grid surface for later grid view
            self.image_surface = pygame.image.load(path).convert()
            
            # Set suggested points if available (on the grid)
            if suggested_start and suggested_end:
                self.start = suggested_start
                self.end = suggested_end
                self.click_points = [suggested_start, suggested_end]
                self.selecting_start = False
            
            self.recalculate_layout()
            self.restart_solver()
            
        except Exception as e:
            print(f"Failed to load maze image: {e}")
            self.mode = 'generated'
            self.active_colors = COLORS
    
    def reload_image_maze(self):
        """Re-process current image with updated invert setting."""
        if self.image_path:
            self.load_image_maze(self.image_path, invert=self.invert_maze_colors)
    
    def screen_to_maze(self, screen_pos: tuple) -> tuple:
        """Convert screen coordinates to maze grid coordinates (for grid view)."""
        cs = self.cell_size
        ox = self.maze_offset_x + self.pan_offset_x
        oy = self.maze_offset_y + self.pan_offset_y
        mx = int((screen_pos[0] - ox) / cs)
        my = int((screen_pos[1] - oy) / cs)
        return max(0, min(self.maze_width - 1, mx)), max(0, min(self.maze_height - 1, my))
    
    def original_to_maze(self, screen_pos: tuple) -> tuple:
        """Convert screen coordinates on original image display to maze grid coordinates."""
        if not self.image_display_rect or not self.original_size:
            return None
        rel_x = (screen_pos[0] - self.image_display_rect.x) / self.image_display_rect.w
        rel_y = (screen_pos[1] - self.image_display_rect.y) / self.image_display_rect.h
        if 0 <= rel_x <= 1 and 0 <= rel_y <= 1:
            mx = int(rel_x * self.maze_width)
            my = int(rel_y * self.maze_height)
            return max(0, min(self.maze_width - 1, mx)), max(0, min(self.maze_height - 1, my))
        return None
    
    def screen_to_original(self, screen_pos: tuple) -> tuple:
        """Convert screen coordinates on original image display to original image pixel coordinates."""
        if not self.image_display_rect or not self.original_size:
            return None
        rel_x = (screen_pos[0] - self.image_display_rect.x) / self.image_display_rect.w
        rel_y = (screen_pos[1] - self.image_display_rect.y) / self.image_display_rect.h
        if 0 <= rel_x <= 1 and 0 <= rel_y <= 1:
            ox = int(rel_x * self.original_size[0])
            oy = int(rel_y * self.original_size[1])
            return max(0, min(self.original_size[0] - 1, ox)), max(0, min(self.original_size[1] - 1, oy))
        return None
    
    def snap_to_path(self, pos: tuple) -> tuple:
        """Snap click to nearest path cell."""
        x, y = pos
        if self.maze[y][x] == 0:
            return (x, y)
        from collections import deque
        queue = deque([(x, y, 0)])
        visited = {(x, y)}
        while queue:
            cx, cy, dist = queue.popleft()
            if self.maze[cy][cx] == 0:
                return (cx, cy)
            for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < self.maze_width and 0 <= ny < self.maze_height and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append((nx, ny, dist + 1))
        return (x, y)
    
    def save_solution_image(self):
        """Save current maze with solution path as PNG."""
        cs = max(4, self.base_cell_size)
        colors = self.active_colors
        surf = pygame.Surface((self.maze_width * cs, self.maze_height * cs))
        
        for y in range(self.maze_height):
            for x in range(self.maze_width):
                rect = pygame.Rect(x * cs, y * cs, cs, cs)
                pygame.draw.rect(surf, colors['wall' if self.maze[y][x] == 1 else 'path'], rect)
        
        for (vx, vy) in self.visited:
            if (vx, vy) not in self.solution_path and (vx, vy) != self.start and (vx, vy) != self.end:
                rect = pygame.Rect(vx * cs + 1, vy * cs + 1, cs - 2, cs - 2)
                pygame.draw.rect(surf, colors['visited_dim'], rect)
        
        if len(self.solution_path) > 1:
            points = [((px + 0.5) * cs, (py + 0.5) * cs) for (px, py) in self.solution_path]
            pygame.draw.lines(surf, colors['solution'], False, points, max(2, cs // 3))
        
        for (px, py), color in [(self.start, colors['start']), (self.end, colors['end'])]:
            pygame.draw.rect(surf, color, (px * cs + 2, py * cs + 2, cs - 4, cs - 4), border_radius=2)
        
        filename = f"maze_solution_{int(time.time())}.png"
        pygame.image.save(surf, filename)
        print(f"Saved solution to {filename}")
    
    def zoom_at(self, factor, screen_x, screen_y):
        """Zoom centered on screen coordinates."""
        cs = self.base_cell_size * self.zoom_level
        maze_x = (screen_x - self.maze_offset_x - self.pan_offset_x) / cs
        maze_y = (screen_y - self.maze_offset_y - self.pan_offset_y) / cs
        
        new_zoom = max(self.min_zoom, min(self.max_zoom, self.zoom_level * factor))
        if new_zoom == self.zoom_level:
            return
        
        self.zoom_level = new_zoom
        cs_new = self.base_cell_size * self.zoom_level
        self.pan_offset_x = screen_x - self.maze_offset_x - maze_x * cs_new
        self.pan_offset_y = screen_y - self.maze_offset_y - maze_y * cs_new
        self.clamp_pan()
    
    def clamp_pan(self):
        """Keep maze within screen bounds."""
        cs = self.base_cell_size * self.zoom_level
        maze_w = self.maze_width * cs
        maze_h = self.maze_height * cs
        
        screen_w = self.screen_width - 2 * MAZE_PADDING
        screen_h = self.screen_height - MAZE_PADDING * 2 - UI_HEIGHT
        
        if maze_w > screen_w:
            max_pan_x = (maze_w - screen_w) / 2
            self.pan_offset_x = max(-max_pan_x, min(max_pan_x, self.pan_offset_x))
        else:
            self.pan_offset_x = 0
        
        if maze_h > screen_h:
            max_pan_y = (maze_h - screen_h) / 2
            self.pan_offset_y = max(-max_pan_y, min(max_pan_y, self.pan_offset_y))
        else:
            self.pan_offset_y = 0
    
    def reset_zoom_pan(self):
        self.zoom_level = 1.0
        self.pan_offset_x = 0
        self.pan_offset_y = 0
    
    def set_algorithm(self, idx: int):
        self.algorithm_idx = idx % len(ALGORITHMS)
        self.restart_solver()
    
    def step_solver(self):
        if self.done or self.solver_gen is None:
            return
        try:
            state = next(self.solver_gen)
            self.visited, self.current_pos, self.solution_path, self.done = state
        except StopIteration as e:
            self.solution_path = e.value if e.value else []
            self.done = True
            self.solve_duration_ms = pygame.time.get_ticks() - self.solve_start_time
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.mode == 'image_cropping':
                        # Cancel crop mode, return to full image selection
                        self.mode = 'image_selecting_original'
                        self.crop_rect = None
                        self.crop_dragging = False
                    else:
                        return False
                elif event.key == pygame.K_x or event.key == pygame.K_q:
                    return False
                elif event.key == pygame.K_f or event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                    info = pygame.display.Info()
                    self.screen_width = info.current_w
                    self.screen_height = info.current_h
                    if self.mode == 'generated':
                        self.generate_new_maze()
                    else:
                        self.recalculate_layout()
                elif event.key == pygame.K_i:
                    if event.mod & pygame.KMOD_CTRL:
                        # Ctrl+I: Toggle maze color inversion
                        if self.mode != 'generated':
                            self.invert_maze_colors = not self.invert_maze_colors
                            print(f"Maze color inversion: {'ON' if self.invert_maze_colors else 'OFF'}")
                            self.reload_image_maze()
                    else:
                        # I: Load image
                        root = tk.Tk()
                        root.withdraw()
                        path = filedialog.askopenfilename(
                            title="Select Maze Image",
                            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")]
                        )
                        root.destroy()
                        if path:
                            self.load_image_maze(path)
                elif event.key == pygame.K_s:
                    if self.mode != 'generated':
                        self.save_solution_image()
                    else:
                        self.auto_step = not self.auto_step
                        if not self.auto_step:
                            self.step_solver()
                elif event.key == pygame.K_SPACE:
                    if self.mode == 'image_cropping' and self.crop_rect:
                        # Confirm crop, reload maze with cropped region
                        self.load_image_maze(self.image_path, crop_rect=self.crop_rect)
                    elif self.mode == 'image_selecting_original' and len(self.click_points) == 2:
                        # Confirm selection on original image, switch to grid view
                        self.mode = 'image_solving'
                        self.restart_solver()
                    elif self.mode == 'image_selecting' and len(self.click_points) == 2:
                        self.mode = 'image_solving'
                        self.restart_solver()
                    elif self.mode == 'image_selecting' and self.drag_selecting and self.drag_start_maze and self.drag_end_maze:
                        # Confirm drag selection
                        self.start = self.drag_start_maze
                        self.end = self.drag_end_maze
                        self.click_points = [self.drag_start_maze, self.drag_end_maze]
                        self.mode = 'image_solving'
                        self.restart_solver()
                    else:
                        self.paused = not self.paused
                elif event.key == pygame.K_TAB:
                    # Toggle between original image view and grid view during selection
                    if self.mode == 'image_selecting_original':
                        self.mode = 'image_selecting'
                    elif self.mode == 'image_selecting':
                        self.mode = 'image_selecting_original'
                    # TAB not available in crop mode
                elif event.key == pygame.K_r:
                    if self.mode == 'generated':
                        self.generate_new_maze()
                    else:
                        self.mode = 'generated'
                        self.active_colors = COLORS
                        self.generate_new_maze()
                elif event.key == pygame.K_UP:
                    self.step_delay = min(200, self.step_delay + 10)
                elif event.key == pygame.K_DOWN:
                    self.step_delay = max(0, self.step_delay - 10)
                elif event.key == pygame.K_v:
                    self.show_visited = not self.show_visited
                elif event.key == pygame.K_c:
                    if self.mode == 'image_selecting_original':
                        # Enter crop mode
                        self.mode = 'image_cropping'
                        self.crop_rect = None
                        self.crop_drag_start = None
                        self.crop_drag_end = None
                        self.crop_dragging = False
                    elif self.mode != 'generated':
                        # Toggle maze color inversion (for images with white paths/black walls)
                        self.invert_maze_colors = not self.invert_maze_colors
                        print(f"Maze color inversion: {'ON' if self.invert_maze_colors else 'OFF'}")
                        self.reload_image_maze()
                elif event.key == pygame.K_1:
                    self.set_algorithm(0)
                elif event.key == pygame.K_2:
                    self.set_algorithm(1)
                elif event.key == pygame.K_3:
                    self.set_algorithm(2)
                elif event.key == pygame.K_EQUALS or event.key == pygame.K_KP_PLUS:
                    self.zoom_at(1.25, self.screen_width // 2, self.screen_height // 2)
                elif event.key == pygame.K_MINUS or event.key == pygame.K_KP_MINUS:
                    self.zoom_at(0.8, self.screen_width // 2, self.screen_height // 2)
                elif event.key == pygame.K_0:
                    self.reset_zoom_pan()
                elif event.key == pygame.K_HOME:
                    self.pan_offset_x = 0
                    self.pan_offset_y = 0
            elif event.type == pygame.MOUSEWHEEL:
                if self.mode not in ('image_cropping', 'image_selecting_original'):
                    mx, my = pygame.mouse.get_pos()
                    factor = 1.15 if event.y > 0 else 1/1.15
                    self.zoom_at(factor, mx, my)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if self.mode == 'image_cropping':
                        # Start crop drag
                        self.crop_dragging = True
                        self.crop_drag_start = event.pos
                        self.crop_drag_end = event.pos
                    elif self.mode == 'image_selecting_original':
                        # Click on original image
                        maze_pos = self.original_to_maze(event.pos)
                        if maze_pos:
                            maze_pos = self.snap_to_path(maze_pos)
                            if self.selecting_start:
                                self.start = maze_pos
                                self.click_points = [maze_pos]
                                self.selecting_start = False
                            else:
                                self.end = maze_pos
                                self.click_points.append(maze_pos)
                                self.selecting_start = True  # Allow re-selection
                    elif self.mode == 'image_selecting':
                        # Start drag-to-select on grid view
                        self.drag_selecting = True
                        self.drag_start_pos = event.pos
                        maze_pos = self.screen_to_maze(event.pos)
                        self.drag_start_maze = self.snap_to_path(maze_pos)
                        self.drag_end_pos = event.pos
                        self.drag_end_maze = self.drag_start_maze
                elif event.button == 2 or event.button == 3:
                    if self.mode == 'image_cropping':
                        # Right-click cancels crop
                        self.mode = 'image_selecting_original'
                        self.crop_rect = None
                        self.crop_dragging = False
                    else:
                        self.dragging = True
                        self.drag_start = pygame.mouse.get_pos()
                        self.drag_pan_start = (self.pan_offset_x, self.pan_offset_y)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    if self.mode == 'image_cropping' and self.crop_dragging:
                        # Finalize crop rectangle
                        self.crop_dragging = False
                        start_orig = self.screen_to_original(self.crop_drag_start)
                        end_orig = self.screen_to_original(self.crop_drag_end)
                        if start_orig and end_orig:
                            x = min(start_orig[0], end_orig[0])
                            y = min(start_orig[1], end_orig[1])
                            w = abs(start_orig[0] - end_orig[0])
                            h = abs(start_orig[1] - end_orig[1])
                            if w > 0 and h > 0:
                                self.crop_rect = (x, y, w, h)
                    elif self.mode == 'image_selecting' and self.drag_selecting:
                        # End drag-to-select
                        self.drag_selecting = False
                        maze_pos = self.screen_to_maze(event.pos)
                        self.drag_end_maze = self.snap_to_path(maze_pos)
                        self.drag_end_pos = event.pos
                        # Auto-confirm drag selection
                        self.start = self.drag_start_maze
                        self.end = self.drag_end_maze
                        self.click_points = [self.drag_start_maze, self.drag_end_maze]
                        self.mode = 'image_solving'
                        self.restart_solver()
                elif event.button == 2 or event.button == 3:
                    self.dragging = False
            elif event.type == pygame.MOUSEMOTION:
                if self.dragging:
                    mx, my = pygame.mouse.get_pos()
                    dx = mx - self.drag_start[0]
                    dy = my - self.drag_start[1]
                    self.pan_offset_x = self.drag_pan_start[0] + dx
                    self.pan_offset_y = self.drag_pan_start[1] + dy
                    self.clamp_pan()
                elif self.mode == 'image_cropping' and self.crop_dragging:
                    # Update crop drag preview
                    self.crop_drag_end = pygame.mouse.get_pos()
                elif self.mode == 'image_selecting' and self.drag_selecting:
                    # Update drag preview
                    self.drag_end_pos = pygame.mouse.get_pos()
                    maze_pos = self.screen_to_maze(self.drag_end_pos)
                    self.drag_end_maze = self.snap_to_path(maze_pos)
        return True
    
    def update(self):
        if self.auto_step and not self.paused and not self.done:
            now = pygame.time.get_ticks()
            if now - self.last_step_time >= self.step_delay:
                for _ in range(self.steps_per_frame):
                    self.step_solver()
                    if self.done:
                        break
                self.last_step_time = now
            
            # Live timer update during solving
            if not self.done:
                self.solve_duration_ms = now - self.solve_start_time
        
        # Keyboard panning when zoomed (only in grid view modes)
        if self.zoom_level > 1.0 and self.mode not in ('image_cropping', 'image_selecting_original'):
            keys = pygame.key.get_pressed()
            pan_speed = max(5, int(20 / self.zoom_level))
            if keys[pygame.K_LEFT]:
                self.pan_offset_x += pan_speed
            if keys[pygame.K_RIGHT]:
                self.pan_offset_x -= pan_speed
            if keys[pygame.K_UP]:
                self.pan_offset_y += pan_speed
            if keys[pygame.K_DOWN]:
                self.pan_offset_y -= pan_speed
            self.clamp_pan()
    
    def draw_maze(self):
        colors = self.active_colors
        cs = self.cell_size
        ox = self.maze_offset_x + self.pan_offset_x
        oy = self.maze_offset_y + self.pan_offset_y
        
        # Crop mode - show original image with crop overlay
        if self.mode == 'image_cropping' and self.original_image:
            self._draw_crop_mode(colors)
            return
        
        # Original image selection mode - show full-res image
        if self.mode == 'image_selecting_original' and self.original_image:
            self._draw_original_image_selection(colors)
            return
        
        # Calculate visible cell range for performance
        start_x = max(0, int((-ox) / cs))
        end_x = min(self.maze_width, int((self.screen_width - ox) / cs) + 1)
        start_y = max(0, int((-oy) / cs))
        end_y = min(self.maze_height, int((self.screen_height - oy) / cs) + 1)
        
        # Draw maze walls and paths (only visible cells)
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                rect = pygame.Rect(ox + x * cs, oy + y * cs, cs, cs)
                if self.maze[y][x] == 1:
                    pygame.draw.rect(self.screen, colors['wall'], rect)
                else:
                    pygame.draw.rect(self.screen, colors['path'], rect)
        
        # Draw visited cells (only visible)
        if self.show_visited:
            for (vx, vy) in self.visited:
                if vx < start_x or vx >= end_x or vy < start_y or vy >= end_y:
                    continue
                if (vx, vy) != self.start and (vx, vy) != self.end:
                    if (vx, vy) in self.solution_path:
                        continue
                    rect = pygame.Rect(ox + vx * cs + 1, oy + vy * cs + 1, cs - 2, cs - 2)
                    color = colors['visited_dim'] if cs < 8 else colors['visited']
                    pygame.draw.rect(self.screen, color, rect)
        
        # Draw solution path as connected lines (always visible at any zoom)
        if len(self.solution_path) > 1:
            points = [
                (ox + (px + 0.5) * cs, oy + (py + 0.5) * cs)
                for (px, py) in self.solution_path
            ]
            thickness = max(2, int(cs * 0.4))
            pygame.draw.lines(self.screen, colors['solution'], False, points, thickness)
        
        # Draw start/end markers
        sx, sy = self.start
        ex, ey = self.end
        for (px, py), color in [((sx, sy), colors['start']), ((ex, ey), colors['end'])]:
            rect = pygame.Rect(ox + px * cs + 2, oy + py * cs + 2, cs - 4, cs - 4)
            pygame.draw.rect(self.screen, color, rect, border_radius=2)
        
        # Draw endpoint ring on top of solution path to show connection
        if self.done and self.solution_path:
            ex, ey = self.end
            rect = pygame.Rect(ox + ex * cs + 1, oy + ey * cs + 1, cs - 2, cs - 2)
            pygame.draw.rect(self.screen, colors['end'], rect, width=2, border_radius=2)
        
        # Draw current position
        cx, cy = self.current_pos
        if not self.done and (cx, cy) != self.start and (cx, cy) != self.end:
            if start_x <= cx < end_x and start_y <= cy < end_y:
                rect = pygame.Rect(ox + cx * cs + 1, oy + cy * cs + 1, cs - 2, cs - 2)
                pygame.draw.rect(self.screen, colors['current'], rect)
        
        # Draw drag selection preview (in grid view)
        if self.mode == 'image_selecting' and self.drag_selecting and self.drag_start_pos and self.drag_end_pos:
            self._draw_drag_preview(colors)
    
    def _draw_original_image_selection(self, colors):
        """Draw original image scaled to fit screen for point selection."""
        img_w, img_h = self.original_size
        screen_w = self.screen_width - 2 * MAZE_PADDING
        screen_h = self.screen_height - MAZE_PADDING * 2 - UI_HEIGHT
        
        # Calculate scale to fit
        scale = min(screen_w / img_w, screen_h / img_h, 1.0)
        draw_w = int(img_w * scale)
        draw_h = int(img_h * scale)
        
        # Center the image
        draw_x = (self.screen_width - draw_w) // 2
        draw_y = MAZE_PADDING + (screen_h - draw_h) // 2
        
        self.image_display_rect = pygame.Rect(draw_x, draw_y, draw_w, draw_h)
        
        # Scale and draw original image
        scaled_img = pygame.transform.smoothscale(self.original_image, (draw_w, draw_h))
        self.screen.blit(scaled_img, (draw_x, draw_y))
        
        # Draw border
        pygame.draw.rect(self.screen, colors['selection'], self.image_display_rect, 3)
        
        # Draw click points mapped to original image coordinates
        for i, (mx, my) in enumerate(self.click_points):
            px = draw_x + int(mx * draw_w / self.maze_width)
            py = draw_y + int(my * draw_h / self.maze_height)
            color = colors['start'] if i == 0 else colors['end']
            pygame.draw.circle(self.screen, color, (px, py), max(8, int(12 * scale)), 3)
            pygame.draw.circle(self.screen, (255, 255, 255), (px, py), max(6, int(10 * scale)), 1)
        
        # Draw drag preview if dragging on original
        if self.drag_selecting and self.drag_start_pos and self.drag_end_pos:
            pygame.draw.line(self.screen, colors['selection'], self.drag_start_pos, self.drag_end_pos, 3)
            # Start marker
            pygame.draw.circle(self.screen, colors['start'], self.drag_start_pos, 12, 3)
            # End marker
            pygame.draw.circle(self.screen, colors['end'], self.drag_end_pos, 12, 3)
    
    def _draw_drag_preview(self, colors):
        """Draw drag selection preview on grid view."""
        if not self.drag_start_pos or not self.drag_end_pos:
            return
        # Line from drag start to current mouse
        pygame.draw.line(self.screen, colors['selection'], self.drag_start_pos, self.drag_end_pos, 3)
        # Start marker
        pygame.draw.circle(self.screen, colors['start'], self.drag_start_pos, 10, 3)
        # End marker (current mouse pos)
        pygame.draw.circle(self.screen, colors['end'], self.drag_end_pos, 10, 3)
        # Show mapped maze coordinates
        if self.drag_start_maze:
            cs = self.cell_size
            ox = self.maze_offset_x + self.pan_offset_x
            oy = self.maze_offset_y + self.pan_offset_y
            sx = ox + (self.drag_start_maze[0] + 0.5) * cs
            sy = oy + (self.drag_start_maze[1] + 0.5) * cs
            pygame.draw.circle(self.screen, colors['start'], (int(sx), int(sy)), max(6, cs//2), 2)
        if self.drag_end_maze:
            cs = self.cell_size
            ox = self.maze_offset_x + self.pan_offset_x
            oy = self.maze_offset_y + self.pan_offset_y
            ex = ox + (self.drag_end_maze[0] + 0.5) * cs
            ey = oy + (self.drag_end_maze[1] + 0.5) * cs
            pygame.draw.circle(self.screen, colors['end'], (int(ex), int(ey)), max(6, cs//2), 2)
    
    def _draw_crop_mode(self, colors):
        """Draw original image with crop rectangle overlay (photo editor style)."""
        if not self.original_image:
            return
        
        img_w, img_h = self.original_size
        screen_w = self.screen_width - 2 * MAZE_PADDING
        screen_h = self.screen_height - MAZE_PADDING * 2 - UI_HEIGHT
        
        # Calculate scale to fit
        scale = min(screen_w / img_w, screen_h / img_h, 1.0)
        draw_w = int(img_w * scale)
        draw_h = int(img_h * scale)
        
        # Center the image
        draw_x = (self.screen_width - draw_w) // 2
        draw_y = MAZE_PADDING + (screen_h - draw_h) // 2
        
        self.image_display_rect = pygame.Rect(draw_x, draw_y, draw_w, draw_h)
        
        # Scale and draw original image
        scaled_img = pygame.transform.smoothscale(self.original_image, (draw_w, draw_h))
        self.screen.blit(scaled_img, (draw_x, draw_y))
        
        # Draw border
        pygame.draw.rect(self.screen, colors['selection'], self.image_display_rect, 3)
        
        # Draw existing click points (start/end) if any
        for i, (mx, my) in enumerate(self.click_points):
            px = draw_x + int(mx * draw_w / self.maze_width)
            py = draw_y + int(my * draw_h / self.maze_height)
            color = colors['start'] if i == 0 else colors['end']
            pygame.draw.circle(self.screen, color, (px, py), max(8, int(12 * scale)), 3)
            pygame.draw.circle(self.screen, (255, 255, 255), (px, py), max(6, int(10 * scale)), 1)
        
        # Calculate crop rectangle in screen coordinates
        if self.crop_dragging and self.crop_drag_start and self.crop_drag_end:
            # Live drag preview
            x1, y1 = self.crop_drag_start
            x2, y2 = self.crop_drag_end
            crop_rect_screen = (
                min(x1, x2), min(y1, y2),
                abs(x1 - x2), abs(y1 - y2)
            )
        elif self.crop_rect:
            # Confirmed crop rect - convert from original image pixels to screen
            cx, cy, cw, ch = self.crop_rect
            crop_rect_screen = (
                draw_x + int(cx * scale),
                draw_y + int(cy * scale),
                int(cw * scale),
                int(ch * scale)
            )
        else:
            crop_rect_screen = None
        
        if crop_rect_screen:
            cr_x, cr_y, cr_w, cr_h = crop_rect_screen
            
            # Draw dark overlay outside crop area (photo editor style)
            overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))  # Semi-transparent black
            
            # Cut out the crop area (make it transparent)
            crop_area = pygame.Rect(cr_x, cr_y, cr_w, cr_h)
            pygame.draw.rect(overlay, (0, 0, 0, 0), crop_area)
            
            self.screen.blit(overlay, (0, 0))
            
            # Draw crop rectangle border (bright, thick)
            pygame.draw.rect(self.screen, colors['selection'], crop_rect_screen, 3)
            
            # Draw corner handles
            handle_size = 10
            corners = [
                (cr_x, cr_y),                           # Top-left
                (cr_x + cr_w, cr_y),                    # Top-right
                (cr_x, cr_y + cr_h),                    # Bottom-left
                (cr_x + cr_w, cr_y + cr_h)              # Bottom-right
            ]
            for corner in corners:
                handle_rect = pygame.Rect(corner[0] - handle_size//2, corner[1] - handle_size//2, handle_size, handle_size)
                pygame.draw.rect(self.screen, colors['selection'], handle_rect)
                pygame.draw.rect(self.screen, (255, 255, 255), handle_rect, 2)
            
            # Show dimensions text
            dim_text = f"{cr_w // max(1, scale)} x {cr_h // max(1, scale)} px"
            text_surf = self.font.render(dim_text, True, colors['selection'])
            text_rect = text_surf.get_rect()
            text_rect.midbottom = (cr_x + cr_w // 2, cr_y - 5)
            # Background for text
            bg_rect = text_rect.inflate(10, 6)
            pygame.draw.rect(self.screen, (0, 0, 0, 200), bg_rect)
            self.screen.blit(text_surf, text_rect)
    
    def draw_ui(self):
        colors = self.active_colors
        ui_y = self.screen_height - UI_HEIGHT + 10
        pygame.draw.rect(self.screen, colors['ui_bg'], (0, self.screen_height - UI_HEIGHT, self.screen_width, UI_HEIGHT))
        
        algo_key, algo_name, _, _ = ALGORITHMS[self.algorithm_idx]
        title = f'Algorithm: {algo_name}  (Keys 1/2/3 to switch)'
        text = self.font_big.render(title, True, colors['text'])
        self.screen.blit(text, (20, ui_y))
        
        if self.mode == 'image_cropping':
            if self.crop_dragging:
                msg = "Crop Mode: Drag to select area  |  Release to finalize  |  SPACE: Confirm crop  |  ESC: Cancel"
            elif self.crop_rect:
                cx, cy, cw, ch = self.crop_rect
                msg = f"Crop Mode: Crop set ({cw}x{ch}px)  |  SPACE: Confirm crop  |  ESC: Cancel  |  Drag again to reselect"
            else:
                msg = "Crop Mode: Drag to select area  |  SPACE: Confirm crop  |  ESC: Cancel"
            text = self.font_big.render(msg, True, colors['selection'])
            self.screen.blit(text, (20, ui_y + 28))
        elif self.mode == 'image_selecting_original':
            if self.drag_selecting:
                msg = "Drag on image: START -> END  |  Release to confirm  |  TAB: Grid view"
            else:
                msg = f"Click to set {'START' if self.selecting_start else 'END'} ({len(self.click_points) + 1}/2)  |  Drag to select both  |  SPACE: Confirm & solve  |  TAB: Grid view  |  C: Crop"
            text = self.font_big.render(msg, True, colors['selection'])
            self.screen.blit(text, (20, ui_y + 28))
        elif self.mode == 'image_selecting':
            if self.drag_selecting:
                msg = "Drag on grid: START -> END  |  Release to confirm  |  TAB: Original view"
            else:
                msg = f"Click to set {'START' if self.selecting_start else 'END'} ({len(self.click_points) + 1}/2)  |  Drag to select both  |  SPACE: Confirm & solve  |  TAB: Original view"
            text = self.font_big.render(msg, True, colors['selection'])
            self.screen.blit(text, (20, ui_y + 28))
        else:
            status = f'SOLVING...  Time: {self.solve_duration_ms}ms' if not self.done else f'DONE! Path: {len(self.solution_path)} steps  Time: {self.solve_duration_ms}ms'
            color = colors['current'] if not self.done else colors['solution']
            text = self.font_big.render(status, True, color)
            self.screen.blit(text, (20, ui_y + 28))
        
        controls = [
            'X/ESC/Q: Exit',
            'F/F11: Toggle Fullscreen',
            'SPACE: Pause/Resume' + (' / Confirm Selection' if self.mode in ('image_selecting', 'image_selecting_original') else '') + (' / Confirm Crop' if self.mode == 'image_cropping' else ''),
            'UP/DOWN: Speed',
            'S: Single Step' + (' / Save Image' if self.mode != 'generated' else ''),
            'V: Toggle Visited',
            'R: New Maze' + (' / Back to Generated' if self.mode != 'generated' else ''),
            '1/2/3: Algorithm',
            'I: Load Image' + (' / Ctrl+I: Invert Colors' if self.mode != 'generated' else ''),
            'C: Invert Colors' + (' (Crop in select mode)' if self.mode == 'image_selecting_original' else '') if self.mode != 'generated' else '',
            'TAB: Switch View (Image/Grid)' if self.mode in ('image_selecting', 'image_selecting_original') else '',
            'Mouse Wheel: Zoom',
            'MMB/RMB Drag: Pan',
            '0: Reset View',
            'Home: Center',
        ]
        for i, ctrl in enumerate(controls):
            if not ctrl:
                continue
            col = i % 4
            row = i // 4
            text = self.font_small.render(ctrl, True, colors['text_dim'])
            self.screen.blit(text, (20 + col * 240, ui_y + 55 + row * 18))
        
        delay_text = f'Delay: {self.step_delay}ms  |  Auto: {"ON" if self.auto_step else "OFF"}  |  Visited: {"ON" if self.show_visited else "OFF"}'
        text = self.font_small.render(delay_text, True, colors['text_dim'])
        self.screen.blit(text, (self.screen_width - 400, ui_y))
        if self.mode != 'generated':
            invert_text = f'Invert: {"ON" if self.invert_maze_colors else "OFF"}  (C / Ctrl+I to toggle)'
            text = self.font_small.render(invert_text, True, colors['selection'])
            self.screen.blit(text, (self.screen_width - 400, ui_y + 20))
            stats = f'Maze: {self.maze_width}x{self.maze_height}  |  Cells: {self.maze_width * self.maze_height}  |  Visited: {len(self.visited)}  |  Cell: {self.cell_size}px'
            text = self.font_small.render(stats, True, colors['text_dim'])
            self.screen.blit(text, (self.screen_width - 400, ui_y + 40))
            zoom_text = f'Zoom: {self.zoom_level:.2f}x  |  Pan: ({self.pan_offset_x:.0f}, {self.pan_offset_y:.0f})'
            text = self.font_small.render(zoom_text, True, colors['text_dim'])
            self.screen.blit(text, (self.screen_width - 400, ui_y + 60))
        else:
            stats = f'Maze: {self.maze_width}x{self.maze_height}  |  Cells: {self.maze_width * self.maze_height}  |  Visited: {len(self.visited)}  |  Cell: {self.cell_size}px'
            text = self.font_small.render(stats, True, colors['text_dim'])
            self.screen.blit(text, (self.screen_width - 400, ui_y + 20))
            zoom_text = f'Zoom: {self.zoom_level:.2f}x  |  Pan: ({self.pan_offset_x:.0f}, {self.pan_offset_y:.0f})'
            text = self.font_small.render(zoom_text, True, colors['text_dim'])
            self.screen.blit(text, (self.screen_width - 400, ui_y + 40))

    def draw(self):
        self.screen.fill(self.active_colors['bg'])
        self.draw_maze()
        self.draw_ui()
        pygame.display.flip()
    
    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()
        sys.exit()


def main():
    print("Maze Solver Visualization")
    print("Controls:")
    print("  SPACE - Pause/Resume (or confirm start/end selection)")
    print("  ↑/↓   - Speed up/slow down")
    print("  S     - Single step (when paused) / Save solution image (image mode)")
    print("  V     - Toggle visited cells")
    print("  R     - Generate new maze (or back to generated from image mode)")
    print("  1/2/3 - Switch algorithm (DFS/Bi-DFS/BFS)")
    print("  I     - Load maze image (PNG/JPG/BMP)")
    print("  C     - Invert maze colors (image mode) / Ctrl+I also works")
    print("  TAB   - Toggle between original image view and grid view (selection mode)")
    print("  Mouse (Original View): Click to set start/end, or drag start->end")
    print("  Mouse (Grid View): Click to set start/end, or drag start->end")
    print("  Mouse Wheel - Zoom (grid view)")
    print("  MMB/RMB Drag - Pan (grid view)")
    print("  0     - Reset view (grid view)")
    print("  Home  - Center view (grid view)")
    print("  ESC/Q - Quit")
    print()
    
    visualizer = MazeVisualizer()
    visualizer.run()


if __name__ == '__main__':
    main()