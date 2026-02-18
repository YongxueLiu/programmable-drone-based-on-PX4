import rclpy
from rclpy.node import Node
def main():

    # ========== 1. 初始化阶段 ==========
    # 初始化 ROS 2 客户端库（所有 ROS 2 程序的第一步）
    rclpy.init()

    # 创建节点实例（节点是 ROS 2 的最小通信与计算单元）
    node = Node('hello_drone_node')

    # ========== 2. 启动提示 ==========
    node.get_logger().info(f"✅ 节点 '{node.get_name()}' 已启动")

    # ========== 3. 主循环 ==========
    iteration = 0  # 迭代计数器
    try:
        # rclpy.ok() 在 Ctrl+C 或 shutdown() 后返回 False
        while rclpy.ok():
            iteration += 1

            node.get_logger().info(f"[循环 #{iteration}] Hello, programmable drone based on PX4 🚁")
            
            # 使用 Python 原生 sleep 实现简单定时
            import time
            time.sleep(1.0)  # 1 Hz 输出频率

    except KeyboardInterrupt:
        # 捕获 Ctrl+C，防止异常堆栈输出
        print("⚠️  检测到 Ctrl+C，中断运行...")

    finally:
        # ========== 4. 资源清理 ==========
        node.destroy_node()   # 显式销毁节点
        rclpy.shutdown()      # 关闭 ROS 2
        print("✅ 节点已安全关闭")


if __name__ == '__main__':
    main()
