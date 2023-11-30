from header.h_point import h_Point

try:
    from ..mutil import Origin, Util
except ImportError:
    from mutil import Origin, Util

class GCode:
    @staticmethod
    def generate_gcode(points: list[h_Point], size: tuple[float, float], origin: int) -> None:
        if origin not in [Origin.CENTER]:
            raise ValueError("Invalid Origin")
        
        translated: list[float, float] = []
        for p in points:
            translated.append((p.x - size[0] / 2, p.y - size[1] / 2))

        code = ""

        for p in points:
            index = points.index(p)
            # round to three decimal places, if the number is a integer add a decimal point
            x = str(round(translated[index][0], 3))
            if x[-2:] == ".0":
                x = x[:-2] + "." + x[-1]
            y = str(round(translated[index][1], 3))
            if y[-2:] == ".0":
                y = y[:-2] + "." + y[-1]
            code += f"G1 X{x} Y{y}\n"
        
        Util._async(lambda: Util.open_notepad_with(code))