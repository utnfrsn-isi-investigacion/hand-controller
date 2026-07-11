import time

import cv2
import esp32
import handlers
from config import Config
from hand import HandProcessor, HandType


def draw_connection_status(frame, connected: bool) -> None:
    """Draw the ESP32 connection state in the top-left corner of the preview."""
    if connected:
        text, color = "ESP32: connected", (0, 255, 0)
    else:
        text, color = "ESP32: disconnected (reconnecting...)", (0, 0, 255)
    cv2.putText(frame, text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)


def main() -> None:
    # Load configuration
    config = Config.from_file()

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

            # Draw info on the frame, reusing the actions that were sent
            for hand in detected_hands:
                hand_type = hand.get_hand_type()
                if hand_type == HandType.UNKNOWN:
                    continue
                hand.draw_info(frame, actions[hand_type], show_landmarks=config.display.show_landmarks)

            draw_connection_status(frame, client_esp32.is_connected())

            now = time.monotonic()
            fps = 1.0 / max(now - prev_time, 1e-6)
            prev_time = now
            if config.display.show_fps:
                cv2.putText(frame, f"FPS: {fps:.0f}", (10, frame.shape[0] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

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
