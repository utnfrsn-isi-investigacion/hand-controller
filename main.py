import hand
import cv2
import esp32
import numpy as np
import numpy.typing as npt
from config import Config
from typing import Any, Tuple, Optional

# Type alias for OpenCV images
CVImage = npt.NDArray[np.uint8]


def main() -> None:
    # Load configuration
    config: Config = Config.from_file()
    
    # Initialize video capture with config
    cap: cv2.VideoCapture = cv2.VideoCapture(config.camera.index)
    
    # Set camera resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.camera.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.camera.height)
    
    # Initialize hand detector
    detector: hand.HandGestureDetector = hand.HandGestureDetector()
    
    # Initialize ESP32 client with config
    client_esp32: esp32.TCPSender = esp32.TCPSender(
        ip=config.esp32.ip,
        port=config.esp32.port,
        action_cooldown=config.esp32.action_cooldown,
        connection_timeout=config.esp32.connection_timeout
    )
    client_esp32.connect()
    
    while True:
        ret: bool
        frame: Any  # cv2.typing.MatLike
        ret, frame = cap.read()
        if not ret:
            break

        rgb_frame: Any = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # cv2.typing.MatLike
        results: Any = detector.hands.process(rgb_frame)

        if results.multi_hand_landmarks:
            hand_landmarks: Any
            for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                handedness: Any = results.multi_handedness[idx]

                # Reload detector instance with new hand data
                detector.reload(handedness, hand_landmarks)

                # Skip if hand is not fully visible
                if not detector.is_hand_fully_visible():
                    continue

                # Get the action using the new method
                action: hand.Action = detector.get_action()

                # Set label position based on hand type
                x_label: int = 50 if detector.hand_type() == hand.HandType.LEFT else 350
                if client_esp32.is_connected():
                    client_esp32.send_action(detector)
                # Draw info on the frame
                detector.draw_hand_info(frame, hand_landmarks, x_label, action)


        cv2.imshow(config.display.window_name, frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    client_esp32.close()


if __name__ == "__main__":
    main()
