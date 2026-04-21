import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import cv2
from cv_bridge import CvBridge
import os

class CaptureNode(Node):
    def __init__(self):
        super().__init__('capture_node')

        self.bridge = CvBridge()
        self.count = 0

        os.makedirs("calib_images", exist_ok=True)

        self.sub = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.callback,
            10
        )

    def callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        cv2.imshow("frame", frame)

        key = cv2.waitKey(1)

        if key == ord('s'):
            filename = f"calib_images/img_{self.count}.png"
            cv2.imwrite(filename, frame)
            print(f"Saved {filename}")
            self.count += 1

def main():
    rclpy.init()
    node = CaptureNode()
    rclpy.spin(node)

if __name__ == '__main__':
    main()