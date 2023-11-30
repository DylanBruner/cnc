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
 - make the menubar actually do things
 - saving and loading a project (contains image, points, origin, point density)
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
        self._screen.fill((255, 255, 255))
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
        }

        for i, (k, v) in enumerate(hud.items()):
            if v:
                text = self._hud_font.render(f"{k}: {v}", True, (0, 0, 0))
                self._screen.blit(text, (10, 20 + (i-1) * 20))

    def _keybind_open_image(self) -> None:
        self._image_path = filedialog.askopenfilename(initialdir=os.getcwd(), title="Select Image", filetypes=(("pictures", "*.png *.jpg *.jpeg *.bmp"), ("all files", "*.*")))
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

                if self._selected_point:
                    self._selected_point.set_pos(self._evaluated_mouse_pos[0] + self._grab_offset[0], self._evaluated_mouse_pos[1] + self._grab_offset[1])
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
                    for p in self._points:
                        if abs(p.x - self._evaluated_mouse_pos[0]) < self._point_size and abs(p.y - self._evaluated_mouse_pos[1]) < self._point_size:
                            self._selected_point = p
                            self._grab_offset = (p.x - self._evaluated_mouse_pos[0], p.y - self._evaluated_mouse_pos[1])
                            self._undo_stack.append({'action': 'move', 'old': (p.x, p.y), 'point': p})
                            break
                    else:
                        if not self._dragging:
                            self._last_mouse_pos = (pygame.mouse.get_pos()[0] - self._zoom_focus[0]) / self._zoom_level + self._zoom_focus[0], (pygame.mouse.get_pos()[1] - self._zoom_focus[1]) / self._zoom_level + self._zoom_focus[1]
                            self._dragging = True

                elif msg.wParam == 2: # right click
                    # TODO: Fix this
                    pos = pygame.mouse.get_pos()
                    if not self._selected_point and self._image and not self._hide_image:
                        self._points.append(Point(pos[0], pos[1]))
                        self._undo_stack.append({'action': 'add', 'point': self._points[-1]})

            elif msg.message == 514: # left click up
                self._selected_point = None
                self._dragging = False
            
            elif msg.message == 517: # right click up
                ...

            elif msg.message == 256: # Key Down
                self._pressed_keys[msg.wParam] = True
                if msg.wParam == 79 and self._pressed_keys.get(17, False): # Ctrl + O
                    self._keybind_open_image()

                elif msg.wParam == 90 and self._pressed_keys.get(17, False) and self._pressed_keys.get(16, False):
                    if len(self._redo_stack) > 0:
                        action = self._redo_stack.pop()
                        self._undo_stack.append(action)
                        if action['action'] == 'add':
                            self._points.append(action['point'])
                        elif action['action'] == 'move':
                            action['point'].set_pos(action['old'][0], action['old'][1])

                elif msg.wParam == 90 and self._pressed_keys.get(17, False): # Ctrl + Z
                    if len(self._undo_stack) > 0:
                        action = self._undo_stack.pop()
                        self._redo_stack.append(action)
                        if action['action'] == 'add':
                            self._points.remove(action['point'])
                        elif action['action'] == 'move':
                            action['point'].set_pos(action['old'][0], action['old'][1])

                elif msg.wParam == 76: # L
                    self._hide_image = not self._hide_image
                
                elif msg.wParam == 67: # C
                    self._zoom_focus = (self._editor_frame.get_width() / 2, self._editor_frame.get_height() / 2)
                    self._zoom_level = 1
                
                elif msg.wParam == 70: # F
                    if debugpy.is_client_connected():
                        debugpy.breakpoint()
                    else:
                        print("Debugger not connected")

            elif msg.message == 257: # Key Up
                self._pressed_keys[msg.wParam] = False

            elif msg.message == 275: # corse scroll
                direction = ctypes.c_int16(msg.wParam).value
            
            elif msg.message == 522: # fine scroll
                direction = -1 if 420_000_000_0 > msg.wParam else 1 # TODO: this line is bad fix it later
                self._zoom_level = min(max(self._zoom_level + (direction * 0.2), 1), 5)

            else:
                pass
                # print(msg.message, msg.wParam, msg.lParam)

            self._draw()
            pygame.display.flip()

        pygame.quit()



                
if __name__ == "__main__":
    pygame.init()
    pygame.display.set_caption("Path Editor")
    editor = Editor()
    editor.run()