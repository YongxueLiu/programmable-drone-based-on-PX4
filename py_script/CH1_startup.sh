

#!/bin/bash
# =========================================================
# PX4 + Gazebo + ROS2 无人机仿真环境自动化启动脚本
# 严格启动顺序：Gazebo → PX4 → ROS-GZ Bridge → MicroXRCEAgent → QGC
# 使用 gnome-terminal 在不同标签页启动
# =========================================================

set -e  # 遇到错误时退出

# === 配置路径（根据你的环境调整） ===
GZ_WORLD_PATH="$HOME/.simulation-gazebo/worlds"
PX4_PATH="$HOME/PX4-Autopilot"
PYTHON_ENV_PATH="$HOME/myenv/bin/activate"
QGC_PATH="$HOME/bin/QGroundControl-x86_64.AppImage"
ROS_DISTRO= $ROS_DISTRO   # 或 humble, iron, jazzy

# 仿真参数
WORLD_NAME="default"
PX4_MODEL="gz_x500"

# =========================================================
#  Gazebo worlds 自动初始化
# =========================================================
init_gazebo_worlds() {
    if [[ ! -d "$GZ_WORLD_PATH" ]]; then
        echo -e "${YELLOW}⚠️ 未发现 Gazebo worlds: $GZ_WORLD_PATH${NC}"
        echo -e "${BLUE}➡️ 初始化 simulation-gazebo 资源...${NC}"

        [[ -d "$GZ_SIM_PATH" ]] || {
            echo -e "${RED}❌ 找不到 simulation/gz 路径: $GZ_SIM_PATH${NC}"
            exit 1
        }

        # mkdir -p "$HOME/.simulation-gazebo"

        (
            cd "$GZ_SIM_PATH"
            echo -e "${BLUE}运行: python3 simulation-gazebo${NC}"
            python3 simulation-gazebo
        )

        if [[ ! -d "$GZ_WORLD_PATH" ]]; then
            echo -e "${RED}❌ Gazebo worlds 初始化失败${NC}"
            exit 1
        fi

        echo -e "${GREEN}✅ Gazebo worlds 初始化完成${NC}"
    else
        echo -e "${GREEN}✅ Gazebo worlds 已存在${NC}"
    fi
}

# =========================================================
#  QGroundControl 自动下载
# =========================================================
init_qgroundcontrol() {
    if [[ ! -f "$QGC_PATH" ]]; then
        echo -e "${YELLOW}⚠️ 未发现 QGroundControl${NC}"
        echo -e "${BLUE}➡️ 下载 QGroundControl AppImage...${NC}"

        mkdir -p "$HOME/bin"

        wget -O "$QGC_PATH" "$QGC_URL" || {
            echo -e "${RED}❌ QGroundControl 下载失败${NC}"
            exit 1
        }

        chmod +x "$QGC_PATH"

        echo -e "${BLUE}➡️ 安装 QGroundControl 运行依赖（需要 sudo）...${NC}"

        sudo apt update
        sudo apt install -y \
            gstreamer1.0-plugins-bad \
            gstreamer1.0-libav \
            gstreamer1.0-gl \
            libfuse2 \
            libxcb-xinerama0 \
            libxkbcommon-x11-0 \
            libxcb-cursor-dev || {
                echo -e "${RED}❌ QGroundControl 依赖安装失败${NC}"
                exit 1
            }

        echo -e "${GREEN}✅ QGroundControl 下载并初始化完成${NC}"
    else
        echo -e "${GREEN}✅ QGroundControl 已存在，跳过下载和依赖安装${NC}"
    fi
}

# === 依赖检查 ===
echo "🔍 检查依赖..."
command -v gnome-terminal >/dev/null 2>&1 || { echo "错误: 需要安装 gnome-terminal"; exit 1; }
command -v ros2 >/dev/null 2>&1 || { echo "错误: 需要安装 ROS2"; exit 1; }
[[ -d "$PX4_PATH" ]] || { echo "错误: PX4 路径不存在: $PX4_PATH"; exit 1; }
[[ -d "$GZ_WORLD_PATH" ]] || { echo "错误: Gazebo 路径不存在: $GZ_WORLD_PATH"; exit 1; }

# Source ROS2
source /opt/ros/$ROS_DISTRO/setup.bash

# === 颜色输出 ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# === 启动函数 ===
start_gazebo() {
    echo -e "${YELLOW}=== 1️⃣ 启动 Gazebo 仿真 ===${NC}"
    gnome-terminal --tab --title="🗺️ Gazebo ($WORLD_NAME)" -- bash -c "
        cd '$GZ_WORLD_PATH';
        echo '🚀 启动 Gazebo 世界: $WORLD_NAME';
        echo '等待 Gazebo 完全启动...';
        python3 simulation-gazebo --world $WORLD_NAME;
        echo 'Gazebo 已停止，按 Enter 关闭窗口...';
        read;
    " &
    GZ_PID=$!
    echo -e "${GREEN}Gazebo 启动中 (PID: $GZ_PID)${NC}"
    
    # 等待 Gazebo 启动
    echo -e "${BLUE}等待 Gazebo 启动完成 (10秒)...${NC}"
    sleep 10
}

