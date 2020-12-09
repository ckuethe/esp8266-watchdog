This is an external watchdog for a raspberry pi that sometimes locks up hard,
probably due to thermal issues. The raspberry pi internal watchdog was unable
to cause a reboot, and getting to the power supply was inconvenient.

Here, a user-space process is required to contact the watchdog at least every
five minutes. A cron job triggers a request to `/feed` once per minute, to give
some tolerance for network issues, wifi errors, etc.

### Schematic
![Schematic](https://raw.githubusercontent.com/ckuethe/esp8266-watchdog/master/schematic.png)
