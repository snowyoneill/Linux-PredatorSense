## ------------------------------##
## ---- Acer keyboard backlight --##
# ---------------------------------##
# Writes RGB keyboard effect payloads to the acer-gkbbl character devices
# exposed by the kernel driver (mohamed-bouhlel's acer_gkbbl / facer family).
# Devices are only present on machines with a supported RGB keyboard, so
# callers should gate on is_supported().
# ---------------------------------##

PAYLOAD_SIZE = 16
CHARACTER_DEVICE = "/dev/acer-gkbbl-0"
PAYLOAD_SIZE_STATIC_MODE = 4
CHARACTER_DEVICE_STATIC = "/dev/acer-gkbbl-static-0"

# When True, payloads are printed instead of written to the devices. Preview
# mode sets this so the keyboard tab can be shown without touching the real
# hardware of the machine running the preview.
DRY_RUN = False


def is_supported():
    """True when the kernel exposes both gkbbl character devices."""
    import os

    if DRY_RUN:
        return True
    return os.path.exists(CHARACTER_DEVICE) and os.path.exists(CHARACTER_DEVICE_STATIC)


def set_mode(mode, zone, speed, brightness, direction, red, green, blue):
    """Apply a keyboard effect.

    Ranges follow the facer/acer-gkbbl driver (facer_rgb.py):
      speed      0-9   (0 = no animation)
      brightness 0-100 (0 = off, 100 = maximum)
      direction  1 = right to left, 2 = left to right
      zone       0 = all, else 1-4 (static mode only)
    """
    if mode == 0:
        _set_static_mode(zone, brightness, red, green, blue)
    else:
        _set_dynamic_mode(mode, speed, brightness, direction, red, green, blue)


def _set_static_mode(zone, brightness, red, green, blue):
    if zone == 0:
        for i in range(1, 5):
            _write_to_device(
                CHARACTER_DEVICE_STATIC, _create_static_payload(i, red, green, blue)
            )
    else:
        _write_to_device(
            CHARACTER_DEVICE_STATIC, _create_static_payload(zone, red, green, blue)
        )
    _write_to_device(CHARACTER_DEVICE, _create_brightness_payload(brightness))


def _set_dynamic_mode(mode, speed, brightness, direction, red, green, blue):
    payload = [0] * PAYLOAD_SIZE
    payload[0] = mode
    payload[1] = speed
    payload[2] = brightness
    payload[3] = 8 if mode == 3 else 0
    payload[4] = direction
    payload[5] = red
    payload[6] = green
    payload[7] = blue
    payload[9] = 1
    _write_to_device(CHARACTER_DEVICE, payload)


def _create_static_payload(zone, red, green, blue):
    payload = [0] * PAYLOAD_SIZE_STATIC_MODE
    payload[0] = 1 << (zone - 1)
    payload[1] = red
    payload[2] = green
    payload[3] = blue
    return payload


def _create_brightness_payload(brightness):
    payload = [0] * PAYLOAD_SIZE
    payload[2] = brightness  # 0 = off, 100 = maximum backlight brightness
    payload[9] = 1
    return payload


def _write_to_device(device, payload):
    if DRY_RUN:
        print(f"[preview] would write to {device}: {payload}")
        return
    with open(device, "wb") as cd:
        cd.write(bytes(payload))
