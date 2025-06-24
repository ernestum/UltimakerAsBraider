"""Braider control script."""
import time

import readchar
import serial
import yaml

from braider import Braider
from config_loading import check_config_for_inconsistencies

help_text = """

Press a key to do something:

    - Press a letter to grab a spool
    - Press a number to move to a place
    - Press arrow keys to move the printhead
    - Press page up/down to engage/disengage the magnet
    - Press space to start braiding the pattern
    - Press delete to clear all places
    - Press F5 to reload the pattern from config.yaml
    
If you press the letter of a spool that was never grabbed before, the current position
of the printhead will be assigned to that spool. 
This is useful to set the spool positions initially.

If you press the number of a place that was never defined before, the current position
of the printhead will be assigned to that place.

To interrupt the pattern, press CTRL+C. Then press SPACE to continue or any other key to abort.
"""


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
                    try:
                        brdr.grab(spool)
                        brdr.move_to(*places[place])
                    except KeyboardInterrupt:
                        print("SPACE to continue, any other key to abort")
                        key = readchar.readkey()
                        if key != readchar.key.SPACE:
                            print("Aborting pattern")
                            break
                        else:
                            print("Continuing pattern")
        elif key == readchar.key.F5:
            # Reload the pattern from config file
            print("Reloading pattern from config.yaml ...")
            with open("config.yaml", "r") as fh:
                loaded_config = yaml.load(fh, Loader=yaml.FullLoader)
                try:
                    check_config_for_inconsistencies(loaded_config)

                    if config['spool_names'] != loaded_config['spool_names']:
                        raise ValueError("Can't change the spool names when reloading!")

                    config = loaded_config
                    places = config["places"]
                except ValueError as e:
                    print(e.args)
        else:
            print(f"Did not understand: '{key}'")