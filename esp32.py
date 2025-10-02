# tcp_sender.py
import socket
from typing import Optional
from hand import HandGestureDetector
from functools import lru_cache
import time
from datetime import datetime

class TCPSender:
    def __init__(self, ip: str = "192.168.1.50", port: int = 5000) -> None:
        """
        TCP sender that sends Action commands to Arduino.
        :param ip: Arduino IP address
        :param port: Arduino TCP port
        """
        self.ip = ip
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.__last_action: int = int(datetime.now().timestamp())
        # self.connect()

    def connect(self) -> None:
        try:
            """Create and connect the TCP socket."""
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.ip, self.port))
            print(f"[TCP] Connected to {self.ip}:{self.port}")
        except Exception:
            return

    def send_action(self, hand: HandGestureDetector) -> None:
        if int(datetime.now().timestamp()) - self.__last_action <= 2:
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

    @lru_cache()
    def is_connected(self) -> bool:
        if not self.sock:
            return False
        try:
            # Check connection without sending data
            self.sock.send(b'')  # Sending empty bytes; will raise if disconnected
            return True
        except (socket.error, BrokenPipeError):
            return False
