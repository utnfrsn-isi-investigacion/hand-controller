import hand
import cv2
import esp32


def main() -> None:
    cap = cv2.VideoCapture(0)
    detector = hand.HandGestureDetector()  # Single reusable instance
    client_esp32 = esp32.TCPSender(ip='esp32.local', port=1234)
    client_esp32.connect()
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = detector.hands.process(rgb_frame)

        if results.multi_hand_landmarks:
            for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                handedness = results.multi_handedness[idx]

                # Reload detector instance with new hand data
                detector.reload(handedness, hand_landmarks)

                # Skip if hand is not fully visible
                if not detector.is_hand_fully_visible():
                    continue

                # Get the action using the new method
                action = detector.get_action()

                # Set label position based on hand type
                x_label = 50 if detector.hand_type() == hand.HandType.LEFT else 350
                if client_esp32.is_connected():
                    client_esp32.send_action(detector)
                # Draw info on the frame
                detector.draw_hand_info(frame, hand_landmarks, x_label, action)


        cv2.imshow("Hand Gesture Recognition", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
