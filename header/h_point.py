try:
    from h_class import HeaderClass
except ImportError:
    from header.h_class import HeaderClass

class h_Point(HeaderClass):
    x: int
    y: int
    _next: 'h_Point' = None
    _prev: 'h_Point' = None

    def set_pos(self, x: int, y: int) -> None:
        self.x = x
        self.y = y
    
    def distance(self, p: 'h_Point') -> float:
        return ((p.x - self.x) ** 2 + (p.y - self.y) ** 2) ** 0.5
    
    def next(self) -> 'h_Point':
        return self._next
    
    def prev(self) -> 'h_Point':
        return self._prev
    
    def __eq__(self, o: object) -> bool:
        if isinstance(o, h_Point):
            return self.x == o.x and self.y == o.y
        return False