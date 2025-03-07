import pygame, os, cv2, ctypes, ctypes.wintypes, debugpy, json
from tkinter import filedialog
from collections import deque

from header.h_editor import h_Editor
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
 - more controls in the toolbar
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
        self._last_point: Point = None
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
        self._pressed_keys = {}
        self._zoom_level = 1
        self._zoom_focus = (self._editor_frame.get_width() / 2, self._editor_frame.get_height() / 2)
        self._dragging = False
        self._last_mouse_pos = (0, 0)
        self._clock = pygame.time.Clock()
        self._evaluated_mouse_pos: tuple[float, float] = None
        self._image_path: str = None
        self._open_project: str = None
        self._saved: bool = True
        self._connect_mode: bool = False
        self._highlight_points: list[tuple[Point, tuple[int, int, int]]] = []
        self._current_conection_id = 0

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
        , 1)
    
    def _draw(self) -> None:
        self._screen.fill((255, 255, 255))
        self._editor_frame.fill((255, 255, 255))

        # Draw Editor Frame ============================
        if self._image and not self._hide_image:
            self._editor_frame.blit(self._image, (self._editor_frame.get_width() / 2 - self._image.get_width() / 2, self._editor_frame.get_height() / 2 - self._image.get_height() / 2))

            # draw a frame around the image
            pygame.draw.rect(self._editor_frame, (255, 0, 0), (self._editor_frame.get_width() / 2 - self._image.get_width() / 2, self._editor_frame.get_height() / 2 - self._image.get_height() / 2, self._image.get_width(), self._image.get_height()), 2)

        for i, p in enumerate(self._points):
            sizeMod = 1 if p != self._hover_point else 1.2 if p == self._selected_point else 1.2

            if p in [x[0] for x in self._highlight_points]:
                color = [x[1] for x in self._highlight_points if x[0] == p][0]
            elif p._locked:
                color = (255, 0, 0)
            elif p == self._selected_point:
                color = (0, 0, 255) if not self._connect_mode else (255, 255, 0)
            elif i == 0:
                color = (0, 0, 255)
            elif i == len(self._points) - 1:
                color = (255, 0, 0)
            elif p._id == -1:
                color = (255, 0, 0)
            else:
                color = (0, 255, 0)

            pygame.draw.circle(self._editor_frame, color, (p.x, p.y), self._point_size * sizeMod)

        # draw connecting lines
        for p in self._points:
            if p.next():
                color = (255, 0, 0) if p._locked and p.next()._locked else (0, 0, 0)
                pygame.draw.line(self._editor_frame, color, (p.x, p.y), (p.next().x, p.next().y))

        # Tool Frame ===================================
        for c in self._tool_components:
            c.draw(self._tool_frame)



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


        Util.zoom_at_pos(self._editor_frame, self._zoom_focus, self._zoom_level)

        self._screen.blit(self._editor_frame, (0, 0))
        self._screen.blit(self._tool_frame, (self._screen.get_width() - 200, 0))

        # Draw HUD =====================================
        hud = {
            "Mouse": self._calculate_machine_pos(Point(pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1])),
            "Point Density": self._point_density,
            "FPS": round(self._clock.get_fps()),
            "Point ID": self._hover_point._id if self._hover_point else None,
        }

        for i, (k, v) in enumerate(hud.items()):
            if v:
                text = self._hud_font.render(f"{k}: {v}", True, (0, 0, 0))
                self._screen.blit(text, (10, 20 + (i-1) * 20))

    def _keybind_open(self) -> None:
        path = filedialog.askopenfilename(initialdir=os.getcwd(), title="Select Image", filetypes=(("project/picture", "*.cncproj *.png *.jpg *.jpeg *.bmp"), ("all files", "*.*")))
        if not path.endswith(".cncproj"):
            self._image_path = path
            self._load_image()
        
        else:
            self._load_project(path)

    def _btn_validate_path(self) -> None:
        if len(self._highlight_points) > 0:
            self._highlight_points = []
            return
        
        error_points = GCode.validate_path(self._points)
        self._highlight_points = [(p, (255, 0, 0)) for p in error_points]

    def _load_image(self) -> None:
        if self._image_path:
            img = cv2.imread(self._image_path)
            self._image = pygame.image.load(self._image_path)
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
            {'text': 'Open', 'id': 201, 'callback': self._keybind_open},
            {'text': 'Save Project', 'id': 202, 'callback': lambda: self._keybind_save(False)},
            {'text': 'Save Project As', 'id': 203, 'callback': lambda: self._keybind_save(True)},
            {'separator': True},
            {'text': 'Exit', 'id': 204, 'callback': lambda: setattr(self, "_running", False)}
        ]},
        {'text': 'Edit', 'id': 102, 'sub_menu': [
            {'text': 'Undo', 'id': 301, 'callback': self._undo},
            {'text': 'Redo', 'id': 302, 'callback': self._redo}
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

        self._tool_components.append(_ConnectModeButton := Button(location=(10, 90), size=(180, 30), text="Connect Mode", font=self._hud_font,
                                            callback=lambda: setattr(self, "_connect_mode", not self._connect_mode),
                                            true_conversion=lambda x, y: (x - self._screen.get_width() + 200, y)))
        _ConnectModeButton.draw = Util.wrap_function(_ConnectModeButton.draw, lambda: (_ConnectModeButton.set_text("Connect Mode" + (" (ON)" if self._connect_mode else " (OFF)")), 
                                                                                       _ConnectModeButton.set_disabled(len(self._points) < 2)), 'pre')
        
        self._tool_components.append(_ValidatePathButton := Button(location=(10, 130), size=(180, 30), text="Validate Path", font=self._hud_font,
                                            callback=lambda: self._btn_validate_path(),
                                            true_conversion=lambda x, y: (x - self._screen.get_width() + 200, y)))
        _ValidatePathButton.draw = Util.wrap_function(_ValidatePathButton.draw, lambda: _ValidatePathButton.set_disabled(len(self._points) < 2), 'pre')

        self._tool_components.append(_HideImageButton := Button(location=(10, 170), size=(180, 30), text="Hide Image", font=self._hud_font,
                                            callback=lambda: setattr(self, "_hide_image", not self._hide_image),
                                            true_conversion=lambda x, y: (x - self._screen.get_width() + 200, y)))
        _HideImageButton.draw = Util.wrap_function(_HideImageButton.draw, lambda: _HideImageButton.set_text("Hide Image" + (" (ON)" if self._hide_image else " (OFF)")), 'pre')

        self._tool_components.append(_ClearnConnectionsButton := Button(location=(10, 210), size=(180, 30), text="Clear Connections", font=self._hud_font,
                                                                        callback=lambda: Util.reconnect_points(self._points),
                                                                        true_conversion=lambda x, y: (x - self._screen.get_width() + 200, y)))
        _ClearnConnectionsButton.draw = Util.wrap_function(_ClearnConnectionsButton.draw, lambda: _ClearnConnectionsButton.set_disabled(len(self._points) < 2), 'pre')

        self._tool_components.append(_ClearPointMetaDataButton := Button(location=(10, 250), size=(180, 30), text="Clear Point MetaData", font=self._hud_font,
                                                                        callback=lambda: Util.clear_point_metadata(self._points),
                                                                        true_conversion=lambda x, y: (x - self._screen.get_width() + 200, y)))
        _ClearPointMetaDataButton.draw = Util.wrap_function(_ClearPointMetaDataButton.draw, lambda: _ClearPointMetaDataButton.set_disabled(len(self._points) < 2), 'pre')

    
    # TODO: test this
    def _save_project(self, path: str) -> None:
        with open(path, 'w') as f:
            f.write(json.dumps({
                'points': [p.to_dict() for p in self._points],
                'origin': self._origin,
                'point_density': self._point_density,
                'image_path': self._image_path
            }))
    
    # TODO: test this
    def _load_project(self, path: str) -> None:
        with open(path, 'r') as f:
            data = json.loads(f.read())
            self._points = [Point.from_dict(p) for p in data['points']]
            Util.reconnect_points(self._points)
            self._origin = data['origin']
            self._point_density = data['point_density']
            self._image_path = data['image_path']
            self._image = pygame.image.load(self._image_path)
            self._open_project = path

    def _keybind_save(self, save_as: bool) -> None:
        if save_as or not self._open_project:
            path = filedialog.asksaveasfilename(initialdir=os.getcwd(), title="Save Project", filetypes=(("project", "*.cncproj"), ("all files", "*.*")))
            if path:
                self._save_project(path)
                self._open_project = path
        else:
            print("saving to", self._open_project)
            self._save_project(self._open_project)
        self._saved = True

    def _undo(self) -> None:
        if len(self._undo_stack) > 0:
            action = self._undo_stack.pop()
            self._redo_stack.append(action)
            if action['action'] == 'add':
                self._points.remove(action['point'])
            elif action['action'] == 'move':
                action['point'].set_pos(action['old'][0], action['old'][1])
            elif action['action'] == 'remove':
                self._points.append(action['point'])
            elif action['action'] == 'lock':
                action['point']._locked = not action['point']._locked

    def _redo(self) -> None:
        if len(self._redo_stack) > 0:
            action = self._redo_stack.pop()
            self._undo_stack.append(action)
            if action['action'] == 'add':
                self._points.append(action['point'])
            elif action['action'] == 'move':
                action['point'].set_pos(action['old'][0], action['old'][1])

    def run(self) -> None:
        # event code needs to be moved over to ctypes because pygame drains the message queue before we can get to it

        while self._running:
            self._clock.tick(60)

            msg = ctypes.wintypes.MSG()
            ret = ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0)

            ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
            ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))

            self._draw()

            self._menu_bar.handle_message(msg)
            Util.apply([x.event for x in self._tool_components], event=msg)

            # Window events ==============================
            if msg.message == 161: # Seems to be interaction with the windowbar
                if msg.wParam == 20: # 'X' button
                    self._running = False
                elif msg.wParam == 8: ... # minimize

            elif msg.message == 512: # Mouse Motion
                # account for zoom in pos using focus_point and zoom_level
                old = (pygame.mouse.get_pos()[0] - self._zoom_focus[0]) / self._zoom_level + self._zoom_focus[0], (pygame.mouse.get_pos()[1] - self._zoom_focus[1]) / self._zoom_level + self._zoom_focus[1]
                self._evaluated_mouse_pos = Util.get_zoomed_mouse_pos(pygame.mouse.get_pos(), self._zoom_level)

                if self._selected_point and not self._connect_mode:
                    self._selected_point.set_pos(self._evaluated_mouse_pos[0] + self._grab_offset[0], self._evaluated_mouse_pos[1] + self._grab_offset[1])
                    self._saved = False
                elif self._dragging:
                    dX, dY = old[0] - self._last_mouse_pos[0], old[1] - self._last_mouse_pos[1]
                    self._last_mouse_pos = old
                    self._zoom_focus = (self._zoom_focus[0] - dX, self._zoom_focus[1] - dY)
                else:
                    for p in self._points:
                        if abs(p.x - self._evaluated_mouse_pos[0]) < self._point_size and abs(p.y - self._evaluated_mouse_pos[1]) < self._point_size:
                            self._hover_point = p
                            break
                        else:
                            self._hover_point = None
            
            elif msg.message == 513: # Mouse Button Down
                if msg.wParam == 1:
                    canDrag = True
                    pointFound = False
                    for p in self._points:
                        if abs(p.x - self._evaluated_mouse_pos[0]) < self._point_size and abs(p.y - self._evaluated_mouse_pos[1]) < self._point_size:
                            pointFound = True
                            if not p._locked and not self._connect_mode:
                                self._selected_point = p
                                self._grab_offset = (p.x - self._evaluated_mouse_pos[0], p.y - self._evaluated_mouse_pos[1])
                                self._undo_stack.append({'action': 'move', 'old': (p.x, p.y), 'point': p})
                                self._saved = False
                                canDrag = False

                            if not p._locked and self._connect_mode:
                                if self._selected_point is not None and self._selected_point != p:
                                    self._selected_point._id = self._current_conection_id
                                    print(f"[INFO] Set point's ID to {self._selected_point._id}/{self._current_conection_id}")
                                    self._current_conection_id += 1
                                    self._saved = False
                                    self._points = Util.connect_points(self._points)
                                self._selected_point = p
                                self._last_point = p
                    
                    if not pointFound:
                        self._selected_point = None

                    if not self._dragging and canDrag:
                        self._last_mouse_pos = (pygame.mouse.get_pos()[0] - self._zoom_focus[0]) / self._zoom_level + self._zoom_focus[0], (pygame.mouse.get_pos()[1] - self._zoom_focus[1]) / self._zoom_level + self._zoom_focus[1]
                        self._dragging = True

            elif msg.message == 514: # left click up
                if not self._connect_mode:
                    self._selected_point = None
                self._dragging = False
            
            elif msg.message == 516: # right click down
                if not self._selected_point and self._image and not self._hide_image and not self._connect_mode:
                    self._points.append(Point(self._evaluated_mouse_pos[0], self._evaluated_mouse_pos[1]))
                    self._undo_stack.append({'action': 'add', 'point': self._points[-1]})
                    self._saved = False
                
                elif self._connect_mode and self._hover_point:
                    self._hover_point._next = None
                    self._saved = False

            elif msg.message == 517: # right click up
                ...

            elif msg.message == 256: # Key Down
                self._pressed_keys[msg.wParam] = True
                if msg.wParam == 79 and self._pressed_keys.get(17, False): # Ctrl + O
                    self._keybind_open()

                elif msg.wParam == 90 and self._pressed_keys.get(17, False) and self._pressed_keys.get(16, False): # Ctrl + Shift + Z
                    self._redo()

                elif msg.wParam == 90 and self._pressed_keys.get(17, False): # Ctrl + Z
                    self._undo()

                elif msg.wParam == 83 and self._pressed_keys.get(17, False): # Ctrl + S
                    self._keybind_save(False)
                
                elif msg.wParam == 83 and self._pressed_keys.get(17, False) and self._pressed_keys.get(16, False): # Ctrl + Shift + S
                    self._keybind_save(True)


                elif msg.wParam == 76: # L
                    if self._hover_point is not None:
                        self._hover_point._locked = not self._hover_point._locked
                        self._saved = False
                        self._undo_stack.append({'action': 'lock', 'point': self._hover_point})
                
                elif msg.wParam == 67: # C
                    self._zoom_focus = (self._editor_frame.get_width() / 2, self._editor_frame.get_height() / 2)
                    self._zoom_level = 1
                
                elif msg.wParam == 70: # F
                    if debugpy.is_client_connected():
                        debugpy.breakpoint()
                    else:
                        print("Debugger not connected")

                elif msg.wParam == 46: # Delete
                    if self._hover_point:
                        self._undo_stack.append({'action': 'remove', 'point': self._hover_point})
                        self._points.remove(self._hover_point)
                        self._hover_point = None
                        self._saved = False

            elif msg.message == 257: # Key Up
                self._pressed_keys[msg.wParam] = False

            elif msg.message == 275: # corse scroll
                direction = ctypes.c_int16(msg.wParam).value
            
            elif msg.message == 522: # fine scroll
                direction = -1 if 420_000_000_0 > msg.wParam else 1 # TODO: this line is bad fix it later
                self._zoom_level = min(max(self._zoom_level + (direction * 0.2), 1), 5)

            elif msg.message == 258: # num-key 8/2 basically up/down
                if msg.wParam == 56:
                    self._current_conection_id += 1
                    print(f"[INFO] Current Connection ID: {self._current_conection_id}")
                elif msg.wParam == 50:
                    self._current_conection_id -= 1
                    print(f"[INFO] Current Connection ID: {self._current_conection_id}")

            else:
                pass
                # print(msg.message, msg.wParam, msg.lParam)

            if not self._saved:
                pygame.display.set_caption(f"Path Editor - [{self._open_project if self._open_project else 'Untitled'}*]")
            else:
                pygame.display.set_caption(f"Path Editor - [{self._open_project if self._open_project else 'Untitled'}]")

            self._draw()
            pygame.display.flip()

        pygame.quit()



                
if __name__ == "__main__":
    pygame.init()
    pygame.display.set_caption("Path Editor")
    editor = Editor()
    editor.run()