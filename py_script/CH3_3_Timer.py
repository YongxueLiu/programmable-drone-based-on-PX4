import rclpy
from rclpy.node import Node


class HelloDroneTimerNode(Node):
    """
    教学示例：ROS 2 多定时器回调节点

    Timer 1：1 Hz，用于模拟低频任务（状态输出、心跳）
    Timer 2：10 Hz，用于模拟高频任务（控制循环）
    """

    def __init__(self):
        super().__init__('hello_drone_timer_node')

        self.counter_1hz = 0
        self.counter_10hz = 0

        # 1 Hz 定时器
        self.timer_1hz = self.create_timer(
            1.0,
            self.timer_1hz_callback
        )

        # 10 Hz 定时器
        self.timer_10hz = self.create_timer(
            0.1,
            self.timer_10hz_callback
        )

        self.get_logger().info("✅ 多定时器节点已启动")

    def timer_1hz_callback(self):
        self.counter_1hz += 1
        self.get_logger().info(
            f"[1 Hz] 状态广播 #{self.counter_1hz} | Hello, programmable drone based on PX4 🚁"
        )

    def timer_10hz_callback(self):
        self.counter_10hz += 1
        self.get_logger().info(
            f"[10 Hz] 控制循环 tick #{self.counter_10hz}"
        )


def main():
    rclpy.init()
    node = HelloDroneTimerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


def main_ctrl_C():
    rclpy.init()
    node = HelloDroneTimerNode()
    try:
        rclpy.spin(node)  # 阻塞运行，处理回调
    except KeyboardInterrupt:
        pass  # 捕获中断信号，抑制异常堆栈输出
    finally:
        # 确保资源有序释放
        node.destroy_node()
        rclpy.shutdown()



if __name__ == '__main__':
    main()