import time
from typing import Tuple, Optional, Dict

import readchar
import serial as serial


class Plotter:
    def __init__(
            self,
            serial_connection: serial.Serial,
            width: float = 70,
            height: float = 70,
            engage_travel: float = 15
         ):
        self._ser = serial_connection
        self._width = width
        self._height = height
        self._engage_travel = engage_travel

        self._position: Tuple[float, float] = None
        self._magnet_is_engaged = None

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

        # Home X and Y axes
        self._ser.write(b'G28 X Y\n')
        self._wait_for_ok()


        # Reset mirror of plotter state
        self._position = (0, 0)

        # After homing the magnet is pulled all the way down, so it is not engaged
        self._magnet_is_engaged = False

    def move_to(self, x: float, y: float):
        x, y = self._clip_position(x, y)
        self._ser.write(f'G1 X{x} Y{y}\n'.encode())
        self._wait_for_ok()
        self._position = (x, y)

    def move_to_relative(self, x: float, y: float):
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
    def position(self):
        return self._position

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    def _wait_for_ok(self):
        while True:
            response = self._ser.readline().decode().strip()
            if response == 'ok':
                break
            else:
                pass
                # print(response)

    def _clip_position(self, x: float, y: float):
        return max(0, min(self._width, x)), max(0, min(self._height, y))

    def engage_magnet(self):
        if not self._magnet_is_engaged:
            print("Enabling Magnet")
            self._ser.write(f'G1 Z{self._engage_travel}\n'.encode())
            self._wait_for_ok()
            self._magnet_is_engaged = True

    def disengage_magnet(self):
        if self._magnet_is_engaged:
            print("Disabling Magnet")
            self._ser.write(f'G28 Za\n'.encode())
            self._wait_for_ok()
            self._magnet_is_engaged = False


class Winder(Plotter):
    def __init__(
            self,
            serial_connection: serial.Serial,
            width: float = 70,
            height: float = 70
         ):
        super().__init__(serial_connection, width, height)

        self.spools: Dict[str, Optional[Tuple[float, float]]] = dict(
            R=None,
            G=None,
            B=None,
        )

        self._grabbed_spool = None

    def grab(self, spool: str):
        spool_pos = self.spools[spool]
        if spool_pos is None:
            if self._grabbed_spool is None:
                self.spools[spool] = self.position
                self.engage_magnet()
                self.beep(440)
                self.beep(640)
                print(f"Assigning current position to {spool}")
                self._grabbed_spool = spool
            else:
                self.beep(660)
                self.beep(660)
                print(f"Can't assign current position to new {spool} while holding {self._grabbed_spool}!")
        else:
            self.disengage_magnet()
            self.move_to(*spool_pos)
            self.engage_magnet()
            self.beep(440)
            print(f"grabbed {spool}")
            self._grabbed_spool = spool

    def disengage_magnet(self):
        super().disengage_magnet()
        if self._grabbed_spool is not None:
            self.spools[self._grabbed_spool] = self.position
            self._grabbed_spool = None


if __name__ == "__main__":
    ser = serial.Serial('/dev/ttyACM0', 250000)
    time.sleep(2)  # Wait for the serial connection to be established

    winder = Winder(ser, 200, 200)

    places = {
        '1': None,
        '2': None,
        '3': None,
        '4': None,
    }

    while True:
        key = readchar.readkey()

        if key.upper() in winder.spools:
            winder.grab(key.upper())

        elif key in places:
            place = places[key]
            if place is None:
                winder.disengage_magnet()
                places[key] = winder.position
                winder.beep(440)
                print(f"Assigning current position to {key}")
            else:
                winder.move_to(*place)
                winder.beep(440)
                print(f"Moving to {key}")
        elif key == readchar.key.UP:
            winder.move_up(5)
        elif key == readchar.key.DOWN:
            winder.move_down(5)
        elif key == readchar.key.LEFT:
            winder.move_left(5)
        elif key == readchar.key.RIGHT:
            winder.move_right(5)
        elif key == readchar.key.PAGE_UP:
            winder.engage_magnet()
        elif key == readchar.key.PAGE_DOWN:
            winder.disengage_magnet()
        elif key == readchar.key.SPACE:
            all_places_set = all(p is not None for p in places.values())
            all_spools_set = all(p is not None for p in winder.spools.values())
            if not all_places_set:
                print("Not all places are set!", places)
                continue
            if not all_spools_set:
                print("Not all spools are set!", winder.spools)
                continue

            # Ensure init state is established
            winder.grab("R")
            winder.move_to(*places['1'])

            winder.grab("G")
            winder.move_to(*places['3'])

            winder.grab("B")
            winder.move_to(*places['2'])

            # Step 1
            winder.grab("R")
            winder.move_to(*places['4'])

            # Step 2
            winder.grab("G")
            winder.move_to(*places['1'])

            # Step 3
            winder.grab("B")
            winder.move_to(*places['3'])

            # Step 4
            winder.grab("R")
            winder.move_to(*places['2'])

            # Step 5
            winder.grab("G")
            winder.move_to(*places['4'])

            # Step 6
            winder.grab("B")
            winder.move_to(*places['1'])

            # Step 7
            winder.grab("R")
            winder.move_to(*places['3'])

            # Step 8
            winder.grab("G")
            winder.move_to(*places['2'])
        else:
            print(f"Did not understand: '{key}'")