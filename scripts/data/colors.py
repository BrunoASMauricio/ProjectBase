from enum import Enum
from colorama import Fore, Style

class Colors(Enum):
    Red = 1
    Blue = 2
    Yellow = 3
    Green = 4
    Cyan = 5
    Magenta = 6

color_dict = {
    Colors.Red: Fore.RED,
    Colors.Blue: Fore.BLUE,
    Colors.Yellow: Fore.YELLOW,
    Colors.Green: Fore.GREEN,
    Colors.Cyan: Fore.CYAN,
    Colors.Magenta: Fore.MAGENTA
}

def ColorFormat(color, message):
    return color_dict[color] + str(message) + Style.RESET_ALL
