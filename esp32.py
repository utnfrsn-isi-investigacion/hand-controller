# tcp_sender.py
import socket
from typing import Optional
from hand import HandGestureDetector


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
        self.connect()

    def connect(self) -> None:
        """Create and connect the TCP socket."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.ip, self.port))
        print(f"[TCP] Connected to {self.ip}:{self.port}")

    def send_action(self, hand: HandGestureDetector) -> None:
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
