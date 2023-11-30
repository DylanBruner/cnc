import cv2, threading, pygame
from typing import Any, Callable
from dataclasses import dataclass

from header.h_editor import h_Editor
from header.h_point import h_Point


class Util:
    _editor: h_Editor = None

    @staticmethod
    def get_editor() -> h_Editor:
        if Util._editor is None:
            raise RuntimeError("Editor not initialized")
        return Util._editor

    @staticmethod
    def get_path_points(img, point_density: int, offset: tuple[int, int] = (0, 0)) -> list[tuple[int, int]]:
        path: list[Point] = []

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)

        # Find contours
        contours, hierarchy = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

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
        # start at the first point,
        # the next point will be the closest non-connected point prioritizing the points furthest away from the middle
        # repeat until all points are connected

        connected_points: list[Point] = []
        connected_points.append(points[0])
        points.remove(points[0])
        while len(points) > 0:
            closest_point = None
            closest_distance = 9999
            for p in points:
                if p.distance(connected_points[-1]) < closest_distance:
                    closest_point = p
                    closest_distance = p.distance(connected_points[-1])
            
                
            connected_points[-1]._next = closest_point
            closest_point._prev = connected_points[-1]
            connected_points.append(closest_point)
            points.remove(closest_point)
        return connected_points
    
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
    
class Origin:
    CENTER = 0

@dataclass
class Point(h_Point):
    x: int
    y: int
    _next: 'Point' = None
    _prev: 'Point' = None

    def set_pos(self, x: int, y: int) -> None:
        self.x = x
        self.y = y
    
    def distance(self, p: 'Point') -> float:
        return ((p.x - self.x) ** 2 + (p.y - self.y) ** 2) ** 0.5
    
    def next(self) -> 'Point':
        return self._next
    
    def prev(self) -> 'Point':
        return self._prev
    
    def __eq__(self, o: object) -> bool:
        if isinstance(o, Point):
            return self.x == o.x and self.y == o.y
        return False