import abc
import logging
import socket
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)


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
        self.__reconnect_lock = threading.Lock()
        self.__reconnect_thread: Optional[threading.Thread] = None
        self._sock: Optional[socket.socket] = None

    def connect(self) -> bool:
        """Create and connect the TCP socket. Returns True on success."""
        self.__last_connect_attempt = time.monotonic()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.__connection_timeout)
        try:
            sock.connect((self._ip, self._port))
        except OSError as e:
            logger.warning("Connection to %s:%s failed: %s", self._ip, self._port, e)
            sock.close()
            self._sock = None
            return False
        self._sock = sock
        logger.info("Connected to %s:%s", self._ip, self._port)
        return True

    def send_action(self, action: str) -> bool:
        """Send an action, scheduling a reconnect if needed. Returns True if sent."""
        sock = self._sock
        if sock is None:
            self.__schedule_reconnect()
            return False
        try:
            sock.sendall((action + "\n").encode("utf-8"))
            self.__drain_replies(sock)
            return True
        except OSError as e:
            logger.warning("Send failed: %s", e)
            self.close()
            return False

    def __schedule_reconnect(self) -> None:
        """Start a throttled background reconnect attempt.

        connect() can block for seconds on mDNS resolution, so it must not
        run on the caller's (frame loop) thread.
        """
        if time.monotonic() - self.__last_connect_attempt < self.__reconnect_interval:
            return
        with self.__reconnect_lock:
            if self.__reconnect_thread and self.__reconnect_thread.is_alive():
                return
            self.__last_connect_attempt = time.monotonic()
            logger.info("Attempting to reconnect...")
            self.__reconnect_thread = threading.Thread(target=self.connect, daemon=True)
            self.__reconnect_thread.start()

    def __drain_replies(self, sock: socket.socket) -> None:
        """Discard pending ESP32 replies so the receive buffer never fills up.

        Operates on the socket the caller just sent on, not self._sock, which
        the background reconnect thread may swap concurrently.
        """
        sock.settimeout(0)
        try:
            while True:
                if not sock.recv(4096):
                    raise OSError("Connection closed by peer")
        except BlockingIOError:
            return  # no more pending data
        finally:
            sock.settimeout(self.__connection_timeout)

    def close(self) -> None:
        """Close the TCP connection."""
        if self._sock:
            try:
                self._sock.close()
            finally:
                self._sock = None
            logger.info("Connection closed")

    def is_connected(self) -> bool:
        return self._sock is not None
