🚁 Programmable Drone Based on PX4 & ROS 2  
🚁 基于 PX4 与 ROS 2 的可编程无人机教程

A hands-on tutorial series teaching drone autonomy using PX4 flight stack and ROS 2. Learn offboard control, precision landing, dynamic obstacle avoidance, YOLO-based tracking, and multi-agent coordination — all while embracing PX4’s design philosophy and ROS 2 best practices.  
一套实战教程系列，基于 PX4 飞控系统与 ROS 2 讲解无人机自主飞行开发。你将系统学习：Offboard 精准控制、厘米级精准降落、动态避障、基于 YOLO 的目标识别与跟踪、多智能体分布式协同——全程遵循 PX4 的设计哲学与 ROS 2 的标准开发范式。本书不仅教你“怎么写代码”，更致力于帮助你建立无人机系统工程思维。

📚 学习目标 | Learning Objectives
章节   内容   Chapter   Content
🎯   Offboard 精准控制通过 ROS 2 发布位置/速度指令，实现稳定飞行   🎯   Offboard ControlStable flight via ROS 2 position/velocity commands

📍   精准降落融合传感器数据实现厘米级定点着陆   📍   Precision LandingCentimeter-level landing with sensor fusion

🚧   动态避障实时点云处理 + 路径重规划   🚧   Dynamic Obstacle AvoidanceReal-time point cloud processing + replanning

👁️   YOLO 目标识别与跟踪检测移动目标并持续追踪   👁️   YOLO TrackingDetect and track moving targets

🤖   多机协同与集群控制基于 DDS 的分布式通信与任务分配   🤖   Multi-Agent CoordinationDDS-based distributed communication & task allocation

📂 项目结构 | Project Structure

bash
programmable-drone-based-on-PX4/
├── CH1_install_px4_ros2_gz_toolchain.sh  # 一键配置 PX4+ROS2+Gazebo 环境
├── CH1_startup.sh                        # 仿真启动脚本（单窗口多标签）
├── CH2_1_hello_world.py                  # ROS 2 基础：Publisher/Subscriber
├── CH2_2_hello_world_oop.py              # 面向对象封装 ROS 2 节点
├── CH3_3_Timer.py                        # 周期性控制（Timer 实现）
├── CH4_2_subscriber.py                   # 订阅无人机状态（位置/姿态）
├── CH4_3_publisher.py                    # 发布 Offboard 控制指令
├── CH5_service.py                        # 调用 PX4 服务（起飞/模式切换）
├── CH6_drone_monitor.py                  # 飞行状态实时监控
├── CH6_drone_takeoff_and_react.py        # 自主起飞 + 环境响应
├── CH6_drone_takeoff_and_react_srv.py    # 基于 Service 的任务触发
└── CH6_flytopos.py                       # 飞行至指定坐标点 (x, y, z)
