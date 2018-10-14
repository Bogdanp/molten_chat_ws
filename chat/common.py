from os import path

#: The path to the root project directory.
BASE_PATH = path.normpath(path.join(path.abspath(path.dirname(__file__)), ".."))


def path_to(*xs):
    """Construct a path from the root project directory.
    """
    return path.join(BASE_PATH, *xs)


def schema_from_model(cls, ob):
    params = {}
    for field_name, field in cls._FIELDS.items():
        params[field_name] = getattr(ob, field_name, None)
    return cls(**params)
