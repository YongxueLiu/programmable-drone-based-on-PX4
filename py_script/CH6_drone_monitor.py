#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from px4_msgs.msg import OffboardControlMode, TrajectorySetpoint, VehicleCommand, VehicleLocalPosition, VehicleStatus
from std_msgs.msg import Bool
from px4_msgs.msg import GotoSetpoint

import math

# Define ANSI escape codes for colors
COLOR_RESET = "\033[0m"       # Reset to default color
COLOR_GREEN = "\033[92m"      # Green text
COLOR_YELLOW = "\033[93m"     # Yellow text
COLOR_BLUE = "\033[94m"       # Blue text
COLOR_CYAN = "\033[96m"       # Cyan text
COLOR_RED = "\033[91m"        # Red text

# Define the mapping of navigation state integers to their names
NAVIGATION_STATE_MAP = {
    0: "NAVIGATION_STATE_MANUAL",
    1: "NAVIGATION_STATE_ALTCTL",
    2: "NAVIGATION_STATE_POSCTL",
    3: "NAVIGATION_STATE_AUTO_MISSION",
    4: "NAVIGATION_STATE_AUTO_LOITER",
    5: "NAVIGATION_STATE_AUTO_RTL",
    6: "NAVIGATION_STATE_POSITION_SLOW",
    7: "NAVIGATION_STATE_FREE5",
    8: "NAVIGATION_STATE_FREE4",
    9: "NAVIGATION_STATE_FREE3",
    10: "NAVIGATION_STATE_ACRO",
    11: "NAVIGATION_STATE_FREE2",
    12: "NAVIGATION_STATE_DESCEND",
    13: "NAVIGATION_STATE_TERMINATION",
    14: "NAVIGATION_STATE_OFFBOARD",
    15: "NAVIGATION_STATE_STAB",
    16: "NAVIGATION_STATE_FREE1",
    17: "NAVIGATION_STATE_AUTO_TAKEOFF",
    18: "NAVIGATION_STATE_AUTO_LAND",
    19: "NAVIGATION_STATE_AUTO_FOLLOW_TARGET",
    20: "NAVIGATION_STATE_AUTO_PRECLAND",
    21: "NAVIGATION_STATE_ORBIT",
    22: "NAVIGATION_STATE_AUTO_VTOL_TAKEOFF",
    23: "NAVIGATION_STATE_EXTERNAL1",
    24: "NAVIGATION_STATE_EXTERNAL2",
    25: "NAVIGATION_STATE_EXTERNAL3",
    26: "NAVIGATION_STATE_EXTERNAL4",
    27: "NAVIGATION_STATE_EXTERNAL5",
    28: "NAVIGATION_STATE_EXTERNAL6",
    29: "NAVIGATION_STATE_EXTERNAL7",
    30: "NAVIGATION_STATE_EXTERNAL8",
    31: "NAVIGATION_STATE_MAX",
}

# Define the mapping of arming state integers to their names
ARMING_STATE_MAP = {
    1: "ARMING_STATE_DISARMED",
    2: "ARMING_STATE_ARMED",
}


