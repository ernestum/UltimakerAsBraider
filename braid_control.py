"""Braider control script."""
import time

import readchar
import serial
import yaml

from braider import Braider

help_text = """

Press a key to do something:

    - Press a letter to grab a spool
    - Press a number to move to a place
    - Press arrow keys to move the printhead
    - Press page up/down to engage/disengage the magnet
    - Press space to start braiding the pattern
    - Press delete to clear all places
    
If you press the letter of a spool that was never grabbed before, the current position
of the printhead will be assigned to that spool. 
This is useful to set the spool positions initially.

If you press the number of a place that was never defined before, the current position
of the printhead will be assigned to that place.
"""


def check_config_for_inconsistencies(config):
    if config["spool_names"] is None:
        raise ValueError("No spools defined in config.json")

    for spool_name in config["spool_names"]:
        if len(spool_name) != 1:
            raise ValueError("Spool names must be single characters")
        if spool_name not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            raise ValueError(f"Spool name '{spool_name}' is not a valid letter")

    if config["places"] is None:
        raise ValueError("No places defined in config.json")

    for place in config["places"]:
        if len(place) != 1:
            raise ValueError("Place names must be single characters")
        if place not in "1234567890":
            raise ValueError(f"Place name '{place}' is not a valid number. It must be a digit!")

    if "pattern" in config:
        for idx, command in enumerate(config["pattern"]):
            if len(command) != 2:
                raise ValueError(f"Command {idx}:{command} must be a tuple of length 2")
            spool, place = command
            if spool not in config["spool_names"]:
                raise ValueError(f"Spool command {idx}:'{spool}' is not defined in spool_names")
            if place not in config["places"]:
                raise ValueError(f"Place command {idx}:'{place}' is not defined in places")

    if "repeats" in config:
        if not isinstance(config["repeats"], int):
            raise ValueError(f"Repeat must be an integer, not {config['repeats']}")
        if config["repeats"] < 0:
            raise ValueError(f"Repeat must be a positive integer, not {config['repeats']}")


if __name__ == "__main__":
    print(help_text)
    serial_connection = serial.Serial('/dev/ttyACM0', 250000)
    time.sleep(2)  # Wait for the serial connection to be established

    with open("config.yaml", "r") as fh:
        config = yaml.load(fh, Loader=yaml.FullLoader)
        check_config_for_inconsistencies(config)

    brdr = Braider(serial_connection, spool_names=config["spool_names"])
    places = config["places"]

    while True:
        key = readchar.readkey()  # Get the key that was pressed

        if key.upper() in brdr.spools:
            brdr.grab(key.upper())

        elif key in places:
            place = places[key]
            if place is None:
                brdr.disengage_magnet()
                places[key] = list(brdr.position)
                brdr.beep(440)
                print(f"Assigning current position to {key}")
                with open("config.yaml", "w") as fh:
                    yaml.dump(config, fh)
            else:
                brdr.move_to(*place)
                brdr.beep(440)
                print(f"Moving to {key}")
        elif key == readchar.key.UP:
            brdr.move_up(5)
        elif key == readchar.key.DOWN:
            brdr.move_down(5)
        elif key == readchar.key.LEFT:
            brdr.move_left(5)
        elif key == readchar.key.RIGHT:
            brdr.move_right(5)
        elif key == readchar.key.PAGE_UP:
            brdr.engage_magnet()
        elif key == readchar.key.PAGE_DOWN:
            brdr.disengage_magnet()
        elif key == readchar.key.DELETE:
            for p in places:
                places[p] = None
            with open("config.yaml", "w") as fh:
                yaml.dump(config, fh)

            brdr.beep(640)
            brdr.beep(640)
            brdr.beep(640)
        elif key == readchar.key.SPACE:
            all_places_set = all(p is not None for p in places.values())
            all_spools_set = all(p is not None for p in brdr.spools.values())
            if not all_places_set:
                print("Not all places are set!", places)
                continue
            if not all_spools_set:
                print("Not all spools are set!", brdr.spools)
                continue

            # If repeats is not in the config, we do one repeat
            for r in range(config.get("repeats", 1)):
                for spool, place in config["pattern"]:
                    brdr.grab(spool)
                    brdr.move_to(*places[place])
        else:
            print(f"Did not understand: '{key}'")