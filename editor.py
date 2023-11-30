import ctypes
import pygame, os, cv2
from tkinter import filedialog
from collections import deque

from header.h_editor import h_Editor
from header.h_menubar import WM_COMMAND, WM_QUIT, WM_DESTROY
from helper.mutil import Util, Point, Origin, Rect
from gcode.p2code import GCode

from ui.menubar import MenuBar
from ui.component import Component
from ui.button import Button

"""
TODO
 - Add a way to change the origin
 - Add a way to change the point density
 - A way to set the next point
    - When you click a point it should show it's properties in the toolbar
      from there you should be able to click 'set next point' and then click
      the point you want to set it to
"""


class Editor(h_Editor):
    _running: bool
    _screen: pygame.Surface
    _point_size: float
    _selected_point: Point | None
    _hover_point: Point | None
    _grab_offset: tuple[int, int]
    _tool_components: list[Component]
    _hide_image: bool
    _editor_frame: pygame.Surface
    _tool_frame: pygame.Surface
    _hud_font: pygame.font.Font
    _origin: int
    _points: list[Point]
    _point_density: int
    _image: pygame.Surface | None
    _PPIN: int
    _undo_stack: deque[list[Point]]
    _redo_stack: deque[list[Point]]
    _menu_bar: MenuBar

    def __init__(self):
        super().__init__()

        # Screen Code ==================================
        self._running = True
        self._screen = pygame.display.set_mode((1200, 800))  # pygame.RESIZABLE
        self._point_size = 3.5
        self._selected_point = None
        self._hover_point = None
        self._grab_offset = (0, 0)
        self._tool_components: list[Component] = []
        self._hide_image = False
        self._undo_stack = deque(maxlen=1000)
        self._redo_stack = deque(maxlen=1000)
        self._editor_frame = pygame.Surface((self._screen.get_width() - 200, self._screen.get_height()))
        self._tool_frame = pygame.Surface((200, self._screen.get_height()))
        self._hud_font = pygame.font.SysFont("Arial", 20)
        self._bounds: Rect = Rect(0, 0, 0, 0)

        self._setup_toolbar()
        self._setup_menubar()

        # Machine Config ===============================
        self._origin = Origin.CENTER

        # Actual Path Code =============================
        self._PPIN = 50  # Pixels per Inch (for converting to gcode mostly)
        self._points: list[Point] = []
        self._point_density = 10
        self._image = None

        # Util =========================================
        Util._editor = self

        # Callback for calculating bounds (running this every frame is a bit much)
        Util.set_interval(
            lambda: setattr(self, "_bounds", Util.calculate_bounds(self._points).scale(1 / self._PPIN).round(3)) if len(self._points) > 2 else None
        ,1)
    
    def _draw(self) -> None:
        self._editor_frame.fill((255, 255, 255))

        # Draw Editor Frame ============================
        if self._image and not self._hide_image:
            self._editor_frame.blit(self._image, (self._editor_frame.get_width() / 2 - self._image.get_width() / 2, self._editor_frame.get_height() / 2 - self._image.get_height() / 2))

            # draw a frame around the image
            pygame.draw.rect(self._editor_frame, (255, 0, 0), (self._editor_frame.get_width() / 2 - self._image.get_width() / 2, self._editor_frame.get_height() / 2 - self._image.get_height() / 2, self._image.get_width(), self._image.get_height()), 2)

        for p in self._points:
            sizeMod = 1 if p != self._hover_point else 2
            pygame.draw.circle(self._editor_frame, (0, 0, 0), (p.x, p.y), self._point_size * sizeMod)

        # draw connecting lines
        for p in self._points:
            if p.next():
                pygame.draw.line(self._editor_frame, (0, 0, 0), (p.x, p.y), (p.next().x, p.next().y))

        # Tool Frame ===================================
        for c in self._tool_components:
            c.draw(self._tool_frame)

        # Draw HUD =====================================
        text = self._hud_font.render(f"Mouse: {self._calculate_machine_pos(Point(pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1]))}", True, (0, 0, 0))
        self._editor_frame.blit(text, (10, 0))

        if self._hover_point:
            text = self._hud_font.render(f"Hover: {self._calculate_machine_pos(self._hover_point)}", True, (0, 0, 0))
            self._editor_frame.blit(text, (10, 20))

        # draw the bounds
        if self._image and not self._hide_image:
            text = self._hud_font.render(f"{round(self._bounds.w, 3)}in", True, (0, 0, 0))
            # draw it in the middle horizontally, and at the bottom vertically + 10 pixels
            self._editor_frame.blit(text, (self._editor_frame.get_width() / 2 - text.get_width() / 2, self._editor_frame.get_height() / 2 + self._image.get_height() / 2 + 10))
            # draw a line from either side of the text to the end of the image and then draw a '|' at the end of each line
            pygame.draw.line(self._editor_frame, (0, 0, 0), (self._editor_frame.get_width() / 2 - text.get_width() / 2 - 10, self._editor_frame.get_height() / 2 + self._image.get_height() / 2 + 10 + text.get_height() / 2), (self._editor_frame.get_width() / 2 - self._image.get_width() / 2, self._editor_frame.get_height() / 2 + self._image.get_height() / 2 + 10 + text.get_height() / 2))
            pygame.draw.line(self._editor_frame, (0, 0, 0), (self._editor_frame.get_width() / 2 + text.get_width() / 2 + 10, self._editor_frame.get_height() / 2 + self._image.get_height() / 2 + 10 + text.get_height() / 2), (self._editor_frame.get_width() / 2 + self._image.get_width() / 2, self._editor_frame.get_height() / 2 + self._image.get_height() / 2 + 10 + text.get_height() / 2))
            pygame.draw.line(self._editor_frame, (0, 0, 0), (self._editor_frame.get_width() / 2 - self._image.get_width() / 2, self._editor_frame.get_height() / 2 + self._image.get_height() / 2 + 10 + text.get_height() / 2 - 5), (self._editor_frame.get_width() / 2 - self._image.get_width() / 2, self._editor_frame.get_height() / 2 + self._image.get_height() / 2 + 10 + text.get_height() / 2 + 5))
            pygame.draw.line(self._editor_frame, (0, 0, 0), (self._editor_frame.get_width() / 2 + self._image.get_width() / 2, self._editor_frame.get_height() / 2 + self._image.get_height() / 2 + 10 + text.get_height() / 2 - 5), (self._editor_frame.get_width() / 2 + self._image.get_width() / 2, self._editor_frame.get_height() / 2 + self._image.get_height() / 2 + 10 + text.get_height() / 2 + 5))

            # now do the same thing for the height
            text = self._hud_font.render(f"{round(self._bounds.h, 3)}in", True, (0, 0, 0))
            text = pygame.transform.rotate(text, 90)
            # draw it in the middle vertically, and at the right horizontally + 10 pixels
            self._editor_frame.blit(text, (self._editor_frame.get_width() / 2 + self._image.get_width() / 2 + 10, self._editor_frame.get_height() / 2 - text.get_height() / 2))
            # draw a line from either side of the text to the end of the image and then draw a '|' at the end of each line
            pygame.draw.line(self._editor_frame, (0, 0, 0), (self._editor_frame.get_width() / 2 + self._image.get_width() / 2 + 10 + text.get_width() / 2, self._editor_frame.get_height() / 2 - text.get_height() / 2 - 10), (self._editor_frame.get_width() / 2 + self._image.get_width() / 2 + 10 + text.get_width() / 2, self._editor_frame.get_height() / 2 - self._image.get_height() / 2))
            pygame.draw.line(self._editor_frame, (0, 0, 0), (self._editor_frame.get_width() / 2 + self._image.get_width() / 2 + 10 + text.get_width() / 2, self._editor_frame.get_height() / 2 + text.get_height() / 2 + 10), (self._editor_frame.get_width() / 2 + self._image.get_width() / 2 + 10 + text.get_width() / 2, self._editor_frame.get_height() / 2 + self._image.get_height() / 2))
            pygame.draw.line(self._editor_frame, (0, 0, 0), (self._editor_frame.get_width() / 2 + self._image.get_width() / 2 + 10 + text.get_width() / 2 - 5, self._editor_frame.get_height() / 2 - self._image.get_height() / 2), (self._editor_frame.get_width() / 2 + self._image.get_width() / 2 + 10 + text.get_width() / 2 + 5, self._editor_frame.get_height() / 2 - self._image.get_height() / 2))
            pygame.draw.line(self._editor_frame, (0, 0, 0), (self._editor_frame.get_width() / 2 + self._image.get_width() / 2 + 10 + text.get_width() / 2 - 5, self._editor_frame.get_height() / 2 + self._image.get_height() / 2), (self._editor_frame.get_width() / 2 + self._image.get_width() / 2 + 10 + text.get_width() / 2 + 5, self._editor_frame.get_height() / 2 + self._image.get_height() / 2))

        self._screen.blit(self._editor_frame, (0, 0))
        self._screen.blit(self._tool_frame, (self._screen.get_width() - 200, 0))

    def _keybind_open_image(self) -> None:
        path = filedialog.askopenfilename(initialdir=os.getcwd(), title="Select Image", filetypes=(("jpeg files", "*.jpg"), ("png files", "*.png"), ("all files", "*.*")))
        if path:
            img = cv2.imread(path)
            self._image = pygame.image.load(path)
            Util.async_task((
                lambda: setattr(self, "_points", Util.get_path_points(img, self._point_density, (self._editor_frame.get_width() / 2 - self._image.get_width() / 2, self._editor_frame.get_height() / 2 - self._image.get_height() / 2))),
                lambda: setattr(self, "_points", Util.clean_points(self._points)),
                lambda: setattr(self, "_points", Util.connect_points(self._points))
            ))

    """
    Calculate the position of the mouse relative to the machine's origin
    """
    def _calculate_machine_pos(self, p: 'Point') -> tuple[int, int]:
        if self._origin == Origin.CENTER:
            return (p.x - self._editor_frame.get_width() / 2, p.y - self._editor_frame.get_height() / 2)

    def _setup_menubar(self) -> None:
        hwnd = pygame.display.get_wm_info()['window']
        menu_definition = [
        {'text': 'File', 'id': 101, 'sub_menu': [
            {'text': 'Open', 'id': 201},
            {'text': 'Save', 'id': 202},
            {'separator': True},
            {'text': 'Exit', 'id': 203}
        ]},
        {'text': 'Edit', 'id': 102, 'sub_menu': [
            {'text': 'Copy', 'id': 301},
            {'text': 'Paste', 'id': 302}
        ]}
        # Add more menu items/submenus as needed
    ]
        
        self._menu_bar = MenuBar(hwnd)
        self._menu_bar.create_menu(menu_definition)
    
    def _setup_toolbar(self) -> None:
        self._tool_components.append(_GCodeButton := Button(location=(10, 10), size=(180, 30), text="Get GCODE", font=self._hud_font,
                                            callback=lambda: GCode.generate_gcode(self._points, self._image.get_size(), self._origin),
                                            true_conversion=lambda x, y: (x - self._screen.get_width() + 200, y)))
        _GCodeButton.draw = Util.wrap_function(_GCodeButton.draw, lambda: _GCodeButton.set_disabled(len(self._points) < 2), 'pre')

        self._tool_components.append(_ConnectPointsButton := Button(location=(10, 50), size=(180, 30), text="Recalc Path", font=self._hud_font,
                                            callback=lambda: setattr(self, "_points", Util.connect_points(self._points)),
                                            true_conversion=lambda x, y: (x - self._screen.get_width() + 200, y)))
        _ConnectPointsButton.draw = Util.wrap_function(_ConnectPointsButton.draw, lambda: _ConnectPointsButton.set_disabled(len(self._points) < 2), 'pre')


    def run(self) -> None:
        # event code needs to be moved over to ctypes because pygame drains the message queue before we can get to it
        while self._running:
            for event in pygame.event.get():
                Util.apply([x.event for x in self._tool_components], event=event)

                # Window events ==============================
                if event.type == pygame.QUIT:
                    self._running = False
                elif event.type == pygame.VIDEORESIZE:
                    self._screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

                # Handle mouse events ========================
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1: # left click
                        for p in self._points:
                            if abs(p.x - event.pos[0]) < self._point_size and abs(p.y - event.pos[1]) < self._point_size:
                                self._selected_point = p
                                self._grab_offset = (p.x - event.pos[0], p.y - event.pos[1])
                                self._undo_stack.append({'action': 'move', 'old': (p.x, p.y), 'point': p})
                                break
                    elif event.button == 3 and not self._selected_point and self._image and not self._hide_image:
                        self._points.append(Point(event.pos[0], event.pos[1]))
                        self._undo_stack.append({'action': 'add', 'point': self._points[-1]})

                elif event.type == pygame.MOUSEBUTTONUP:
                    self._selected_point = None
                elif event.type == pygame.MOUSEMOTION:
                    if self._selected_point:
                        self._selected_point.set_pos(event.pos[0] + self._grab_offset[0], event.pos[1] + self._grab_offset[1])
                    else:
                        for p in self._points:
                            if abs(p.x - event.pos[0]) < self._point_size and abs(p.y - event.pos[1]) < self._point_size:
                                self._hover_point = p
                                break
                            else:
                                self._hover_point = None

                # Keybinds ===================================
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_o and pygame.key.get_mods() & pygame.KMOD_CTRL:
                        self._keybind_open_image()

                    elif event.key == pygame.K_z and pygame.key.get_mods() & pygame.KMOD_CTRL and pygame.key.get_mods() & pygame.KMOD_SHIFT:
                        if len(self._redo_stack) > 0:
                            action = self._redo_stack.pop()
                            self._undo_stack.append(action)
                            if action['action'] == 'add':
                                self._points.append(action['point'])
                            elif action['action'] == 'move':
                                action['point'].set_pos(action['old'][0], action['old'][1])
                            
                    elif event.key == pygame.K_z and pygame.key.get_mods() & pygame.KMOD_CTRL:
                        if len(self._undo_stack) > 0:
                            action = self._undo_stack.pop()
                            self._redo_stack.append(action)
                            if action['action'] == 'add':
                                self._points.remove(action['point'])
                            elif action['action'] == 'move':
                                action['point'].set_pos(action['old'][0], action['old'][1])

                    elif event.key == pygame.K_l:
                        self._hide_image = not self._hide_image


            self._draw()
            pygame.display.flip()

        pygame.quit()



                
if __name__ == "__main__":
    pygame.init()
    pygame.display.set_caption("Path Editor")
    editor = Editor()
    editor.run()