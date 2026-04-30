#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image

class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')

        # Último depth recibido
        self.last_depth = None

        # Subscribers normales (sin message_filters)
        self.rgb_sub = self.create_subscription(
            Image,
            '/camera/camera/color/image_raw',
            self.rgb_callback,
            10
        )

        self.depth_sub = self.create_subscription(
            Image,
            '/camera/camera/aligned_depth_to_color/image_raw',
            self.depth_callback,
            10
        )

        # Publishers
        self.rgb_pub = self.create_publisher(Image, '/perception/rgb', 10)
        self.depth_pub = self.create_publisher(Image, '/perception/depth', 10)

        self.get_logger().info('Camera node ready')

    def depth_callback(self, msg):
        # Guardas el último depth siempre
        self.last_depth = msg

    def rgb_callback(self, msg):
        # Publicas RGB siempre
        self.rgb_pub.publish(msg)

        # Solo publicas depth si ya tienes uno
        if self.last_depth is not None:
            self.depth_pub.publish(self.last_depth)
            
def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()