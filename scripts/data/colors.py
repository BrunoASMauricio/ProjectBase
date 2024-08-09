from enum import Enum
from colorama import Fore, Style

class Colors(Enum):
    Red = 1
    Blue = 2
    Yellow = 3
    Green = 4
    Cyan = 5
    Magenta = 6

ColorDict = {
    Colors.Red: Fore.RED,
    Colors.Blue: Fore.BLUE,
    Colors.Yellow: Fore.YELLOW,
    Colors.Green: Fore.GREEN,
    Colors.Cyan: Fore.CYAN,
    Colors.Magenta: Fore.MAGENTA
}

def ColorFormat(Color, Message):
    return ColorDict[Color] + str(Message) + Style.RESET_ALL