start_px4() {
    echo -e "${YELLOW}=== 2️⃣ 启动 PX4 SITL ===${NC}"
    gnome-terminal --tab --title="🛫 PX4 SITL ($PX4_MODEL)" -- bash -c "
        cd '$PX4_PATH';
        echo '🛫 启动 PX4 SITL: $PX4_MODEL';
        echo '确保 Gazebo 已运行...';
        export PX4_SIM_MODEL=$PX4_MODEL;
        make px4_sitl $PX4_MODEL;
        echo 'PX4 已停止，按 Enter 关闭窗口...';
        read;
    " &
    PX4_PID=$!
    echo -e "${GREEN}PX4 启动中 (PID: $PX4_PID)${NC}"
    
    # 等待 PX4 连接 Gazebo
    echo -e "${BLUE}等待 PX4 连接 Gazebo (15秒)...${NC}"
    sleep 15
}


start_micro_agent() {
    echo -e "${YELLOW}=== 4️⃣ 启动 MicroXRCEAgent ===${NC}"
    gnome-terminal --tab --title="📡 MicroXRCEAgent" -- bash -c "
        cd '$PX4_PATH';
        echo '📡 启动 MicroXRCEAgent (UDP port 8888)';
        echo '等待 PX4 客户端连接...';
        MicroXRCEAgent udp4 -p 8888;
        echo 'Agent 已停止，按 Enter 关闭窗口...';
        read;
    " &
    AGENT_PID=$!
    echo -e "${GREEN}MicroXRCEAgent 启动中 (PID: $AGENT_PID)${NC}"
    sleep 5
}

start_qgroundcontrol() {
    if [[ -f "$QGC_PATH" ]]; then
        echo -e "${YELLOW}=== 5️⃣ 启动 QGroundControl ===${NC}"
        gnome-terminal --tab --title="🛰️ QGroundControl" -- bash -c "
            echo '🛰️ 启动 QGroundControl 地面站';
            echo '连接到 PX4 SITL (UDP 14550)...';
            '$QGC_PATH';
            echo 'QGC 已关闭';
        " &
        QGC_PID=$!
        echo -e "${GREEN}QGroundControl 启动中 (PID: $QGC_PID)${NC}"
    else
        echo -e "${RED}⚠️ QGroundControl 未找到: $QGC_PATH${NC}"
        echo -e "${YELLOW}请手动启动: $QGC_PATH${NC}"
    fi
    sleep 2
}



# === 清理函数 ===
cleanup() {
    echo -e "\n${RED}=== 停止仿真环境 ===${NC}"
    echo "终止进程: GZ($GZ_PID), PX4($PX4_PID), Bridge($BRIDGE_PID), Agent($AGENT_PID)"
    kill $GZ_PID $PX4_PID $BRIDGE_PID $AGENT_PID $QGC_PID $ENV_PID 2>/dev/null || true
    pkill -f "QGroundControl\|MicroXRCEAgent\|ros_gz_bridge\|simulation-gazebo" 2>/dev/null || true
    echo -e "${GREEN}清理完成${NC}"
    exit 0
}

# 捕获 Ctrl+C
trap cleanup SIGINT SIGTERM

# === 主启动流程 ===
echo -e "${GREEN}🚁 PX4 + Gazebo + ROS2 仿真环境启动${NC}"
echo -e "${BLUE}ROS 版本: $ROS_DISTRO | 世界: $WORLD_NAME | 模型: $PX4_MODEL${NC}"
echo "================================================================"

# 1. 启动 Gazebo
start_gazebo

# 2. 启动 PX4
start_px4


# 3. 启动 MicroXRCEAgent
start_micro_agent

# 5. 启动 QGroundControl
start_qgroundcontrol


# === 验证和提示 ===
echo -e "\n${GREEN}✅ 所有组件启动完成！${NC}"
echo -e "${YELLOW}=== 验证检查 ===${NC}"
echo "1. 检查 ROS2 话题:"
echo "   ros2 topic list | grep -E '(rgb|depth|camera|fmu)'"
echo "2. 检查 PX4 连接:"
echo "   ros2 topic list | grep fmu"
echo "3. QGC 连接: UDP 14550 (默认)"
echo "4. Python 环境: 运行你的 VO/VIO 节点"

echo -e "\n${RED}停止脚本: Ctrl+C 或关闭所有终端${NC}"
echo -e "${YELLOW}日志查看: ~/.ros/log/ 最新的日志文件${NC}"

# 保持脚本运行，监控进程
echo -e "\n${BLUE}监控进程状态 (按 Ctrl+C 停止)...${NC}"
wait
