import logging
import sys
import time

import cv2
import esp32
import handlers
from config import Config, ConfigError
from draw import Drawer
from hand import HandProcessor, HandType

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    # Load configuration
    try:
        config = Config.from_file()
    except ConfigError as e:
        logger.error("%s", e)
        sys.exit(1)

    # Initialize video capture with config
    cap = cv2.VideoCapture(config.camera.index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.camera.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.camera.height)

    # Initialize hand processor
    hand_processor = HandProcessor(
        min_detection_confidence=config.hand_detection.min_detection_confidence,
        min_tracking_confidence=config.hand_detection.min_tracking_confidence,
        max_hands=config.hand_detection.max_hands,
        open_threshold_ratio=config.hand_detection.open_threshold_ratio,
        index_orientation_threshold=config.hand_detection.index_orientation_threshold
    )

    # Initialize ESP32 client with config
    client_esp32 = esp32.TCPSender(
        ip=config.esp32.ip,
        port=config.esp32.port,
        connection_timeout=config.esp32.connection_timeout
    )
    client_esp32.connect()

    # Init Handler with config
    handler = handlers.CarHandler(
        client_esp32,
        buffer_size=config.handler.buffer_size,
        refresh_interval=config.handler.refresh_interval
    )

    # Init overlay renderer with config
    drawer = Drawer(config.display)

    prev_time = time.monotonic()
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Mirror the frame (selfie view): MediaPipe assigns handedness
            # assuming a mirrored image, so labels match physical hands and
            # the preview behaves like a mirror.
            frame = cv2.flip(frame, 1)

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Process the frame to find hands
            detected_hands = hand_processor.process_frame(rgb_frame)

            # Let the handler determine and send actions
            actions = handler.process_hands(detected_hands)
            confidences = {
                hand_type: handler.get_action_confidence(hand_type)
                for hand_type in (HandType.LEFT, HandType.RIGHT)
            }

            now = time.monotonic()
            fps = 1.0 / max(now - prev_time, 1e-6)
            prev_time = now

            # Draw all overlays, reusing the actions that were sent
            drawer.draw(frame, detected_hands, actions, confidences,
                        client_esp32.is_connected(), fps)

            cv2.imshow(config.display.window_name, frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        client_esp32.close()
        hand_processor.close()


if __name__ == "__main__":
    main()
