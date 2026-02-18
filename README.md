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

💡 提示：建议将项目目录重命名为无空格路径（如 px4_drone_tutorial），避免 Shell 脚本兼容性问题  
💡 Tip: Rename directory to space-free path (e.g., px4_drone_tutorial) for better script compatibility

🚀 快速开始 | Quick Start

1️⃣ 克隆仓库 | Clone Repository
bash
git clone https://github.com/your-username/programmable-drone-based-on-PX4.git
cd programmable-drone-based-on-PX4
（推荐）重命名目录避免空格问题
mv ../"programmable drone based on PX4" ../px4_drone_tutorial && cd ../px4_drone_tutorial

2️⃣ 一键配置环境 | Setup Environment (Ubuntu 22.04 + ROS 2 Humble)
bash
chmod +x CH1_install_px4_ros2_gz_toolchain.sh
./CH1_install_px4_ros2_gz_toolchain.sh

3️⃣ 启动仿真 | Launch Simulation
bash
chmod +x CH1_startup.sh
./CH1_startup.sh  # 自动在单窗口多标签中启动：Gazebo, PX4, Agent, QGC

4️⃣ 运行示例 | Run Example (New Terminal)
bash
source /opt/ros/humble/setup.bash
python3 CH6_flytopos.py  # 飞行至 (5, 0, 2) 坐标点

🌟 核心理念 | Core Philosophy
原则   说明   Principle   Explanation
✅ 尊重 PX4 架构   通过标准 MAVLink 接口交互，不绕过飞控安全机制   ✅ Respect PX4 Architecture   Interact via standard MAVLink, never bypass flight controller safety

✅ ROS 2 最佳实践   使用 Lifecycle Nodes、QoS、参数服务器等标准机制   ✅ ROS 2 Best Practices   Leverage Lifecycle Nodes, QoS, parameter server

✅ 仿真→真机无缝迁移   SITL 验证逻辑，仅需少量修改即可部署至真实硬件   ✅ SITL to Hardware   Logic validated in simulation, minimal changes for real drone

✅ 工程思维培养   每章聚焦系统设计，而非仅代码片段   ✅ Engineering Mindset   Focus on system design, not just code snippets


Thank you: PX4, ROS 2, and Gazebo open-source communities for their outstanding contributions!  
🌍让无人机开发更简单，让智能飞行触手可及  
🌍Making drone development accessible, one line of code at a time

✅ 使用说明：
复制全部内容 → 保存为项目根目录 README.md
替换 your-username 为你的 GitHub 用户名
（可选）在仓库根目录添加 LICENSE 文件（推荐 MIT）
建议将仓库目录重命名为 无空格路径（如 px4_drone_tutorial），避免脚本执行问题
