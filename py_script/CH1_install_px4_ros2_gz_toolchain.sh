#!/usr/bin/env bash
set -e

echo "=============================================="
echo " ROS 2 + PX4 + Gazebo 一键开发仿真环境安装脚本"
echo "=============================================="

# -----------------------------
# 基本环境检测
# -----------------------------
if [[ $EUID -ne 0 ]]; then
    echo "❌ 请使用 sudo 运行该脚本"
    exit 1
fi

UBUNTU_VERSION=$(lsb_release -rs)
UBUNTU_CODENAME=$(lsb_release -cs)

echo "✔ 检测到 Ubuntu 版本: ${UBUNTU_VERSION} (${UBUNTU_CODENAME})"

# -----------------------------
# Locale（ROS 2 必需）
# -----------------------------
echo ">>> 配置 locale (UTF-8)"
apt update
apt install -y locales
locale-gen en_US en_US.UTF-8
update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8

# shellcheck disable=SC1091
source /etc/default/locale

# -----------------------------
# ROS 2 安装
# -----------------------------
echo ">>> 安装 ROS 2"

apt install -y software-properties-common curl
add-apt-repository universe -y

ROS_DISTRO=""

if [[ "$UBUNTU_VERSION" == "22.04" ]]; then
    ROS_DISTRO="humble"
elif [[ "$UBUNTU_VERSION" == "24.04" ]]; then
    ROS_DISTRO="jazzy"
else
    echo "❌ 不支持的 Ubuntu 版本"
    exit 1
fi

echo "✔ ROS 2 发行版: ${ROS_DISTRO}"

ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest \
    | grep -F "tag_name" | awk -F\" '{print $4}')

curl -L -o /tmp/ros2-apt-source.deb \
    "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.${UBUNTU_CODENAME}_all.deb"

dpkg -i /tmp/ros2-apt-source.deb

apt update
apt upgrade -y
apt install -y ros-${ROS_DISTRO}-desktop

# 添加到 bashrc
if ! grep -q "source /opt/ros/${ROS_DISTRO}/setup.bash" ~/.bashrc; then
    echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc
fi

# -----------------------------
# PX4 源码与依赖
# -----------------------------
echo ">>> 克隆 PX4-Autopilot"

PX4_DIR="$HOME/PX4-Autopilot"

if [[ ! -d "$PX4_DIR" ]]; then
    sudo -u "$SUDO_USER" git clone https://github.com/PX4/PX4-Autopilot.git --recursive "$PX4_DIR"
else
    echo "✔ PX4-Autopilot 已存在，跳过 clone"
fi

echo ">>> 安装 PX4 Ubuntu 依赖（ubuntu.sh脚本包括安装gz）"
bash "$PX4_DIR/Tools/setup/ubuntu.sh"

# -----------------------------
# Micro XRCE-DDS Agent
# -----------------------------
echo ">>> 安装 Micro XRCE-DDS Agent"

DDS_DIR="$HOME/Micro-XRCE-DDS-Agent"

if [[ ! -d "$DDS_DIR" ]]; then
    sudo -u "$SUDO_USER" git clone -b v2.4.3 https://github.com/eProsima/Micro-XRCE-DDS-Agent.git "$DDS_DIR"
fi

cd "$DDS_DIR"
mkdir -p build
cd build
cmake ..
make -j$(nproc)
make install
ldconfig /usr/local/lib/

# -----------------------------
# ROS 2 PX4 工作空间
# -----------------------------
echo ">>> 构建 ROS 2 PX4 工作空间"

WS_DIR="$HOME/ros2_px4"

sudo -u "$SUDO_USER" mkdir -p "$WS_DIR/src"
cd "$WS_DIR/src"

if [[ ! -d px4_msgs ]]; then
    sudo -u "$SUDO_USER" git clone https://github.com/PX4/px4_msgs.git
fi

if [[ ! -d px4_ros_com ]]; then
    sudo -u "$SUDO_USER" git clone https://github.com/PX4/px4_ros_com.git
fi

cd "$WS_DIR"

# shellcheck disable=SC1091
source /opt/ros/${ROS_DISTRO}/setup.bash

sudo -u "$SUDO_USER" colcon build

# 添加 workspace 到 bashrc
if ! grep -q "source ~/ros2_px4/install/setup.bash" ~/.bashrc; then
    echo "source ~/ros2_px4/install/setup.bash" >> ~/.bashrc
fi

# -----------------------------
# 完成
# -----------------------------
echo "=============================================="
echo "🎉 ros2+px4+gz安装完成！"
echo
echo "下一步建议："
echo "1️⃣ 新终端运行 PX4 仿真："
echo "   cd ~/PX4-Autopilot && make px4_sitl gz_x500"
echo
echo "2️⃣ 启动 XRCE-DDS Agent："
echo "   MicroXRCEAgent udp4 -p 8888"
echo
echo "3️⃣ ROS 2 查看话题："
echo "   ros2 topic list"
echo "=============================================="

