import tempfile, os, time, cv2, threading, pygame
from typing import Any, Callable
from dataclasses import dataclass

from header.h_editor import h_Editor
from header.h_point import h_Point


class Util:
    _editor: h_Editor = None
    _editor_center: tuple[int, int] = None
    _id_counter: int = 0 # used to give anything a unique id

    @staticmethod
    def get_editor() -> h_Editor:
        if Util._editor is None:
            raise RuntimeError("Editor not initialized")
        return Util._editor

    @staticmethod
    def get_unique_id() -> int:
        Util._id_counter += 1
        return Util._id_counter

    @staticmethod
    def get_path_points(img, point_density: int, offset: tuple[int, int] = (0, 0)) -> list[tuple[int, int]]:
        path: list['Point'] = []

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)

        contours, hierarchy = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_TC89_KCOS)

        # add all points to the path making sure their all connected
        for c in contours:
            for p in c:
                path.append(Point(p[0][0] + offset[0], p[0][1] + offset[1]))

        # remove points that are too close to each other
        for p in path:
            for p2 in path:
                if p == p2:
                    continue
                if p.distance(p2) < point_density:
                    path.remove(p2)

        return path
    
    @staticmethod
    def connect_points(points: list['Point']) -> list['Point']:
        points = sorted(points, key=lambda p: p._id)
        connected = 0
        for p in [p for p in points if p._id != -1]:
            if p._id == -1: continue

            connected += 1
            i = points.index(p)
            if i == 0:
                p._prev = None
            else:
                p._prev = points[i - 1]
            if i == len(points) - 1:
                p._next = None
            else:
                if points[i + 1]._id != -1:                
                    p._next = points[i + 1]
        print(f"[INFO] Connected {connected} points")
        return points

    @staticmethod
    def clean_points(points: list['Point']) -> list['Point']:
        # remove points that are too close to each other
        for p in points:
            for p2 in points:
                if p == p2:
                    continue
                if p.distance(p2) < 10:
                    points.remove(p2)
        return points

    @staticmethod
    def _async(func: callable) -> threading.Thread:
        t = threading.Thread(target=func, daemon=True)
        t.start()
        return t
    
    @staticmethod
    def async_task(funcs: list[callable]) -> None:
        Util._async(lambda: [f for f in funcs if (lambda: (t:=Util._async(f), t.join()))()])

    @staticmethod
    def apply(funcs: list[Callable], *args, **kwargs) -> list[Any]:
        return [f(*args, **kwargs) for f in funcs]

    @staticmethod
    def open_notepad_with(text: str) -> None:
        tmp = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
        tmp.write(text.encode())
        tmp.flush()
        tmp.close()

        os.system(f"notepad.exe {tmp.name}")
    
    @staticmethod
    def wrap_function(func: Callable, callback: Callable, position: str = 'pre', ) -> Callable:
        def wrapper(*args, **kwargs):
            if position == 'pre':
                callback()
            func(*args, **kwargs)
            if position == 'post':
                callback()
        return wrapper

    @staticmethod
    def set_interval(func: Callable, interval: float) -> None:
        def wrapper():
            func()
            time.sleep(interval)
            Util.set_interval(func, interval)
        threading.Thread(target=wrapper, daemon=True).start()
                
    @staticmethod
    def calculate_bounds(points: list[h_Point]) -> 'Rect':
        min_x = 99999999
        min_y = 99999999
        max_x = -99999999
        max_y = -99999999

        for p in points:
            if p.x < min_x:
                min_x = p.x
            if p.y < min_y:
                min_y = p.y
            if p.x > max_x:
                max_x = p.x
            if p.y > max_y:
                max_y = p.y

        return Rect(min_x, min_y, max_x - min_x, max_y - min_y)

    @staticmethod
    def zoom_at_pos(screen: pygame.Surface, pos: tuple[float | int, float | int], scale: float | int) -> None:
        # Get the current mouse position
        x, y = pos

        # Create a new surface that is a copy of the original surface but scaled by the zoom factor
        zoomed_surface = pygame.transform.scale(screen, (int(screen.get_width() * scale), int(screen.get_height() * scale)))

        # Calculate the new position of the mouse on the zoomed surface
        zoomed_mouse_pos = x * scale, y * scale

        # Create a new surface that is the size of the screen
        new_surface = pygame.Surface((screen.get_width(), screen.get_height()))
        new_surface.fill((255, 255, 255))

        # Blit the zoomed surface onto this new surface at a position such that the new mouse position is at the center of the screen
        new_surface.blit(zoomed_surface, (screen.get_width() / 2 - zoomed_mouse_pos[0], screen.get_height() / 2 - zoomed_mouse_pos[1]))

        Util._editor_center = (screen.get_width() / 2 - zoomed_mouse_pos[0], screen.get_height() / 2 - zoomed_mouse_pos[1])

        # Replace the original surface with the new surface
        screen.blit(new_surface, (0, 0))
    
    @staticmethod
    def get_zoomed_mouse_pos(pos: tuple[float | int, float | int], zoom: float | int) -> tuple[float | int, float | int]:
        return (pos[0] - Util._editor_center[0]) / zoom, (pos[1] - Util._editor_center[1]) / zoom
    
    @staticmethod
    def convertorigin(point: 'Point', _from: int, _to: int) -> 'Point':
        if _from == _to:
            return point
        if _from == Origin.CENTER:
            if _to == Origin.TOP_LEFT:
                return Point(point.x - Util.get_editor()._image.get_width() / 2, point.y - Util.get_editor()._image.get_height() / 2)
        elif _from == Origin.TOP_LEFT:
            if _to == Origin.CENTER:
                return Point(point.x + Util.get_editor()._image.get_width() / 2, point.y + Util.get_editor()._image.get_height() / 2)
        raise ValueError("Invalid Origin")
    
    @staticmethod
    def copy_points(points: list['Point']) -> list['Point']:
        new_points: list['Point'] = []
        for p in points:
            new_points.append(Point(p.x, p.y))

        # copy over the next and prev pointers by finding the new points they point to
        for i in range(len(points)):
            if points[i]._next is not None:
                new_points[i]._next = new_points[points.index(points[i]._next)]
            if points[i]._prev is not None:
                new_points[i]._prev = new_points[points.index(points[i]._prev)]
            new_points[i]._id = points[i]._id
            new_points[i]._locked = points[i]._locked
        return new_points

    @staticmethod    
    def findpoint(points: list['Point'], id: int) -> 'Point':
        for p in points:
            if p._id == id:
                return p
        return None
    
    """
    Should be used after loading points using from_dict
    """
    @staticmethod
    def reconnect_points(points: list['Point']) -> list['Point']:
        
        for p in points:
            if p._next is not None:
                p._next = Util.findpoint(points, p._next)
            if p._prev is not None:
                p._prev = Util.findpoint(points, p._prev)

    @staticmethod
    def clear_point_metadata(points: list['Point']) -> list['Point']:
        for p in points:
            p._id = -1
            p._next = None
            p._prev = None
            p._locked = False
        return points

    class Transform:
        @staticmethod
        def vshift(points: list['Point'], amount: int) -> list['Point']:
            return Util.Transform.shift(points, (0, amount))    
    
        @staticmethod
        def hshift(points: list['Point'], amount: int) -> list['Point']:
            return Util.Transform.shift(points, (amount, 0))
        
        @staticmethod
        def shift(points: list['Point'], amount: tuple[int, int]) -> list['Point']:
            for p in points:
                p.x += amount[0]
                p.y += amount[1]
            return points
        
        @staticmethod
        def hflip(points: list['Point']) -> list['Point']:
            return Util.Transform.flip(points, True, False)

        @staticmethod
        def vflip(points: list['Point']) -> list['Point']:
            return Util.Transform.flip(points, False, True)

        @staticmethod
        def flip(points: list['Point'], horizontal: bool, vertical: bool) -> list['Point']:
            for p in points:
                if horizontal:
                    p.x = -p.x
                if vertical:
                    p.y = -p.y
            return points
        
