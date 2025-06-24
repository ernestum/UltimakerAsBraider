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
