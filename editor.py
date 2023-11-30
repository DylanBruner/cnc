import pygame, os, cv2
from tkinter import filedialog

from header.h_editor import h_Editor
from mutil import Util, Point, Origin
from ui.component import Component
from ui.button import Button

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

    def __init__(self):
        super().__init__()

        Util._editor = self

        # Screen Code ==================================
        self._running = True
        self._screen = pygame.display.set_mode((1200, 800), ) # pygame.RESIZABLE
        self._point_size = 3.5
        self._selected_point = None
        self._hover_point = None
        self._grab_offset = (0, 0)
        self._tool_components: list[Component] = []

        self._hide_image = False

        self._editor_frame = pygame.Surface((self._screen.get_width() - 200, self._screen.get_height()))
        self._tool_frame = pygame.Surface((200, self._screen.get_height()))

        self._hud_font = pygame.font.SysFont("Arial", 20)

        self._setup_toolbar()

        # Machine Config ===============================
        self._origin = Origin.CENTER

        # Actual Path Code =============================
        self._points: list[Point] = []
        self._point_density = 5
        self._image = None
    
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
            ))
            print("done")
    

    def _calculate_machine_pos(self, p: 'Point') -> tuple[int, int]:
        if self._origin == Origin.CENTER:
            return (p.x - self._editor_frame.get_width() / 2, p.y - self._editor_frame.get_height() / 2)
        
    
    def _setup_toolbar(self) -> None:
        self._tool_components.append(Button(location=(10, 10), size=(180, 30), text="Open Image", font=self._hud_font,
                                            callback=lambda: print("hi"),
                                            true_conversion=lambda x, y: (x - self._screen.get_width() + 200, y)))

    def run(self) -> None:
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
                    for p in self._points:
                        if abs(p.x - event.pos[0]) < self._point_size and abs(p.y - event.pos[1]) < self._point_size:
                            self._selected_point = p
                            self._grab_offset = (p.x - event.pos[0], p.y - event.pos[1])
                            break
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
                    if event.key == pygame.K_l:
                        self._hide_image = not self._hide_image
        
            self._draw()
            pygame.display.flip()

        pygame.quit()



                
if __name__ == "__main__":
    pygame.init()
    pygame.display.set_caption("Path Editor")
    editor = Editor()
    editor.run()