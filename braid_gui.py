from queue import Queue
from threading import Thread
import time
from imgui_bundle import imgui, immapp
import serial
import yaml

from braider import Braider
from config_loading import check_config_for_inconsistencies

command_queue = Queue(maxsize=1)

def exec_commands():
    while True:
        command = command_queue.get()
        command()
        command_queue.task_done()

command_worker = Thread(target=exec_commands, daemon=True)
command_worker.start()

def gui():
    global pattern_is_executing, pattern_cursor
    imgui.begin("Braid Control")

    imgui.separator_text("Going Places and Grabbing Spools")

    for spool in brdr.spools:
        highlight = brdr._currently_grabbed_spool == spool
        if highlight:
            imgui.push_style_color(imgui.Col_.button, imgui.get_style_color_vec4(imgui.Col_.text_selected_bg))
        if imgui.button(f"Grab {spool}"):
            command_queue.put(lambda s=spool: brdr.grab(s))
        if highlight:
            imgui.pop_style_color()
        imgui.same_line()

    imgui.new_line()

    for place in places.keys():
        if places[place] is None:
            if imgui.button(f"Assign {place} to current position"):
                command_queue.put(lambda p=place: brdr.disengage_magnet())
                places[place] = list(brdr.position)
                # brdr.beep(440) FIXME
                print(f"Assigning current position to {place}")
                with open("config.yaml", "w") as fh:
                    yaml.dump(config, fh)
        else:
            if imgui.button(f"Go to {place} {places[place]}"):
                command_queue.put(lambda p=place: brdr.move_to(*places[p]))
                # brdr.beep(440) FIXME
                print(f"Moving to {place}")
        imgui.same_line()
    imgui.new_line()
    if imgui.button("Clear all places"):
        for p in places:
            places[p] = None
        with open("config.yaml", "w") as fh:
            yaml.dump(config, fh)

        # brdr.beep(640) FIXME
        brdr.beep(640)
        brdr.beep(640)
        brdr.beep(640)

    imgui.separator_text("Manual Movement Controls")

    imgui.dummy(imgui.ImVec2(7, 0))  # Add some space
    imgui.same_line()

    if imgui.arrow_button("Up", imgui.Dir.up):
        command_queue.put(lambda: brdr.move_up(5))
    
    if imgui.arrow_button("Left", imgui.Dir.left):
        command_queue.put(lambda: brdr.move_left(5))
    imgui.same_line()
    if imgui.arrow_button("Right", imgui.Dir.right):
        command_queue.put(lambda: brdr.move_right(5))

    imgui.dummy(imgui.ImVec2(7, 0))  # Add some space
    imgui.same_line()
    if imgui.arrow_button("Down", imgui.Dir.down):
        command_queue.put(lambda: brdr.move_down(5))

    changed, new_state = imgui.checkbox("Engage Magnet", brdr._magnet_is_engaged)
    if changed:
        if new_state:
            command_queue.put(lambda: brdr.engage_magnet())
        else:
            command_queue.put(lambda: brdr.disengage_magnet())


    imgui.separator_text("Pattern Control")

    if imgui.arrow_button("Rewind", imgui.Dir.left):
        pattern_cursor = 0
        pattern_is_executing = False
    imgui.same_line()

    if not pattern_is_executing and imgui.button("Run Pattern"):
        all_places_set = all(p is not None for p in places.values())
        all_spools_set = all(p is not None for p in brdr.spools.values())
        if not all_places_set:
            print("Not all places are set!", places)
        elif not all_spools_set:
            print("Not all spools are set!", brdr.spools)
        else: 
            pattern_is_executing = True
            
    if pattern_is_executing and imgui.button("Pause Pattern"):
        pattern_is_executing = False

    for idx, (spool, place) in enumerate(config.get("pattern", [])):
        highlight = pattern_cursor == idx
        if highlight:
            imgui.push_style_color(imgui.Col_.button, imgui.get_style_color_vec4(imgui.Col_.text_selected_bg))

        imgui.begin_disabled(pattern_is_executing or places[place] is None or spool not in brdr.spools)
        if imgui.button(f"{spool} -> {place}##{idx}"):
            command_queue.put(lambda s=spool, p=place: (brdr.grab(s), brdr.move_to(*places[p])))
        imgui.end_disabled()
        if highlight:
            imgui.pop_style_color()
                
    if pattern_is_executing:
        spool, place = config["pattern"][pattern_cursor]
        try:
            command_queue.put(lambda s=spool, p=place: (brdr.grab(s), brdr.move_to(*places[p])))
            pattern_cursor += 1
        except Exception as e:
            print(f"Error executing pattern: {e}")
            
    if pattern_cursor >= len(config.get("pattern", [])):
        pattern_is_executing = False
        pattern_cursor = 0
        print("Pattern execution completed.")

    
    imgui.end()


class DummySerial:
    def write(self, data):
        print(f"DummySerial write: {data}")

    def readline(self):
        return b'ok\n'

if __name__ == "__main__":
    # serial_connection = serial.Serial('/dev/ttyACM0', 250000)
    time.sleep(2)  # Wait for the serial connection to be established

    with open("config3.yaml", "r") as fh:
        config = yaml.load(fh, Loader=yaml.FullLoader)
        check_config_for_inconsistencies(config)

    brdr = Braider(DummySerial(), spool_names=config["spool_names"])
    places = config["places"]
    pattern_is_executing = False
    pattern_cursor = 0
    immapp.run(gui_function=gui, window_title="Braid GUI", window_size_auto=True)