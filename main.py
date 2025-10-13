import cv2
import esp32
import handlers
from config import Config
from hand import HandProcessor
from typing import Any


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
        max_hands=config.hand_detection.max_hands
    )

    # Initialize ESP32 client with config
    client_esp32 = esp32.TCPSender(
        ip=config.esp32.ip,
        port=config.esp32.port,
        connection_timeout=config.esp32.connection_timeout
    )
    client_esp32.connect()

    # Init Handler
    handler = handlers.CarHandler(client_esp32)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process the frame to find hands
        detected_hands = hand_processor.process_frame(rgb_frame)

        # Let the handler determine and send actions
        handler.process_hands(detected_hands)

        # Draw info on the frame
        for hand in detected_hands:
            action = handler.get_action(hand)
            hand.draw_info(frame, action)

        cv2.imshow(config.display.window_name, frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    client_esp32.close()
    hand_processor.close()


if __name__ == "__main__":
    main()