class Origin:
    CENTER = 0
    TOP_LEFT = 1

@dataclass
class Rect:
    x: int
    y: int
    w: int
    h: int

    def contains(self, x: int, y: int) -> bool:
        return x >= self.x and x <= self.x + self.w and y >= self.y and y <= self.y + self.h

    """
    Returns a reference to it's self
    """
    def scale(self, scale: float) -> 'Rect':
        self.x *= scale
        self.y *= scale
        self.w *= scale
        self.h *= scale
        return self
    
    def round(self, precision: int) -> 'Rect':
        return Rect(round(self.x, precision), round(self.y, precision), round(self.w, precision), round(self.h, precision))

class Point(h_Point):
    def __init__(self, x: float | int, y: float | int, fully_initialized: bool = True) -> None:
        self._id: int = Util.get_unique_id()
        self.x = x
        self.y = y
        self._next = None
        self._prev = None
        self._locked = False
        self._initialized = fully_initialized

    @staticmethod
    def from_dict(d: dict, upgrade_if_needed: bool = True) -> 'Point':
        if upgrade_if_needed:
            d = Point._upgrade_data(d)

        p = Point(d["x"], d["y"], False)
        p._id = d["id"]
        p._locked = d["locked"]
        p._next = d["next"]
        p._prev = d["prev"]


        return p
    
    def set_pos(self, x: int, y: int) -> None:
        self.x = x
        self.y = y
    
    def distance(self, p: 'Point') -> float:
        return ((p.x - self.x) ** 2 + (p.y - self.y) ** 2) ** 0.5
    
    def islocked(self) -> bool:
        return self._locked
    
    def setlocked(self, locked: bool) -> None:
        self._locked = locked
    
    def next(self) -> 'Point':
        return self._next
    
    def prev(self) -> 'Point':
        return self._prev
    
    def __eq__(self, o: object) -> bool:
        if isinstance(o, Point):
            return self.x == o.x and self.y == o.y
        return False
    
    def to_dict(self) -> dict:
        return {
            "id": self._id,
            "x": self.x,
            "y": self.y,
            "locked": self._locked,
            "next": self._next._id if self._next is not None else None,
            "prev": self._prev._id if self._prev is not None else None
        }
    
    @staticmethod
    def _upgrade_data(data: dict) -> dict:
        _template = {"id": 0, "x": 0, "y": 0, "locked": False, "next": None, "prev": None}
        for k in _template:
            if k not in data:
                data[k] = _template[k]
                print(f"[INFO] Warning Point at {data.get('x', 'X-NotFound')}, {data.get('y', 'Y-NotFound')} is missing key [{k}, adding it to the memory copy")
        return data

    def __str__(self) -> str:
        return f"Point({self.x}, {self.y})"