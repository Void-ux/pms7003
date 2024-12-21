### pms7003

A small, elegant and performant client driver for the PMS7003 particulate matter sensor.

This code was tested on the Raspberry Pi 5, though feel free to use this on any machine with Python and a serial port.

```python
from pms7003 import PMSSensor

with PMSSensor('/dev/ttyAMA0') as sensor:
    while True:
        print(sensor.read())
```

### Installation

Installing the library is simple and done purely through git, so make sure you have it installed (`sudo apt-get git` on Debian-based).

```shell
pip install git+https://github.com/Void-ux/pms7003.git
```

### License

MIT
