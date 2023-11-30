import pygame

try:
    from h_class import HeaderClass
    from h_point import h_Point
except ImportError:
    from header.h_class import HeaderClass
    from header.h_point import h_Point

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

    _origin: int

    _points: list[h_Point]
    _point_density: int
    _image: pygame.Surface | None

    def __init__(self):
        super().__init__(h_Editor)

    def _draw(self) -> None: ...
    def _keybind_open_image(self) -> None: ...
    def _calculate_machine_pos(self, p: 'h_Point') -> tuple[int, int]: ...
    def _setup_toolbar(self) -> None: ...
    def run(self) -> None: ...