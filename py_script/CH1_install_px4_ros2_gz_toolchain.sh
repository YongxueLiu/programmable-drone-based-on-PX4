#!/usr/bin/env bash
# '''
# ================================================================================
# 作者/Author: 刘永学/Liu Yongxue
# 邮箱/Email: 805110687@qq.com
# QQ群：1080856708
# wechat：LingZhiLab

# 版权声明/Copyright Notice:
# © All rights reserved. 保留所有权利。

# 使用许可/Usage License:
# 仅供个人使用，禁止商业用途。
# For personal use only. Commercial use is prohibited.
# ================================================================================
# '''


set -e

echo "================================================="
echo " ROS2 + PX4 + Gazebo 一键开发环境安装脚本 (稳定版)"
echo "================================================="

# ------------------------------------------------
# 检测不要 sudo 运行
# ------------------------------------------------
if [[ $EUID -eq 0 ]]; then
    echo "❌ 请不要使用 sudo 运行脚本"
    echo "正确方式:"
    echo "./install_px4_ros2.sh"
    exit 1
fi

USER_HOME="$HOME"
REAL_USER="$USER"

echo "✔ 当前用户: $REAL_USER"
echo "✔ 用户目录: $USER_HOME"

# ------------------------------------------------
# Ubuntu版本检测
# ------------------------------------------------
UBUNTU_VERSION=$(lsb_release -rs)
UBUNTU_CODENAME=$(lsb_release -cs)

echo "✔ Ubuntu版本: $UBUNTU_VERSION ($UBUNTU_CODENAME)"

if [[ "$UBUNTU_VERSION" == "22.04" ]]; then
    ROS_DISTRO="humble"
elif [[ "$UBUNTU_VERSION" == "24.04" ]]; then
    ROS_DISTRO="jazzy"
else
    echo "❌ 仅支持 Ubuntu 22.04 / 24.04"
    exit 1
fi

echo "✔ ROS2发行版: $ROS_DISTRO"

# ------------------------------------------------
# Locale
# ------------------------------------------------
echo ">>> 配置 locale"

sudo apt update
sudo apt install -y locales

sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8

# ------------------------------------------------
# 基础工具
# ------------------------------------------------
echo ">>> 安装开发工具"

sudo apt install -y \
git \
wget \
curl \
build-essential \
cmake \
ninja-build \
python3-colcon-common-extensions \
python3-pip

# ------------------------------------------------
# ROS2 安装检测
# ------------------------------------------------
if [[ -d "/opt/ros/$ROS_DISTRO" ]]; then
    echo "✔ 检测到 ROS2 已安装: $ROS_DISTRO"
else
    echo ">>> 安装 ROS2"

    sudo apt install -y software-properties-common
    sudo add-apt-repository universe -y

    ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest \
        | grep -F "tag_name" | awk -F\" '{print $4}')

    curl -L -o /tmp/ros2-apt-source.deb \
        "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.${UBUNTU_CODENAME}_all.deb"

    sudo dpkg -i /tmp/ros2-apt-source.deb

    sudo apt update
    sudo apt upgrade -y

    sudo apt install -y ros-${ROS_DISTRO}-desktop

    echo "✔ ROS2 安装完成"
fi

# ------------------------------------------------
# ROS2 bashrc
# ------------------------------------------------
if ! grep -q "/opt/ros/$ROS_DISTRO/setup.bash" ~/.bashrc; then
    echo ">>> 写入 ROS2 bashrc"
    echo "source /opt/ros/$ROS_DISTRO/setup.bash" >> ~/.bashrc
fi

# ------------------------------------------------
# PX4
# ------------------------------------------------
PX4_DIR="$USER_HOME/PX4-Autopilot"

echo ">>> 安装 PX4"

if [[ ! -d "$PX4_DIR" ]]; then
    git clone https://github.com/PX4/PX4-Autopilot.git --recursive "$PX4_DIR"
else
    echo "✔ PX4 已存在"
fi

echo ">>> 安装 PX4 依赖"

cd "$PX4_DIR"
bash Tools/setup/ubuntu.sh

# ------------------------------------------------
# XRCE DDS Agent
# ------------------------------------------------
DDS_DIR="$USER_HOME/Micro-XRCE-DDS-Agent"

echo ">>> 安装 Micro XRCE DDS Agent"

if [[ ! -d "$DDS_DIR" ]]; then
    git clone -b v2.4.3 https://github.com/eProsima/Micro-XRCE-DDS-Agent.git "$DDS_DIR"
fi

cd "$DDS_DIR"

mkdir -p build
cd build

cmake ..
make -j$(nproc)

sudo make install
sudo ldconfig

echo "✔ XRCE DDS Agent 安装完成"

# ------------------------------------------------
# ROS2 PX4 workspace
# ------------------------------------------------
WS_DIR="$USER_HOME/ros2_px4"

echo ">>> 构建 ROS2 PX4 工作空间"

mkdir -p "$WS_DIR/src"

cd "$WS_DIR/src"

if [[ ! -d px4_msgs ]]; then
    git clone https://github.com/PX4/px4_msgs.git
fi

if [[ ! -d px4_ros_com ]]; then
    git clone https://github.com/PX4/px4_ros_com.git
fi

cd "$WS_DIR"

source /opt/ros/$ROS_DISTRO/setup.bash

colcon build

# ------------------------------------------------
# workspace bashrc
# ------------------------------------------------
if ! grep -q "ros2_px4/install/setup.bash" ~/.bashrc; then
    echo "source ~/ros2_px4/install/setup.bash" >> ~/.bashrc
fi

# ------------------------------------------------
# 完成
# ------------------------------------------------
echo
echo "================================================="
echo " 🎉 ROS2 + PX4 + Gazebo 安装完成"
echo "================================================="
echo
echo "PX4目录:"
echo "$PX4_DIR"
echo
echo "ROS2 workspace:"
echo "$WS_DIR"
echo
echo "下一步："
echo
echo "1️⃣ 运行PX4仿真"
echo "cd ~/PX4-Autopilot"
echo "make px4_sitl gz_x500"
echo
echo "2️⃣ 启动XRCE Agent"
echo "MicroXRCEAgent udp4 -p 8888"
echo
echo "3️⃣ 查看ROS2 topic"
echo "ros2 topic list"
echo
echo "================================================="
