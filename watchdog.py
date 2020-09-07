# pylint: disable=import-error

from machine import Timer, Pin
import network
from picoweb import WebApp, jsonify
import time

# This li'l thingy is just a network-enabled watchdog and remote power switch
# for my all-sky camera which seems to be a crashy little bugger lately. Maybe
# thermal issues? Anyhoo, we just switch a 12V/2A power supply through some
# jellybean logic-level N-channel MOSFET. In my case I used a Fairchild/OnSemi
# RFP30N06LE (KiCAD didn't have that in its part library, so the schematic has
# a Fairchild FQP30N06L which is similar) as a low-side switch, eg.
#
# V+ -> load -> MOSFET -> GND
#           MCU---^
#
# Software-wise, the controlled device must make a web request every so often
# or else a countdown timer will run out triggering the GPIO connected to the
# MOSFET to be toggled, thereby power-cycling the controlled deviced.

app = WebApp(None)
mosfet_pin = Pin(16, Pin.OUT, value=1)  # GPIO16, D0
watchdog_counter = 0
watchdog_ttl = 300
watchdog_running = False
watchdog_timer = None
reset_count = 0
boot_time = None


def mosfet_off(_=None):
    mosfet_pin.off()


def mosfet_on(_=None):
    mosfet_pin.on()


def wd_callback(_=None):
    global watchdog_counter, reset_count
    watchdog_counter -= 1
    if watchdog_counter <= 0:
        watchdog_counter = watchdog_ttl
        reset_count += 1
        do_powercycle()


def set_auto():
    global watchdog_counter, watchdog_timer, watchdog_running, watchdog_ttl

    watchdog_counter = watchdog_ttl
    if watchdog_timer:
        watchdog_timer.deinit()
        watchdog_timer = None

    watchdog_timer = Timer(-1)
    watchdog_timer.init(period=1_000, mode=Timer.PERIODIC, callback=wd_callback)
    watchdog_running = True


@app.route("/")
def get_status(req=None, resp=None):
    rv = {
        "counter": watchdog_counter,
        "ttl": watchdog_ttl,
        "mosfet_on": bool(mosfet_pin.value()),
        "resets": reset_count,
        "running": watchdog_running,
        "uptime": time.time() - boot_time,
    }
    yield from jsonify(resp, rv)


@app.route("/off")
def set_off(req=None, resp=None):
    global watchdog_timer, watchdog_running
    if watchdog_timer:
        watchdog_timer.deinit()
        watchdog_timer = None
        watchdog_running = False
    mosfet_off()
    yield from jsonify(resp, {"mosfet": "off", "watchdog": "off"})


@app.route("/on")
def set_on(req=None, resp=None):
    global watchdog_timer, watchdog_running
    if watchdog_timer:
        watchdog_timer.deinit()
        watchdog_timer = None
        watchdog_running = False
    mosfet_on()
    yield from jsonify(resp, {"mosfet": "on", "watchdog": "off"})


@app.route("/reboot")
def do_powercycle(req=None, resp=None):
    global reset_count
    reset_count += 1
    toggle_timer = Timer(-1)
    mosfet_off()
    toggle_timer.init(period=10_000, mode=Timer.ONE_SHOT, callback=mosfet_on)
    yield from jsonify(resp, {"reboot": True, "reset_count": reset_count})


@app.route("/auto")
def do_auto(req=None, resp=None):
    set_auto()
    yield from jsonify(resp, {"mosfet": "auto", "watchdog": "on"})


@app.route("/feed")
def wd_feed(req=None, resp=None):
    global watchdog_counter
    watchdog_counter = watchdog_ttl

    if req:
        yield from jsonify(resp, {"watchdog_feed": True, "counter": watchdog_counter})


@app.route("/ttl")
def set_ttl(req=None, resp=None):
    global watchdog_ttl, watchdog_counter
    op = "get"
    try:
        req.parse_qs()
        ttl = int(req.form["ttl"])
        if ttl > 0:
            watchdog_ttl = ttl
            if watchdog_counter > ttl:
                watchdog_counter = ttl
            op = "set"
    except Exception:
        pass

    if req:
        yield from jsonify(resp, {"op": op, "ttl": watchdog_ttl})


def cb_time(_=None):
    _ = time.time()


def main():
    global boot_time, reset_count
    boot_time = time.time()
    clock_correcting_timer = Timer(-1)
    clock_correcting_timer.init(period=60_000, mode=Timer.PERIODIC, callback=cb_time)

    set_auto()
    app.run(debug=True, host="0.0.0.0", port=80)


if __name__ == "__main__":
    main()