class DroneMonitor(Node):
    """Node for monitoring vehicle state in offboard mode."""

    def __init__(self) -> None:
        super().__init__('drone_monitor')
        
        # Configure QoS profile for publishing and subscribing
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )

        # Create subscribers
        self.vehicle_local_position_subscriber = self.create_subscription(
            VehicleLocalPosition, '/fmu/out/vehicle_local_position', self.vehicle_local_position_callback, qos_profile)
        self.vehicle_status_subscriber = self.create_subscription(
            VehicleStatus, '/fmu/out/vehicle_status', self.vehicle_status_callback, qos_profile)
        self.vehicle_trajectory_setpoint_subscriber = self.create_subscription(
            TrajectorySetpoint, '/position_target', self.position_target_callback, qos_profile)
        self.vehicle_takeoff_subscriber = self.create_subscription(
            Bool, '/takeoff_status', self.takeoff_status_callback, qos_profile)
        self.vehicle_goto_setpoint_subscriber = self.create_subscription(
            GotoSetpoint, '/goto_setpoint', self.goto_setpoint_callback, qos_profile)

        # Initialize variables
        self.vehicle_local_position = VehicleLocalPosition()
        self.vehicle_status = VehicleStatus()
        self.vehicle_position_target = TrajectorySetpoint()
        self.goto_setpoint  = GotoSetpoint()

        # Create a timer to periodically log data
        self.timer = self.create_timer(1.0, self.timer_callback)
        self.position_target_update_flag = False
        self.goto_setpoint_update_flag = False
        self.is_takeoff_complete = False


    def normalize_angle(self,angle):
        """Normalize an angle to be within the range [-pi, pi]."""
        return (angle + math.pi) % (2 * math.pi) - math.pi


    def takeoff_status_callback(self, takeoff_status):
        self.is_takeoff_complete = takeoff_status.data

    def ned_to_enu(self, x_ned, y_ned, z_ned):
        """Convert NED coordinates to ENU coordinates."""
        x_enu = y_ned
        y_enu = x_ned
        z_enu = -z_ned
        return x_enu, y_enu, z_enu

    def position_target_callback(self, vehicle_position_target):
        """Callback for the trajectory setpoint target position."""
        self.position_target_update_flag = True
        self.vehicle_position_target = vehicle_position_target

    def goto_setpoint_callback(self, vehicle_position_target):
        """Callback for the trajectory setpoint target position."""
        self.goto_setpoint_update_flag = True
        self.goto_setpoint  = vehicle_position_target
        self.vehicle_position_target.position = self.goto_setpoint.position
        self.vehicle_position_target.yaw = self.goto_setpoint.heading


    def vehicle_local_position_callback(self, vehicle_local_position):
        """Callback function for the vehicle_local_position topic subscriber.
        This method receives the current local position from FMU in the NED (North-East-Down) frame
        and converts it to the ENU (East-North-Up) frame for the ROS2 agent to use.
        """
        self.vehicle_local_position = vehicle_local_position
        # Convert position coordinates from NED to ENU (internal representation)
        self.vehicle_local_position.x, self.vehicle_local_position.y, self.vehicle_local_position.z = self.ned_to_enu(
            self.vehicle_local_position.x,
            self.vehicle_local_position.y,
            self.vehicle_local_position.z
        )

        # Adjust the yaw (heading) to align with the ENU frame
        # In ENU, a heading of 0 radians means facing East (positive X direction).
        self.vehicle_local_position.heading = -self.vehicle_local_position.heading + math.radians(90)
        """Normalize an angle to be within the range [-pi, pi]."""
        self.vehicle_local_position.heading = self.normalize_angle(self.vehicle_local_position.heading)

    def vehicle_status_callback(self, vehicle_status):
        """Callback for the vehicle's status."""
        self.vehicle_status = vehicle_status

    def timer_callback(self) -> None:
        """Logs the vehicle's current status and target setpoints."""
        # Log arming state in blue
        arming_state_name = ARMING_STATE_MAP.get(self.vehicle_status.arming_state, "UNKNOWN_ARMING_STATE")
        self.get_logger().info(COLOR_BLUE + f"Arming state: {arming_state_name}" + COLOR_RESET)

        # Log flying mode in green
        state_name = NAVIGATION_STATE_MAP.get(self.vehicle_status.nav_state, "UNKNOWN_STATE")
        self.get_logger().info(COLOR_GREEN + f"Flying mode: {state_name}" + COLOR_RESET)
  
        # Log current position and heading in cyan
        self.get_logger().info(
            COLOR_CYAN +
            f"Current position and heading in ENU: [{self.vehicle_local_position.x:.2f}, "
            f"{self.vehicle_local_position.y:.2f}, "
            f"{self.vehicle_local_position.z:.2f}, "
            f"{self.vehicle_local_position.heading:.2f}]" +
            COLOR_RESET
        )

        # Log current heading in yellow
        # self.get_logger().info(
        #     COLOR_YELLOW +
        #     f"Current heading: {self.vehicle_local_position.heading:.2f}" +
        #     COLOR_RESET
        # )

        # Log received target position in red
        if not self.is_takeoff_complete:
            self.get_logger().info(COLOR_RED +"wait for takeoff to be complete" +  COLOR_RESET)
        else: 
            if self.position_target_update_flag or self.goto_setpoint_update_flag: 
                self.get_logger().info(
                    COLOR_RED +
                    f"Position target in ENU: [{self.vehicle_position_target.position[0]:.2f}, "
                    f"{self.vehicle_position_target.position[1]:.2f}, "
                    f"{self.vehicle_position_target.position[2]:.2f}, "
                    f"Yaw: {self.vehicle_position_target.yaw:.2f}]" +
                    COLOR_RESET
                )
            else:self.get_logger().info(COLOR_RED +"the plane is hovering, with no position targets received" + COLOR_RESET)


def main(args=None) -> None:
    """Main function to initialize and run the node."""
    print('Starting drone monitor node...')
    rclpy.init(args=args)
    node = DroneMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        print('Node interrupted by user.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
