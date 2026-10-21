"""Letterboxed logical-table viewport shared by drawing and mouse input."""


def viewport(display_size, logical_size):
    width, height = display_size
    logical_width, logical_height = logical_size
    if width <= 0 or height <= 0:
        return 1.0, logical_size, (0, 0)
    scale = min(width / logical_width, height / logical_height)
    size = (round(logical_width * scale), round(logical_height * scale))
    offset = ((width - size[0]) // 2, (height - size[1]) // 2)
    return scale, size, offset


def design_position(position, display_size, logical_size):
    scale, _, offset = viewport(display_size, logical_size)
    return (round((position[0] - offset[0]) / scale),
            round((position[1] - offset[1]) / scale))
