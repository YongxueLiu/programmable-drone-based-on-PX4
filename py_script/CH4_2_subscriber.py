import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from px4_msgs.msg import VehicleLocalPosition


class DroneMonitor(Node):
    def __init__(self):
        super().__init__('drone_monitor')
        self.get_logger().info("✅ DroneMonitor 节点初始化成功")

        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )

        self.vehicle_local_position = VehicleLocalPosition()

         # ========== 创建订阅（关键参数说明）==========
        self.subscription = self.create_subscription(
            VehicleLocalPosition,               # 消息类型（PX4 局部位置）
            '/fmu/out/vehicle_local_position',  # 话题名称（PX4 标准输出路径）
            self.vehicle_local_position_callback,
            qos_profile
        )

    def vehicle_local_position_callback(self, msg):
        self.vehicle_local_position = msg
        self.get_logger().info(
            f"Local position: x={msg.x:.2f}, y={msg.y:.2f}, z={msg.z:.2f}"
        )


def main():
    rclpy.init()
    node = DroneMonitor()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

