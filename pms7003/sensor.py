from __future__ import annotations

import time
from typing import TYPE_CHECKING, Literal, overload

import serial

from .errors import SensorError, ChecksumMismatch

if TYPE_CHECKING:
    from typing import TypeVar, Self
    from types import TracebackType

    BE = TypeVar("BE", bound=BaseException)


# payload is 32 bytes
START_SEQ = bytes([0x42, 0x4d])
# remaining 30 bytes will contain data
# as first two are start chars
FRAME_BYTES = 30

BYTES_LOOKUP = {
    1: 'pm1_0cf1',
    2: 'pm2_5cf1',
    3: 'pm10cf1',
    4: 'pm1_0',
    5: 'pm2_5',
    6: 'pm10',
    7: 'n0_3',
    8: 'n0_5',
    9: 'n1_0',
    10: 'n2_5',
    11: 'n5_0',
    12: 'n10',
}


class SensorReading:
    def __init__(self, data: dict[str, int]):
        # μg/m3
        # useful for calibration/lab conditions
        # not representative of real-world conditions
        self.pm1_0cf1: int = data['pm1_0cf1']
        self.pm2_5cf1: int = data['pm2_5cf1']
        self.pm10cf1: int = data['pm10cf1']
        # under atmospheric conditions
        # use these values
        self.pm1_0: int = data['pm1_0']
        self.pm2_5: int = data['pm2_5']
        self.pm10: int = data['pm10']
        # num particles > nx_y per 0.1L
        self.n0_3: int = data['n0_3']
        self.n0_5: int = data['n0_5']
        self.n1_0: int = data['n1_0']
        self.n2_5: int = data['n2_5']
        self.n5_0: int = data['n5_0']
        self.n10: int = data['n10']

    def __repr__(self) -> str:
        return f'<SensorReading PM1.0={self.pm1_0} PM2.5={self.pm2_5} PM10={self.pm10}>'


class PMSSensor:
    def __init__(self, serial_device: str):
        # values according to product data manual
        # https://download.kamami.pl/p564008-PMS7003%20series%20data%20manua_English_V2.5.pdf
        # backup:
        # https://cdn.danielgnt.com/screenshots/p564008-PMS7003%20series%20data%20manua_English_V2.5.pdf
        self._serial = serial.Serial(
            port=serial_device,
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2
        )
        self._mode: Literal['active', 'passive'] = 'active'

    def __enter__(self) -> Self:
        return self

    def __exit__(self, type_: type[BE] | None, value: BE, traceback: TracebackType) -> None:
        self.close()

    @property
    def mode(self) -> Literal['active', 'passive']:
        return self._mode

    @staticmethod
    def _split_high_low(value: int) -> tuple[int, int]:
        return (value >> 8) & 0xFF, value & 0xFF 

    def _get_buffer(self) -> list[int]:
        """Retrieves a reading from the sensor as a pre-processed buffer

        Returns
        -------
        List[:class:`int`]
            A raw list of bytes as integers
        """
        with self._serial as s:
            s.read_until(START_SEQ)
            buff = list(s.read(FRAME_BYTES))
            if len(buff) != FRAME_BYTES:
                raise SensorError()
            return buff

    def _parse_buffer(self, buff: list[int]) -> list[int]:
        """Iterates every second index and glues the H and L bytes together"""
        return [buff[i] << 8 | buff[i + 1] for i in range(0, len(buff), 2)]

    def _validate_checksum(self, buff: list[int], values: list[int]) -> bool:
        checksum = values[-1]
        return checksum == sum(buff[:-2]) + sum(START_SEQ)

    @overload
    def _send_command(
        self,
        command: int,
        data: int | None = None,
        *,
        expect_response: Literal[True],
        response_length: int = 6
    ) -> list[int]:
        ...

    @overload
    def _send_command(
        self,
        command: int,
        data: int | None = None,
        *,
        expect_response: Literal[False] = False,
        response_length: int = 6
    ) -> None:
        ...

    def _send_command(
        self,
        command: int,
        data: int | None = None,
        *,
        expect_response: bool = False,
        response_length: int = 6
    ) -> list[int] | None:
        dh, dl = self._split_high_low(data) if data else (0, 0)
        payload = [0x42, 0x4D, command, dh, dl]
        payload += self._split_high_low(sum(payload))

        with self._serial as serial:
            serial.write(bytearray(payload))

            if expect_response:
                # manual states this is the highest possible interval
                time.sleep(2.3)
                serial.read_until(START_SEQ)
                buff = list(serial.read(response_length))
                if len(buff) != response_length:
                    raise SensorError()
                return buff

    def wakeup(self) -> None:
        """Wakes up the sensor. It's recommended to wait 30s to let the fan circulate air."""
        self._send_command(0xe4, 1)

    def sleep(self) -> None:
        """Puts the sensor to sleep."""
        self._send_command(0xe4, 0, expect_response=True)

    def set_mode(self, mode: Literal['active', 'passive']) -> None:
        """Sets the mode of the sensor.
        Note that these changes will persist even after closing the sensor.
        """
        if mode not in ('active', 'passive'):
            raise ValueError('Invalid mode entered; either "active" or "passive"')

        self._send_command(0xe1, 1 if mode == 'active' else 0, expect_response=True)
        self._mode = mode

    def read(self):
        """Collects a reading from the sensor.
        
        Returns
        -------
        :class:`.SensorReading`
            The data encapsulated in a class, see attributes and comments for more info.
        """
        if self._mode == 'passive':
            buff = self._send_command(0xe2, expect_response=True, response_length=30)
        else:
            buff = self._get_buffer()
        values = self._parse_buffer(buff)

        if not self._validate_checksum(buff, values):
            raise ChecksumMismatch()

        data = {BYTES_LOOKUP[i]: values[i] for i in range(1, len(BYTES_LOOKUP) + 1)}
        return SensorReading(data)

    def close(self):
        self._serial.close()
