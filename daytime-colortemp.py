#!/bin/env python
from datetime import time
import math

# Homeassistant mired range is [153, 500]
MIRED_MIN = 153.0
MIRED_MAX = 500.0
# Homeassistant brightness range is [0, 255]
BRIGHTNESS_RANGE_MIN = 75.0
BRIGHTNESS_RANGE_MAX = 225.0
# Max brightness
BRIGHTNESS_MAX = 255.0

HOURS_IN_DAY = 24.0

BRIGHTNESS_ON_ERROR = 255.0
MIRED_ON_ERROR = 220.0

# Configure shape. In hours.
BRIGHTNESS_MORNING_MIDPOINT = 6.5
BRIGHTNESS_TIME_TO_REACH_MAX_MORNING = 0.5
BRIGHTNESS_EVENING_MIDPOINT = 22.5
BRIGHTNESS_TIME_TO_REACH_MAX_EVENING = -2.0

TEMP_SHIFT_SUNRISE = 0.0
TEMP_TIME_TO_REACH_MAX_SUNRISE = 1.0
TEMP_SHIFT_SUNSET = 0.0
TEMP_TIME_TO_REACH_MAX_SUNSET = -2.0

SWITCH_BRIGHTNESS_A = (
    (BRIGHTNESS_MORNING_MIDPOINT + BRIGHTNESS_EVENING_MIDPOINT) / 2.0
    + BRIGHTNESS_TIME_TO_REACH_MAX_MORNING
    + BRIGHTNESS_TIME_TO_REACH_MAX_EVENING
)
SWITCH_BRIGHTNESS_B = (
    (BRIGHTNESS_MORNING_MIDPOINT + HOURS_IN_DAY + BRIGHTNESS_EVENING_MIDPOINT) / 2.0
    - BRIGHTNESS_TIME_TO_REACH_MAX_MORNING
    - BRIGHTNESS_TIME_TO_REACH_MAX_EVENING
)


def time_to_hours_of_day(t: time) -> float:
    return float(t.hour) + float(t.minute) / 60.0 + float(t.second) / 3600.0


def _sloped_value(x: float, midpoint: float, max_after: float):
    return math.tanh((x - midpoint) / max_after) / 2.0 + 0.5


def _calculate_brightness_f_from_hours(now: float) -> float:
    if now + HOURS_IN_DAY < SWITCH_BRIGHTNESS_B:
        now += HOURS_IN_DAY

    if now < SWITCH_BRIGHTNESS_A:
        brightness_f = _sloped_value(
            now,
            midpoint=BRIGHTNESS_MORNING_MIDPOINT,
            max_after=BRIGHTNESS_TIME_TO_REACH_MAX_MORNING,
        )

    else:
        brightness_f = _sloped_value(
            now,
            midpoint=BRIGHTNESS_EVENING_MIDPOINT,
            max_after=BRIGHTNESS_TIME_TO_REACH_MAX_EVENING,
        )
    return brightness_f


def _calculate_color_temp_f_from_hours(
    sunrise: float, sunset: float, now: float
) -> float:
    mid_day = (
        (sunrise + TEMP_SHIFT_SUNRISE + sunset + TEMP_SHIFT_SUNSET) / 2.0
        + TEMP_TIME_TO_REACH_MAX_SUNRISE
        + TEMP_TIME_TO_REACH_MAX_SUNSET
    )
    # might be >= HOURS_IN_DAY
    mid_night = (
        (sunrise + TEMP_SHIFT_SUNRISE + HOURS_IN_DAY + sunset + TEMP_SHIFT_SUNSET) / 2.0
        - TEMP_TIME_TO_REACH_MAX_SUNRISE
        - TEMP_TIME_TO_REACH_MAX_SUNSET
    )

    if now + HOURS_IN_DAY < mid_night:
        now += HOURS_IN_DAY

    if now < mid_day:
        temp_f = _sloped_value(
            now,
            midpoint=sunrise + TEMP_SHIFT_SUNRISE,
            max_after=TEMP_TIME_TO_REACH_MAX_SUNRISE,
        )
    else:
        temp_f = _sloped_value(
            now,
            midpoint=sunset + TEMP_SHIFT_SUNSET,
            max_after=TEMP_TIME_TO_REACH_MAX_SUNSET,
        )
    return temp_f


def calculate_color_temp_from_hours(sunrise: float, sunset: float, now: float) -> float:
    """Calculate brightness and color temperature in mireds.

    Return tuple (brightness, temp)
    """
    if now < 0.0:
        now = 0.0
    elif now > HOURS_IN_DAY:
        # leap second?
        now -= HOURS_IN_DAY
    if sunset <= sunrise:
        raise ValueError("Sunset needs to happen after sunrise")

    brightness_f = _calculate_brightness_f_from_hours(now)
    temp_f = _calculate_color_temp_f_from_hours(sunrise, sunset, now)

    brightness = (
        1.0 - brightness_f
    ) * BRIGHTNESS_RANGE_MIN + brightness_f * BRIGHTNESS_RANGE_MAX
    mired = (1.0 - temp_f) * MIRED_MAX + temp_f * MIRED_MIN
    return brightness, mired


def calculate_color_temp_from_time(sunrise: time, sunset: time, now: time) -> float:
    """Calculate color temperature in mireds [153.0, 500.0].

    Return tuple (brightness, temp)
    """
    return calculate_color_temp_from_hours(
        time_to_hours_of_day(sunrise),
        time_to_hours_of_day(sunset),
        time_to_hours_of_day(now),
    )


if __name__ == "__main__":
    sunrise = time(7, 0, 0)
    sunset = time(20, 0, 0)

    import numpy as np
    import matplotlib.pyplot as plt

    x = np.linspace(0.0, HOURS_IN_DAY, 200)
    sunrise = time_to_hours_of_day(sunrise)
    sunset = time_to_hours_of_day(sunset)

    print(f"sunrise hours: {sunrise}")
    print(f"sunset hours: {sunset}")

    def plot(t):
        return calculate_color_temp_from_hours(sunrise, sunset, t)

    y = np.vectorize(plot)(x)

    plt.plot(x, y[0])
    plt.plot(x, y[1])
    plt.show()
