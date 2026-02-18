#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from px4_msgs.msg import VehicleCommand

class ArmDroneNode(Node):
    """
    最小示例：
    - 创建一个 ROS 2 节点
    - 通过 /fmu/in/vehicle_command 发布 ARM 解锁命令
    """

    def __init__(self):
        super().__init__('arm_drone_node')

        # 创建 VehicleCommand 发布者（PX4 命令入口）
        self.vehicle_command_publisher = self.create_publisher(
            VehicleCommand,
            '/fmu/in/vehicle_command',
            10
        )

        self.get_logger().info("🚀 ArmDroneNode started")

        # 启动后立即发送解锁命令
        self.arm()


    def arm(self):
        """
        发送解锁（ARM）命令给 PX4
        """
        self.get_logger().info("🔓 Sending ARM command...")

        # VEHICLE_CMD_COMPONENT_ARM_DISARM
        # param1 = 1.0 → ARM
        self.publish_vehicle_command(
            VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM,
            param1=1.0
        )

        self.get_logger().info("✅ Arm command published")


    def publish_vehicle_command(self, command, **params):
        """
        构造并发布 VehicleCommand 消息

        Parameters:
        - command : PX4 命令枚举
        - params  : MAVLink command 参数（param1 ~ param7）
        """

        msg = VehicleCommand()

        # ----------- 命令本体 -----------
        msg.command = command
        msg.param1 = params.get("param1", 0.0)
        msg.param2 = params.get("param2", 0.0)
        msg.param3 = params.get("param3", 0.0)
        msg.param4 = params.get("param4", 0.0)
        msg.param5 = params.get("param5", 0.0)
        msg.param6 = params.get("param6", 0.0)
        msg.param7 = params.get("param7", 0.0)

        # ----------- 目标与来源 -----------
        # 通常 system id = 1, component id = 1（飞控）
        msg.target_system = 1
        msg.target_component = 1
        msg.source_system = 1
        msg.source_component = 1

        # 标记该命令来自外部（ROS 2）
        msg.from_external = True

        # PX4 要求使用微秒时间戳
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)

        # ----------- 发布命令 -----------
        try:
            self.vehicle_command_publisher.publish(msg)
        except Exception as e:
            self.get_logger().error(f"❌ Failed to publish vehicle command: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = ArmDroneNode()
    try:
        # spin 让节点保持存活（否则程序会立刻退出）
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

