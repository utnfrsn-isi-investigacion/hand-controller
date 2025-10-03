import socket
from typing import Optional, Union
from hand import HandGestureDetector
from datetime import datetime


class TCPSender:
    def __init__(
        self, 
        ip: str = "esp32.local", 
        port: int = 1234, 
        action_cooldown: int = 2, 
        connection_timeout: int = 5
    ) -> None:
        """
        TCP sender that sends Action commands to ESP32/Arduino.
        :param ip: ESP32/Arduino IP address
        :param port: TCP port
        :param action_cooldown: Minimum seconds between actions
        :param connection_timeout: Connection timeout in seconds
        """
        self.ip = ip
        self.port = port
        self.action_cooldown = action_cooldown
        self.connection_timeout = connection_timeout
        self.sock: Optional[socket.socket] = None
        self.__last_action: int = int(datetime.now().timestamp())

    def connect(self) -> None:
        """Create and connect the TCP socket."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.connection_timeout)
            self.sock.connect((self.ip, self.port))
            print(f"[TCP] Connected to {self.ip}:{self.port}")
        except Exception as e:
            print(f"[TCP] Connection failed: {e}")
            return

    def send_action(self, hand: HandGestureDetector) -> None:
        if int(datetime.now().timestamp()) - self.__last_action <= self.action_cooldown:
            return

        self.__last_action = int(datetime.now().timestamp())
        """Send the given action to Arduino."""
        if not self.sock:
            raise ConnectionError("TCP socket is not connected")
        message = hand.get_action().value.encode("utf-8")

        self.sock.sendall(message)
        print(f"[TCP] Sent action: {message}")

    def close(self) -> None:
        """Close the TCP connection."""
        if self.sock:
            self.sock.close()
            self.sock = None
            print("[TCP] Connection closed")

    def is_connected(self) -> bool:
        if not self.sock:
            return False
        try:
            # Check connection without sending data
            self.sock.send(b'')  # Sending empty bytes; will raise if disconnected
            return True
        except (socket.error, BrokenPipeError):
            return False
