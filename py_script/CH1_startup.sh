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
# ============================================================
# PX4 + Gazebo + ROS2 + QGroundControl 一键仿真启动脚本
#
# Author: UAV Dev Lab
# Description:
#   工业级仿真启动脚本
#
# 启动顺序:
#   1 PX4 SITL
#   2 MicroXRCEAgent
#   3 QGroundControl
#
# 特性:
#   自动下载 QGC
#   自动初始化 Gazebo worlds
#   自动依赖检查
#   日志管理
# ============================================================

set -e

# ============================================================
# 基本配置
# ============================================================

PX4_PATH="$HOME/PX4-Autopilot"
QGC_PATH="$HOME/bin/QGroundControl.AppImage"

GZ_WORLD_PATH="$HOME/.simulation-gazebo/worlds/"
GZ_SIM_SCRIPT="$PX4_PATH/Tools/simulation/gz/simulation-gazebo"

PX4_MODEL="gz_x500"
WORLD_NAME="default"

LOG_DIR="$HOME/.px4_sim_logs"
mkdir -p "$LOG_DIR"

# ============================================================
# 颜色输出
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================================
# 打印函数
# ============================================================

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }

# ============================================================
# 依赖检查
# ============================================================

check_dependencies() {

log_info "检查系统依赖..."

source ~/.bashrc
command -v ros2 >/dev/null || { log_error "ROS2 未安装"; exit 1; }
command -v gnome-terminal >/dev/null || { log_error "gnome-terminal 未安装"; exit 1; }
command -v wget >/dev/null || { log_error "wget 未安装"; exit 1; }

[[ -d "$PX4_PATH" ]] || { log_error "PX4 路径不存在: $PX4_PATH"; exit 1; }

log_ok "依赖检查通过"

}

# ============================================================
# 初始化 Gazebo worlds
# ============================================================

init_gazebo_worlds() {

if [[ ! -d "$GZ_WORLD_PATH" ]]; then

log_warn "未发现 Gazebo worlds"

#mkdir -p "$GZ_WORLD_PATH"

log_info "初始化 Gazebo worlds..."

(
cd "$(dirname "$GZ_SIM_SCRIPT")"
python3 "$GZ_SIM_SCRIPT"
)

if [[ ! -f "$GZ_WORLD_PATH/$WORLD_NAME.sdf" ]]; then
log_error "world 文件生成失败"
exit 1
fi

log_ok "Gazebo worlds 初始化完成"

else

log_ok "Gazebo worlds 已存在"

fi

}

# ============================================================
# 初始化 QGroundControl
# ============================================================

init_qgc() {

if [[ ! -f "$QGC_PATH" ]]; then

log_warn "未检测到 QGroundControl"

mkdir -p "$HOME/bin"

QGC_URL="https://d176tv9ibo4jno.cloudfront.net/latest/QGroundControl-x86_64.AppImage"

log_info "下载 QGroundControl..."

wget -O "$QGC_PATH" "$QGC_URL"

chmod +x "$QGC_PATH"

log_info "安装 QGC 依赖..."

sudo usermod -a -G dialout $USER
sudo apt-get remove modemmanager -y
sudo apt update
sudo apt install -y \
gstreamer1.0-plugins-bad \
gstreamer1.0-libav \
gstreamer1.0-gl \
libfuse2 \
libxcb-xinerama0 \
libxkbcommon-x11-0

log_ok "QGroundControl 初始化完成"

else

log_ok "QGroundControl 已安装"

fi

}

# ============================================================
# 启动 PX4 SITL
# ============================================================

start_px4() {

log_info "启动 PX4 SITL..."

gnome-terminal --tab --title="PX4 SITL" -- bash -c "

cd $PX4_PATH

export PX4_SIM_MODEL=$PX4_MODEL

echo 'PX4 SITL 启动中...'

make px4_sitl $PX4_MODEL

read
"

sleep 5

log_ok "PX4 启动完成"

}

# ============================================================
# 启动 MicroXRCEAgent
# ============================================================

start_agent() {

log_info "启动 MicroXRCEAgent..."

gnome-terminal --tab --title="MicroXRCEAgent" -- bash -c "

echo '等待 PX4 连接...'

MicroXRCEAgent udp4 -p 8888

read
"

sleep 5

log_ok "MicroXRCEAgent 启动完成"

}

# ============================================================
# 启动 QGroundControl
# ============================================================

start_qgc() {

log_info "启动 QGroundControl..."

gnome-terminal --tab --title="QGroundControl" -- bash -c "

$QGC_PATH

"

log_ok "QGroundControl 已启动"

}

# ============================================================
# 清理函数
# ============================================================

cleanup() {

log_warn "停止仿真环境..."

pkill -f px4 || true
pkill -f MicroXRCEAgent || true
pkill -f QGroundControl || true

log_ok "环境已关闭"

exit 0

}

trap cleanup SIGINT SIGTERM

# ============================================================
# 主函数
# ============================================================

main() {

echo
echo "=========================================="
echo " PX4 + Gazebo + ROS2 仿真启动器"
echo "=========================================="
echo

check_dependencies

init_gazebo_worlds

init_qgc

start_px4

start_agent

start_qgc

log_ok "仿真环境已全部启动"

echo
echo "连接检查:"
echo "QGC: UDP 14550"
echo "ROS2 topic:"
echo "   ros2 topic list | grep fmu"
echo

wait

}

main
