#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from message_filters import ApproximateTimeSynchronizer, Subscriber

class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')

        # Subscribers a los topics que ya publica tu driver Astra
        self.rgb_sub = Subscriber(self, Image, '/camera/image_raw')
        self.depth_sub = Subscriber(self, Image, '/camera/depth/image_raw')

        # Sincronización temporal RGB + Depth
        self.sync = ApproximateTimeSynchronizer(
            [self.rgb_sub, self.depth_sub],
            queue_size=10,
            slop=0.1  # 50ms de tolerancia
        )
        self.sync.registerCallback(self.callback)

        # Re-publica sincronizados
        self.rgb_pub = self.create_publisher(Image, '/perception/rgb', 10)
        self.depth_pub = self.create_publisher(Image, '/perception/depth', 10)

        self.get_logger().info('Camera node ready')

    def callback(self, rgb_msg, depth_msg):
        self.rgb_pub.publish(rgb_msg)
        self.depth_pub.publish(depth_msg)

def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()