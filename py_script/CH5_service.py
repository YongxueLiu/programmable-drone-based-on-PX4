#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from functools import partial
from px4_msgs.msg import VehicleCommand
# PX4 的服务类型（由 px4_ros_com 提供）
from px4_msgs.srv import VehicleCommand as VehicleCommandSrv


class OffboardControl(Node):
    """
    最小 PX4 Service Client 示例
    功能：通过 Service 发送 VehicleCommand（上锁 / 解锁）
    """

    def __init__(self, ):
        super().__init__('offboard_control_srv')

        # 创建 VehicleCommand 服务客户端
        # 对应 PX4 暴露的 /fmu/vehicle_command 服务
        self.vehicle_command_client = self.create_client(
            VehicleCommandSrv,
             '/fmu/vehicle_command'
        )

        self.get_logger().info('Waiting for PX4 vehicle_command service...')

        # 等待 PX4 服务就绪
        while not self.vehicle_command_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Service not available, retrying...')

        self.get_logger().info('PX4 vehicle_command service available')

        # 示例：启动后直接发送 Disarm 命令
        self.disarm()

    def disarm(self):
        """
        请求 PX4 执行上锁（Disarm）
        """
        self.get_logger().info('Requesting DISARM')
        self.send_vehicle_command(
            VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM,
            param1=0.0   # 0.0 → Disarm，1.0 → Arm
        )


    def send_vehicle_command(self, command, param1=0.0, param2=0.0):
        """
        构造并发送 VehicleCommand 的 Service 请求
        """

        # ---------- 构造 PX4 命令 ----------
        cmd = VehicleCommand()
        cmd.command = command
        cmd.param1 = float(param1)
        cmd.param2 = float(param2)
        # PX4 系统 / 组件 ID（仿真与实机中通常为 1）
        cmd.target_system = 1
        cmd.target_component = 1
        cmd.source_system = 1
        cmd.source_component = 1
        # 标记为外部（ROS 2）指令
        cmd.from_external = True
        # PX4 使用微秒级时间戳
        cmd.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        # ---------- 封装为 Service Request ----------
        request = VehicleCommandSrv.Request()
        request.request = cmd
        # ---------- 异步调用服务 ----------
        future = self.vehicle_command_client.call_async(request)
        future.add_done_callback(
            partial(self.response_callback)
        )


    def response_callback(self, future):
        """
        处理 PX4 返回的服务响应
        """
        try:
            response = future.result()
            result = response.reply.result

            if result == response.reply.VEHICLE_CMD_RESULT_ACCEPTED:
                self.get_logger().info('Command ACCEPTED by PX4')
            else:
                self.get_logger().warn(f'Command rejected, result={result}')
        except Exception as e:
            self.get_logger().error(f'Service call failed: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = OffboardControl()
    # 使用多线程执行器，避免服务回调阻塞节点
    executor = MultiThreadedExecutor()
    try:
        rclpy.spin(node, executor=executor)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
