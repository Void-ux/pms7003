### pms7003

A small, elegant and performant client driver for the PMS7003 particle matter sensor.

This code was tested on the Raspberry Pi 5, though feel free to use this on any machine with Python and a serial port.

```python
from pms7003 import PMSSensor

with PMSSensor('/dev/ttyAMA0') as sensor:
    while True:
        print(sensor.read())
```

### License

MIT
