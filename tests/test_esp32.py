import unittest
import socket
import time
import sys
import os

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from esp32 import TCPSender  # noqa: E402


def closed_port() -> int:
    """Return a localhost port with nothing listening on it."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestTCPSenderOffline(unittest.TestCase):

    def test_connect_failure_leaves_disconnected(self):
        """A failed connect must not leave a half-initialized socket behind."""
        sender = TCPSender(ip="127.0.0.1", port=closed_port(), connection_timeout=1)
        self.assertFalse(sender.connect())
        self.assertFalse(sender.is_connected())

    def test_send_without_connection_returns_false(self):
        """Sending while disconnected fails gracefully instead of raising."""
        sender = TCPSender(ip="127.0.0.1", port=closed_port(), connection_timeout=1, reconnect_interval=3600)
        sender.connect()
        self.assertFalse(sender.send_action("001"))


class TestTCPSenderWithServer(unittest.TestCase):

    def setUp(self):
        self.server = socket.create_server(("127.0.0.1", 0))
        self.server.settimeout(5)
        self.port = self.server.getsockname()[1]
        self.sender = TCPSender(ip="127.0.0.1", port=self.port, connection_timeout=1, reconnect_interval=0)

    def tearDown(self):
        self.sender.close()
        self.server.close()

    def test_send_action_delivers_newline_terminated_frame(self):
        self.assertTrue(self.sender.connect())
        conn, _ = self.server.accept()
        self.assertTrue(self.sender.send_action("001"))
        self.assertEqual(conn.recv(16), b"001\n")
        conn.close()

    def test_replies_are_drained_without_breaking_sends(self):
        """Pending ESP32 replies are consumed so the receive buffer never fills."""
        self.assertTrue(self.sender.connect())
        conn, _ = self.server.accept()
        conn.sendall(b"ACCELERATE (LED ON)\r\n" * 5)
        time.sleep(0.05)  # let the replies arrive
        self.assertTrue(self.sender.send_action("001"))
        self.assertEqual(conn.recv(16), b"001\n")
        conn.close()

    def test_reconnects_after_server_drops_connection(self):
        self.assertTrue(self.sender.connect())
        conn, _ = self.server.accept()
        conn.close()

        # The drop is noticed within a few sends (FIN/RST propagation is not instant)
        for _ in range(10):
            if not self.sender.send_action("000"):
                break
            time.sleep(0.05)
        self.assertFalse(self.sender.is_connected())

        # With reconnect_interval=0 the next send reconnects immediately
        self.assertTrue(self.sender.send_action("111"))
        conn2, _ = self.server.accept()
        self.assertEqual(conn2.recv(16), b"111\n")
        conn2.close()


if __name__ == '__main__':
    unittest.main()
