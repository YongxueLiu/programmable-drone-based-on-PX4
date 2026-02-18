import rclpy
from rclpy.node import Node
import time

class HelloDroneNode(Node):

 
    def __init__(self):
        # 初始化父类 Node，并指定节点名
        super().__init__('hello_drone_node')

        self.iteration = 0

        self.get_logger().info(f"✅ 节点 '{self.get_name()}' 已启动（OOP 方式）")

    def run(self):
        try:
            while rclpy.ok():
                self.iteration += 1

                self.get_logger().info(
                    f"[循环 #{self.iteration}] Hello, programmable drone based on PX4 🚁")

                time.sleep(1.0)

        except KeyboardInterrupt:
            print("⚠️  检测到 Ctrl+C，中断运行")

        finally:
            self.destroy_node()
            rclpy.shutdown()
            print("✅ 节点已安全关闭")


def main():
    # 初始化 ROS 2
    rclpy.init()

    # 创建节点对象
    node = HelloDroneNode()

    # 运行节点逻辑
    node.run()


if __name__ == '__main__':
    main()
