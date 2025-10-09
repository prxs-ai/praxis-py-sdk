"""
Prometheus Remote Write protocol buffer definitions.
Generated manually based on Prometheus remote.proto.
"""

from typing import List


class Label:
    """Prometheus label."""

    def __init__(self, name: str = "", value: str = ""):
        self.name = name
        self.value = value

    def SerializeToString(self) -> bytes:
        """Serialize label to protobuf format."""
        result = b""
        if self.name:
            name_bytes = self.name.encode('utf-8')
            result += b'\x0a' + self._encode_varint(len(name_bytes)) + name_bytes
        if self.value:
            value_bytes = self.value.encode('utf-8')
            result += b'\x12' + self._encode_varint(len(value_bytes)) + value_bytes
        return result

    @staticmethod
    def _encode_varint(value: int) -> bytes:
        """Encode integer as varint."""
        result = b""
        while value > 0x7F:
            result += bytes([0x80 | (value & 0x7F)])
            value >>= 7
        result += bytes([value & 0x7F])
        return result


class Sample:
    """Prometheus sample."""

    def __init__(self, value: float = 0.0, timestamp: int = 0):
        self.value = value
        self.timestamp = timestamp

    def SerializeToString(self) -> bytes:
        """Serialize sample to protobuf format."""
        import struct

        result = b""
        if self.value != 0.0:
            result += b'\x09' + struct.pack('<d', self.value)
        if self.timestamp != 0:
            result += b'\x10' + self._encode_varint(self.timestamp)
        return result

    @staticmethod
    def _encode_varint(value: int) -> bytes:
        """Encode integer as varint."""
        result = b""
        while value > 0x7F:
            result += bytes([0x80 | (value & 0x7F)])
            value >>= 7
        result += bytes([value & 0x7F])
        return result


class TimeSeries:
    """Prometheus time series."""

    def __init__(self, labels: List[Label] = None, samples: List[Sample] = None):
        self.labels = labels or []
        self.samples = samples or []

    def SerializeToString(self) -> bytes:
        """Serialize time series to protobuf format."""
        result = b""
        for label in self.labels:
            label_data = label.SerializeToString()
            result += b'\x0a' + self._encode_varint(len(label_data)) + label_data
        for sample in self.samples:
            sample_data = sample.SerializeToString()
            result += b'\x12' + self._encode_varint(len(sample_data)) + sample_data
        return result

    @staticmethod
    def _encode_varint(value: int) -> bytes:
        """Encode integer as varint."""
        result = b""
        while value > 0x7F:
            result += bytes([0x80 | (value & 0x7F)])
            value >>= 7
        result += bytes([value & 0x7F])
        return result


class WriteRequest:
    """Prometheus write request."""

    def __init__(self, timeseries: List[TimeSeries] = None):
        self.timeseries = timeseries or []

    def SerializeToString(self) -> bytes:
        """Serialize write request to protobuf format."""
        result = b""
        for ts in self.timeseries:
            ts_data = ts.SerializeToString()
            result += b'\x0a' + self._encode_varint(len(ts_data)) + ts_data
        return result

    @staticmethod
    def _encode_varint(value: int) -> bytes:
        """Encode integer as varint."""
        result = b""
        while value > 0x7F:
            result += bytes([0x80 | (value & 0x7F)])
            value >>= 7
        result += bytes([value & 0x7F])
        return result
