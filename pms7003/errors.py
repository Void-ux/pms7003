class PMSException(Exception):
    """Base class for PMS-related exceptions"""
    pass


class ChecksumMismatch(PMSException):
    """Occurs when the provided checksum does not match the data buffer"""
    pass


class SensorError(PMSException):
    """Implies a problem with sensor communication that is unlikely to re-occur
    (e.g. serial connection glitch).
    """
    pass
