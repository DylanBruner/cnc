import pygame
from collections import deque

try:
    from h_class import HeaderClass
    from h_point import h_Point
    from h_menubar import h_MenuBar
    from ..ui.component import Component
    from ..ui.menubar import MenuBar
except ImportError:
    from header.h_class import HeaderClass
    from header.h_point import h_Point
    from header.h_menubar import h_MenuBar
    from ui.component import Component



class h_Editor(HeaderClass):
    _running: bool
    _screen: pygame.Surface
    _point_size: float
    _selected_point: h_Point | None
    _hover_point: h_Point | None
    _grab_offset: tuple[int, int]
    _tool_components: list[Component]

    _hide_image: bool

    _editor_frame: pygame.Surface
    _tool_frame: pygame.Surface

    _hud_font: pygame.font.Font
    _menu_bar: h_MenuBar

    _origin: int

    _points: list[h_Point]
    _point_density: int
    _image: pygame.Surface | None

    _PPIN: int
    _undo_stack: deque[list[h_Point]]
    _redo_stack: deque[list[h_Point]]

    def __init__(self):
        super().__init__(h_Editor)

    def _draw(self) -> None: ...
    def _keybind_open(self) -> None: ...
    def _calculate_machine_pos(self, p: 'h_Point') -> tuple[int, int]: ...
    def _setup_toolbar(self) -> None: ...
    def run(self) -> None: ...