import time
from typing import Tuple, Dict, Optional, List

import serial


class Braider:
    """A class to control the braider.

    The braider in this case is Ultimaker 3D printer with a magnet attached to the
    printhead. The magnet can be engaged and disengaged by moving the printhead along
    the z-axis. The magnet can be moved along the x and y axes by moving the printhead.

    The braider has a number of spools attached to it. The spools are assigned to letters
    on the keyboard. When a spool is grabbed, the printhead is moved to the spool and the
    magnet is engaged. When a spool is released, the printhead is moved to the spool and
    the magnet is disengaged.
    """
    def __init__(
            self,
            serial_connection: serial.Serial,
            width: float = 200,
            height: float = 200,
            engage_travel_distance: float = 15,
            spool_names: List[str] = ["R", "G", "B"]
         ):
        """
        Creates a new Braider instance.

        :param serial_connection: An open serial connection to the plotter.
        :param width: The width of braiding area in mm.
        :param height: The height of braiding area in mm.
        :param engage_travel_distance: How much to release the magnet when engaging it along the z-axis.
        :param spool_names: The names of the spools sitting on the braider.
        """
        self._ser = serial_connection
        self._width = width
        self._height = height
        self._engage_travel_distance = engage_travel_distance

        self._position: Tuple[float, float] = None
        self._magnet_is_engaged = None

        # The position of the spools is not known at the start ...
        self.spools: Dict[str, Optional[Tuple[float, float]]] = {
            spool_name: None for spool_name in spool_names
        }

        # ... and no spool is grabbed
        self._currently_grabbed_spool = None

        self.init()

    def init(self):
        # Set to absolute positioning
        self._ser.write(b'G90\n')
        self._wait_for_ok()

        # Set feed rate to something fast
        self._ser.write(b'G1 F5000\n')
        self._wait_for_ok()

        # Home magnet axes
        self._ser.write(b'G28 Z\n')
        self._wait_for_ok()

        # After homing the magnet is pulled all the way down, so it is not engaged
        self._magnet_is_engaged = False

        # Home X and Y axes
        self._ser.write(b'G28 X Y\n')
        self._wait_for_ok()

        # Reset mirror of plotter state
        self._position = (0, 0)

    def move_to(self, x: float, y: float):
        """Moves to the given position without leaving the bounds."""
        x, y = self._clip_position(x, y)
        self._ser.write(f'G1 X{x} Y{y}\n'.encode())
        self._wait_for_ok()
        self._position = (x, y)

    def move_to_relative(self, x: float, y: float):
        """Moves to the given position relative to the current position without leaving the bounds."""
        self.move_to(self._position[0] + x, self._position[1] + y)

    def move_left(self, distance: float = 1):
        self.move_to_relative(-distance, 0)

    def move_right(self, distance: float = 1):
        self.move_to_relative(distance, 0)

    def move_up(self, distance: float = 1):
        self.move_to_relative(0, distance)

    def move_down(self, distance: float = 1):
        self.move_to_relative(0, -distance)

    def beep(self, frequency: float = 440, duration: float = 200):
        self._ser.write(f'M300 S{frequency} P{duration}\n'.encode())
        self._wait_for_ok()
        time.sleep(duration / 1000)

    @property
    def position(self) -> Tuple[float, float]:
        return self._position

    @property
    def width(self) -> float:
        return self._width

    @property
    def height(self) -> float:
        return self._height

    def _wait_for_ok(self):
        response = ""
        while response != "ok":
            response = self._ser.readline().decode().strip()

    def _clip_position(self, x: float, y: float):
        return max(0, min(self._width, x)), max(0, min(self._height, y))

    def engage_magnet(self):
        """Engages the magnet by releasing it up by the engage travel distance."""
        if not self._magnet_is_engaged:
            print("Enabling Magnet")
            self._ser.write(f'G1 Z{self._engage_travel_distance}\n'.encode())
            self._wait_for_ok()
            self._magnet_is_engaged = True

    def disengage_magnet(self):
        """Disengages the magnet by pulling it down by homing the Z axis."""
        if self._magnet_is_engaged:
            print("Disabling Magnet")
            self._ser.write(f'G28 Z\n'.encode())
            self._wait_for_ok()
            self._magnet_is_engaged = False

        if self._currently_grabbed_spool is not None:
            self.spools[self._currently_grabbed_spool] = self.position
            self._currently_grabbed_spool = None

    def grab(self, spool: str):
        """Moves to the spools and grabs it.

        When the position of the spool is not yet known,
        the current position is assigned to the spool (unless another spool is already grabbed).

        When the position of the spool is known, the magnet is disengaged,
        the position is moved to the spool, and the magnet is engaged.

        :param spool: The spool to grab.
        """
        spool_pos = self.spools[spool]
        if spool_pos is None:
            if self._currently_grabbed_spool is None:
                self.spools[spool] = self.position
                self.engage_magnet()
                self.beep(440)
                self.beep(640)
                print(f"Assigning current position to {spool}")
                self._currently_grabbed_spool = spool
            else:
                self.beep(660)
                self.beep(660)
                print(f"Can't assign current position to new {spool} while holding {self._currently_grabbed_spool}!")
        else:
            self.disengage_magnet()
            self.move_to(*spool_pos)
            self.engage_magnet()
            self.beep(440)
            print(f"grabbed {spool}")
            self._currently_grabbed_spool = spool
