import abc
import socket
import typing
from typing import Optional, Union
from datetime import datetime

from hand import HandGestureDetector


class Esp32(abc.ABC):

    def __init__(self, ip: str, port: int):
        self._ip = ip
        self._port = port

    @abc.abstractmethod
    def connect(self) -> None:
        pass

    @abc.abstractmethod
    def send_action(self, action: str) -> typing.Any:
        pass

    @abc.abstractmethod
    def is_connected(self) -> bool:
        pass


class TCPSender(Esp32):
    def __init__(self, ip: str = "esp32.local", port: int = 1234, connection_timeout: int = 5):
        """
        TCP sender that sends Action commands to ESP32/Arduino.
        :param ip: ESP32/Arduino IP address
        :param port: TCP port
        :param action_cooldown: Minimum seconds between actions
        :param connection_timeout: Connection timeout in seconds
        """
        super().__init__(ip, port)
        self.__connection_timeout = connection_timeout
        self._sock: Optional[socket.socket] = None
        self.__last_action: int = int(datetime.now().timestamp())

    def connect(self) -> None:
        """Create and connect the TCP socket."""
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(self.__connection_timeout)
            self._sock.connect((self._ip, self._port))
            print(f"[TCP] Connected to {self._ip}:{self._port}")
        except Exception as e:
            print(f"[TCP] Connection failed: {e}")
            return

    def send_action(self, action: str) -> None:
        if not self._sock:
            raise ConnectionError("TCP socket is not connected")
        frame = (action + "\n").encode("utf-8")
        self._sock.sendall(frame)
        print(f"[TCP] Sent action: {frame}")

    def close(self) -> None:
        """Close the TCP connection."""
        if self._sock:
            self._sock.close()
            self._sock = None
            print("[TCP] Connection closed")

    def is_connected(self) -> bool:
        if not self._sock:
            return False
        try:
            # Check connection without sending data
            self._sock.send(b'')  # Sending empty bytes; will raise if disconnected
            return True
        except (socket.error, BrokenPipeError):
            return False
