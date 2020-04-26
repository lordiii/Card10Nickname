import utime
import display
import leds
import ledfx
import buttons
import light_sensor
import ujson
import os

FILENAME = "nickname.json"

def wheel(pos):
    """
    Taken from https://badge.team/projects/rainbow_name
    Input a value 0 to 255 to get a color value.
    The colours are a transition r - g - b - back to r.
    :param pos: input position
    :return: rgb value
    """
    if pos < 0:
        return 0, 0, 0
    if pos > 255:
        pos -= 255
    if pos < 85:
        return int(255 - pos * 3), int(pos * 3), 0
    if pos < 170:
        pos -= 85
        return 0, int(255 - pos * 3), int(pos * 3)
    pos -= 170
    return int(pos * 3), 0, int(255 - (pos * 3))


def random_rgb():
    """
    Generates a random RGB value
    :return: RGB array
    """
    rgb = []
    for i in range(0, 3):
        rand = int.from_bytes(os.urandom(1), "little")
        if rand > 255:
            rand = 255
        rgb.append(rand)
    return rgb


def render_error(err1, err2):
    """
    Function to render two lines of text (each max 11 chars). Useful to display error messages
    :param err1: line one
    :param err2: line two
    """
    with display.open() as disp:
        disp.clear()
        disp.print(err1, posx=80 - round(len(err1) / 2 * 14), posy=18)
        disp.print(err2, posx=80 - round(len(err2) / 2 * 14), posy=42)
        disp.update()
        disp.close()


def get_bat_color(bat):
    """
    Function determines the color of the battery indicator. Colors can be set in config.
    Voltage threshold's are currently estimates as voltage isn't that great of an indicator for
    battery charge.
    :param bat: battery config tuple (boolean: indicator on/off, array: good rgb, array: ok rgb, array: bad rgb)
    :return: battery status tuple (float: battery voltage, false if old firmware, RGB color array otherwise)
    """
    try:
        v = os.read_battery()
        if v > 3.8:
            return (v, bat[1])
        if v > 3.6:
            return (v, bat[2])
        return (v, bat[3])
    except AttributeError:
        return (0, False)


def render_battery(disp, bat):
    """
    Adds the battery indicator to the display. Does not call update or clear so it can be used in addition to
    other display code.
    :param disp: open display
    :param bat: battery config tuple (boolean: indicator on/off, array: good rgb, array: ok rgb, array: bad rgb)
    """
    v, c = get_bat_color(bat)
    if not c:
        return
    if v > 4.0:
        disp.rect(140, 2, 155, 9, filled=True, col=c)
    else:
        disp.rect(140, 2, 154, 8, filled=False, col=c)
        if v > 3.5:
            disp.rect(141, 3, 142 + int((v - 3.5) * 24), 8, filled=True, col=c)
    disp.rect(155, 4, 157, 7, filled=True, col=c)


def get_time():
    """
    Generates a nice timestamp in format hh:mm:ss from the devices localtime
    :return: timestamp
    """
    timestamp = ""
    if utime.localtime()[3] < 10:
        timestamp = timestamp + "0"
    timestamp = timestamp + str(utime.localtime()[3]) + ":"
    if utime.localtime()[4] < 10:
        timestamp = timestamp + "0"
    timestamp = timestamp + str(utime.localtime()[4]) + ":"
    if utime.localtime()[5] < 10:
        timestamp = timestamp + "0"
    timestamp = timestamp + str(utime.localtime()[5])
    return timestamp


def toggle_rockets(state):
    """
    Turns all rocked LEDs on or off.
    :param state: True=on, False=off
    """
    brightness = 15
    if not state:
        brightness = 0
    leds.set_rocket(0, brightness)
    leds.set_rocket(1, brightness)
    leds.set_rocket(2, brightness)


def render_nickname(title, sub, fg_color, bg_color, fg_sub_color, bg_sub_color, background, bat):
    """
    Main function to render the nickname on screen.
    Pretty ugly but not time for cleanup right now (and some APIs missing)
    :param title: first row of text
    :param sub: second row of text
    :param fg_color: tuple of (day, night) rgb for title text color
    :param bg_color: tuple of (day, night) rgb for title background color
    :param fg_sub_color: tuple of (day, night) rgb for subtitle text color
    :param bg_sub_color: tuple of (day, night) rgb for subtitle background color
    :param background: tuple of (day, night) rgb for general background color
    :param bat: battery config tuple (boolean: indicator on/off, array: good rgb, array: ok rgb, array: bad rgb)
    """
    posy = 30
    if sub != "":
        posy = 18
    r_sub = sub
    while True:
        sleep = 0.5
        if sub == "#time":
            r_sub = get_time()
        # Animations
        for i in range(0, 14):
            leds.prep(i, random_rgb())
        leds.update()
        leds.dim_top(4)
        toggle_rockets(True)

        # Print to Display
        with display.open() as disp: 
            disp.rect(0, 0, 160, 80, col=background, filled=True)
            if bat[0]:
                render_battery(disp, bat)
            disp.print(
                title,
                fg=fg_color,
                bg=bg_color,
                posx=80 - round(len(title) / 2 * 14),
                posy=posy,
            )
            if r_sub != "":
                disp.print(
                    r_sub,
                    fg=fg_sub_color,
                    bg=bg_sub_color,
                    posx=80 - round(len(r_sub) / 2 * 14),
                    posy=42,
                )

            disp.update()
            disp.close()
        utime.sleep(sleep)


def get_key(json, key, default):
    """
    Gets a defined key from a json object or returns a default if the key cant be found
    :param json: json object to search key in
    :param key: key to search for
    :param default: default to return if no key is found
    :return:
    """
    try:
        return json[key]
    except KeyError:
        return default


leds.clear()
with display.open() as disp:
    disp.clear().update()
    disp.close()
if FILENAME in os.listdir("."):
    f = open(FILENAME, "r")
    try:
        c = ujson.loads(f.read())
        f.close()
        # parse config
        nick = get_key(c, "nickname", "no nick")
        sub = get_key(c, "subtitle", "")
        # battery
        battery_show = get_key(c, "battery", True)
        battery_c_good = get_key(c, "battery_color_good", [0, 230, 00])
        battery_c_ok = get_key(c, "battery_color_ok", [255, 215, 0])
        battery_c_bad = get_key(c, "battery_color_bad", [255, 0, 0])
        # color values
        background = get_key(c, "background", [0, 0, 0])
        fg_color = get_key(c, "fg_color", [255, 255, 255])
        bg_color = get_key(c, "bg_color", background)
        fg_sub_color = get_key(c, "fg_sub_color", [255, 255, 255])
        bg_sub_color = get_key(c, "bg_sub_color", background)
        # render nickname
        render_nickname(
            nick,
            sub,
            fg_color,
            bg_color,
            fg_sub_color,
            bg_sub_color,
            background,
            (battery_show, battery_c_good, battery_c_ok, battery_c_bad),
        )
    except ValueError:
        render_error("invalid", "json")
