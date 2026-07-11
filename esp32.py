import abc
import socket
import time
from typing import Optional


class Esp32(abc.ABC):

    def __init__(self, ip: str, port: int):
        self._ip = ip
        self._port = port

    @abc.abstractmethod
    def connect(self) -> bool:
        pass

    @abc.abstractmethod
    def send_action(self, action: str) -> bool:
        pass

    @abc.abstractmethod
    def is_connected(self) -> bool:
        pass

    @abc.abstractmethod
    def close(self) -> None:
        pass


class TCPSender(Esp32):
    def __init__(self, ip: str = "esp32.local", port: int = 1234,
                 connection_timeout: int = 5, reconnect_interval: float = 2.0):
        """
        TCP sender that sends Action commands to ESP32/Arduino.
        :param ip: ESP32/Arduino IP address
        :param port: TCP port
        :param connection_timeout: Connection timeout in seconds
        :param reconnect_interval: Minimum seconds between reconnection attempts
        """
        super().__init__(ip, port)
        self.__connection_timeout = connection_timeout
        self.__reconnect_interval = reconnect_interval
        self.__last_connect_attempt = 0.0
        self._sock: Optional[socket.socket] = None

    def connect(self) -> bool:
        """Create and connect the TCP socket. Returns True on success."""
        self.__last_connect_attempt = time.monotonic()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.__connection_timeout)
        try:
            sock.connect((self._ip, self._port))
        except OSError as e:
            print(f"[TCP] Connection failed: {e}")
            sock.close()
            self._sock = None
            return False
        self._sock = sock
        print(f"[TCP] Connected to {self._ip}:{self._port}")
        return True

    def send_action(self, action: str) -> bool:
        """Send an action, reconnecting if needed. Returns True if sent."""
        if self._sock is None and not self.__try_reconnect():
            return False
        try:
            self._sock.sendall((action + "\n").encode("utf-8"))  # type: ignore[union-attr]
            self.__drain_replies()
            return True
        except OSError as e:
            print(f"[TCP] Send failed: {e}")
            self.close()
            return False

    def __try_reconnect(self) -> bool:
        """Attempt to reconnect, throttled to one attempt per reconnect_interval."""
        if time.monotonic() - self.__last_connect_attempt < self.__reconnect_interval:
            return False
        print("[TCP] Attempting to reconnect...")
        return self.connect()

    def __drain_replies(self) -> None:
        """Discard pending ESP32 replies so the receive buffer never fills up."""
        if self._sock is None:
            return
        self._sock.settimeout(0)
        try:
            while True:
                if not self._sock.recv(4096):
                    raise OSError("Connection closed by peer")
        except BlockingIOError:
            return  # no more pending data
        finally:
            self._sock.settimeout(self.__connection_timeout)

    def close(self) -> None:
        """Close the TCP connection."""
        if self._sock:
            try:
                self._sock.close()
            finally:
                self._sock = None
            print("[TCP] Connection closed")

    def is_connected(self) -> bool:
        return self._sock is not None
