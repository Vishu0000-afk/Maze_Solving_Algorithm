import time
import random
from typing import List, Tuple, Optional, Generator, Set
Point = Tuple[int, int]
Path = List[Point]
SolverState = Tuple[Set[Point], Point, Path, bool]  # visited, current, path, done


def generate_maze(width: int, height: int, complexity: float = 0.7) -> List[List[int]]:
    """Generate a random maze using iterative randomized DFS."""
    maze = [[1] * width for _ in range(height)]
    stack = [(1, 1)]
    maze[1][1] = 0
    
    while stack:
        x, y = stack[-1]
        directions = [(0, 2), (2, 0), (0, -2), (-2, 0)]
        random.shuffle(directions)
        carved = False
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 < nx < width - 1 and 0 < ny < height - 1 and maze[ny][nx] == 1:
                maze[y + dy // 2][x + dx // 2] = 0
                maze[ny][nx] = 0
                stack.append((nx, ny))
                carved = True
                break
        if not carved:
            stack.pop()
    
    maze[1][0] = 0
    return maze


def find_furthest_cell(maze: List[List[int]], start: Point) -> Point:
    """BFS to find all reachable cells, then pick one with max Euclidean distance from start."""
    from collections import deque
    height, width = len(maze), len(maze[0])
    queue = deque([start])
    visited = {start}
    reachable = []
    
    while queue:
        x, y = queue.popleft()
        reachable.append((x, y))
        for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                if (nx, ny) not in visited and maze[ny][nx] == 0:
                    visited.add((nx, ny))
                    queue.append((nx, ny))
    
    if not reachable:
        return start
    
    sx, sy = start
    return max(reachable, key=lambda p: (p[0] - sx)**2 + (p[1] - sy)**2)


def dfs_solver(maze: List[List[int]], start: Point, end: Point) -> Optional[Path]:
    """Iterative DFS - finds any path fast."""
    height, width = len(maze), len(maze[0])
    stack = [(start, [start])]
    visited = [[False] * width for _ in range(height)]
    visited[start[1]][start[0]] = True
    
    while stack:
        (x, y), path = stack.pop()
        if (x, y) == end:
            return path
        
        for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                if not visited[ny][nx] and maze[ny][nx] == 0:
                    visited[ny][nx] = True
                    stack.append(((nx, ny), path + [(nx, ny)]))
    return None


def bidirectional_dfs(maze: List[List[int]], start: Point, end: Point) -> Optional[Path]:
    """Bidirectional DFS - ~2x faster on large mazes."""
    height, width = len(maze), len(maze[0])
    
    stack_fwd = [(start, [start])]
    stack_bwd = [(end, [end])]
    visited_fwd = [[False] * width for _ in range(height)]
    visited_bwd = [[False] * width for _ in range(height)]
    parent_fwd = {}
    parent_bwd = {}
    
    visited_fwd[start[1]][start[0]] = True
    visited_bwd[end[1]][end[0]] = True
    parent_fwd[start] = None
    parent_bwd[end] = None
    
    meet_point = None
    
    while stack_fwd and stack_bwd:
        for _ in range(2):
            if stack_fwd:
                (x, y), _ = stack_fwd.pop()
                if visited_bwd[y][x]:
                    meet_point = (x, y)
                    break
                for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        if not visited_fwd[ny][nx] and maze[ny][nx] == 0:
                            visited_fwd[ny][nx] = True
                            parent_fwd[(nx, ny)] = (x, y)
                            stack_fwd.append(((nx, ny), []))
        
        for _ in range(2):
            if stack_bwd:
                (x, y), _ = stack_bwd.pop()
                if visited_fwd[y][x]:
                    meet_point = (x, y)
                    break
                for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        if not visited_bwd[ny][nx] and maze[ny][nx] == 0:
                            visited_bwd[ny][nx] = True
                            parent_bwd[(nx, ny)] = (x, y)
                            stack_bwd.append(((nx, ny), []))
        
        if meet_point:
            break
    
    if not meet_point:
        return None
    
    path = []
    curr = meet_point
    while curr:
        path.append(curr)
        curr = parent_fwd[curr]
    path.reverse()
    
    curr = parent_bwd[meet_point]
    while curr:
        path.append(curr)
        curr = parent_bwd[curr]
    
    return path


def bfs_solver(maze: List[List[int]], start: Point, end: Point) -> Optional[Path]:
    """BFS for comparison - guarantees shortest path."""
    from collections import deque
    height, width = len(maze), len(maze[0])
    queue = deque([(start, [start])])
    visited = [[False] * width for _ in range(height)]
    visited[start[1]][start[0]] = True
    
    while queue:
        (x, y), path = queue.popleft()
        if (x, y) == end:
            return path
        for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                if not visited[ny][nx] and maze[ny][nx] == 0:
                    visited[ny][nx] = True
                    queue.append(((nx, ny), path + [(nx, ny)]))
    return None


# ==================== Generator-based solvers for visualization ====================

def dfs_generator(maze: List[List[int]], start: Point, end: Point) -> Generator[SolverState, None, Optional[Path]]:
    """Iterative DFS - yields state each step for visualization."""
    height, width = len(maze), len(maze[0])
    stack = [(start, [start])]
    visited = set([start])
    
    while stack:
        (x, y), path = stack.pop()
        
        if (x, y) == end:
            yield (visited, (x, y), path, True)
            return path
        
        yield (visited, (x, y), path, False)
        
        for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                if (nx, ny) not in visited and maze[ny][nx] == 0:
                    visited.add((nx, ny))
                    stack.append(((nx, ny), path + [(nx, ny)]))
    
    yield (visited, start, [], True)
    return None


def bidirectional_dfs_generator(maze: List[List[int]], start: Point, end: Point) -> Generator[SolverState, None, Optional[Path]]:
    """Bidirectional DFS - yields state each step for visualization."""
    height, width = len(maze), len(maze[0])
    
    stack_fwd = [(start, [start])]
    stack_bwd = [(end, [end])]
    visited_fwd = {start}
    visited_bwd = {end}
    parent_fwd = {start: None}
    parent_bwd = {end: None}
    
    meet_point = None
    step = 0
    
    while stack_fwd and stack_bwd:
        for _ in range(2):
            if stack_fwd:
                (x, y), _ = stack_fwd.pop()
                step += 1
                if (x, y) in visited_bwd:
                    meet_point = (x, y)
                    break
                for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        if (nx, ny) not in visited_fwd and maze[ny][nx] == 0:
                            visited_fwd.add((nx, ny))
                            parent_fwd[(nx, ny)] = (x, y)
                            stack_fwd.append(((nx, ny), []))
                if step % 5 == 0:
                    yield (visited_fwd | visited_bwd, (x, y), [], False)
        
        for _ in range(2):
            if stack_bwd:
                (x, y), _ = stack_bwd.pop()
                step += 1
                if (x, y) in visited_fwd:
                    meet_point = (x, y)
                    break
                for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        if (nx, ny) not in visited_bwd and maze[ny][nx] == 0:
                            visited_bwd.add((nx, ny))
                            parent_bwd[(nx, ny)] = (x, y)
                            stack_bwd.append(((nx, ny), []))
                if step % 5 == 0:
                    yield (visited_fwd | visited_bwd, (x, y), [], False)
        
        if meet_point:
            break
    
    if not meet_point:
        yield (visited_fwd | visited_bwd, start, [], True)
        return None
    
    path = []
    curr = meet_point
    while curr:
        path.append(curr)
        curr = parent_fwd[curr]
    path.reverse()
    
    curr = parent_bwd[meet_point]
    while curr:
        path.append(curr)
        curr = parent_bwd[curr]
    
    yield (visited_fwd | visited_bwd, meet_point, path, True)
    return path


def bfs_generator(maze: List[List[int]], start: Point, end: Point) -> Generator[SolverState, None, Optional[Path]]:
    """BFS - yields state each step for visualization."""
    from collections import deque
    height, width = len(maze), len(maze[0])
    queue = deque([(start, [start])])
    visited = {start}
    
    while queue:
        (x, y), path = queue.popleft()
        
        if (x, y) == end:
            yield (visited, (x, y), path, True)
            return path
        
        yield (visited, (x, y), path, False)
        
        for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                if (nx, ny) not in visited and maze[ny][nx] == 0:
                    visited.add((nx, ny))
                    queue.append(((nx, ny), path + [(nx, ny)]))
    
    yield (visited, start, [], True)
    return None


def benchmark():
    sizes = [(51, 51), (101, 101), (201, 201), (401, 401)]
    runs = 5
    
    print(f"{'Size':>10} | {'DFS (ms)':>10} | {'Bi-DFS (ms)':>12} | {'BFS (ms)':>10} | {'Speedup':>8}")
    print("-" * 65)
    
    for w, h in sizes:
        dfs_times = []
        bi_times = []
        bfs_times = []
        
        for _ in range(runs):
            maze = generate_maze(w, h)
            start = (0, 1)
            end = find_furthest_cell(maze, start)
            
            t0 = time.perf_counter()
            dfs_solver(maze, start, end)
            dfs_times.append((time.perf_counter() - t0) * 1000)
            
            t0 = time.perf_counter()
            bidirectional_dfs(maze, start, end)
            bi_times.append((time.perf_counter() - t0) * 1000)
            
            t0 = time.perf_counter()
            bfs_solver(maze, start, end)
            bfs_times.append((time.perf_counter() - t0) * 1000)
        
        avg_dfs = sum(dfs_times) / runs
        avg_bi = sum(bi_times) / runs
        avg_bfs = sum(bfs_times) / runs
        speedup = avg_bfs / avg_dfs
        
        print(f"{w}x{h:>3} | {avg_dfs:>10.2f} | {avg_bi:>12.2f} | {avg_bfs:>10.2f} | {speedup:>7.1f}x")


def solve_and_print(maze: List[List[int]], solver, name: str):
    start = (0, 1)
    end = find_furthest_cell(maze, start)
    t0 = time.perf_counter()
    path = solver(maze, start, end)
    elapsed = (time.perf_counter() - t0) * 1000
    
    if path:
        for x, y in path:
            maze[y][x] = 2
        print(f"{name}: {len(path)} steps, {elapsed:.2f}ms")
        for row in maze:
            print(''.join('█' if c == 1 else '·' if c == 0 else '░' for c in row))
    else:
        print(f"{name}: No path found")


if __name__ == "__main__":
    print("=== Benchmark ===")
    benchmark()
    
    print("\n=== Demo (31x31) ===")
    maze = generate_maze(31, 31)
    solve_and_print([row[:] for row in maze], dfs_solver, "DFS")
    print()
    solve_and_print([row[:] for row in maze], bidirectional_dfs, "Bi-DFS")
    print()
    solve_and_print([row[:] for row in maze], bfs_solver, "BFS")