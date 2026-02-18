#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from px4_msgs.msg import OffboardControlMode, TrajectorySetpoint, VehicleLocalPosition
import math
from std_msgs.msg import Bool
import time
from px4_msgs.msg import GotoSetpoint

# Define tolerances for distance and yaw
DISTANCE_TOLERANCE = 0.5  # meters
YAW_TOLERANCE = 0.1       # radians

class OffboardControl(Node):
    """Node for controlling a vehicle in offboard mode."""

    def __init__(self) -> None:
        super().__init__('offboard_control')

        # Configure QoS profile for publishing and subscribing
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )

        # Create publishers
        self.trajectory_setpoint_publisher = self.create_publisher(
            TrajectorySetpoint, '/position_target', qos_profile)
        self.vehicle_goto_setpoint_publisher  = self.create_publisher(
            GotoSetpoint, '/goto_setpoint', qos_profile)

        # Create subscribers
        self.vehicle_local_position_subscriber = self.create_subscription(
            VehicleLocalPosition, '/fmu/out/vehicle_local_position', self.vehicle_local_position_callback, qos_profile)
        self.vehicle_takeoff_subscriber = self.create_subscription(
            Bool, '/takeoff_status', self.takeoff_status_callback, qos_profile)

        # Initialize vehicle position
        self.vehicle_local_position = VehicleLocalPosition()
        self.timer = None  # Timer for periodic callbacks
        self.is_takeoff_complete = True
        self.target_reached = False

    def takeoff_status_callback(self, takeoff_status):
        """Callback for takeoff status updates."""
        self.is_takeoff_complete = takeoff_status.data
        self.get_logger().info(f"Takeoff status: {'Complete' if self.is_takeoff_complete else 'Incomplete'}")

    
    def vehicle_local_position_callback(self, vehicle_local_position):
        """Callback function for the vehicle_local_position topic subscriber.
        This method receives the current local position from FMU in the NED (North-East-Down) frame
        and converts it to the ENU (East-North-Up) frame for the ROS2 agent to use.
        """
        # Store the received vehicle local position message
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

    def ned_to_enu(self, x_ned, y_ned, z_ned):
        """Convert NED coordinates to ENU coordinates.
           Returns:
           tuple: Converted (x_enu, y_enu, z_enu) coordinates.
        """
        x_enu = y_ned
        y_enu = x_ned
        z_enu = -z_ned
        return x_enu, y_enu, z_enu
    
    def enu_to_ned(self, x_enu, y_enu, z_enu):
        """Convert ENU (East-North-Up) coordinates to NED (North-East-Down) coordinates.

        Returns:
            tuple: Converted (x_ned, y_ned, z_ned) coordinates.
        """
        x_ned = y_enu      # East becomes North
        y_ned = x_enu      # North becomes East
        z_ned = -z_enu     # Up becomes Down
        return x_ned, y_ned, z_ned


    def publish_trajectory_setpoint(self, x: float, y: float, z: float, yaw: float):
        """Publish the trajectory setpoint."""
        msg = TrajectorySetpoint()
        msg.position = [x, y, z]
        msg.yaw = yaw
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.trajectory_setpoint_publisher.publish(msg)
        self.get_logger().info(f"Publishing position setpoint: {[x, y, z]}, yaw: {yaw}")

    def publish_goto_setpoint(self, x: float, y: float, z: float, yaw: float, **args):

        msg = GotoSetpoint()
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        msg.position = [x, y, z]
        msg.heading = yaw
        max_horizontal_speed = args.get("max_horizontal_speed", 10)
        msg.flag_set_max_horizontal_speed = True
        msg.max_horizontal_speed = float(max_horizontal_speed)
        self.vehicle_goto_setpoint_publisher.publish(msg)
    

    def fly_to_trajectory_position(self, x: float, y: float, z: float, yaw: float):
        """Fly the vehicle to the specified position and yaw."""
        if self.timer is None:
            self.timer = self.create_timer(1, lambda: self.timer_callback(x, y, z, yaw))
            self.get_logger().info("Flight timer started.")

    def fly_to_position(self, x: float, y: float, z: float, yaw: float, max_horizontal_speed: float, sleep_duration: float = 1.0):
        """
        Fly the vehicle to the specified position (x, y, z) and yaw orientation with a given horizontal speed limit.

        This function does not use timers, so it needs to be executed in a separate thread to avoid blocking the current event loop.
        
        Args:
            x (float): Target position along the X-axis (NED frame) in meters.
            y (float): Target position along the Y-axis (NED frame) in meters.
            z (float): Target position along the Z-axis (NED frame) in meters.
            yaw (float): Target yaw angle in radians (range: -π to +π).
            max_horizontal_speed (float): The maximum allowable horizontal speed in meters per second.
            sleep_duration (float): Time to wait (in seconds) between position updates. Default is 1.0 second.
        """

        # Publish the initial position setpoint to the vehicle
        self.publish_goto_setpoint(x, y, z, yaw, max_horizontal_speed=max_horizontal_speed)

        while True:
            # Calculate the remaining distance to the target position
            dx = self.vehicle_local_position.x - x
            dy = self.vehicle_local_position.y - y
            dz = self.vehicle_local_position.z - z
            remaining_distance = math.sqrt(dx ** 2 + dy ** 2 + dz ** 2)  # Euclidean distance to the target

            # Calculate the remaining yaw difference
            remaining_yaw = abs(self.normalize_yaw(self.vehicle_local_position.heading - yaw))  # Ensure yaw difference is within valid range

            # Log the current status: remaining distance and yaw
            self.get_logger().info(f'Remaining distance: {remaining_distance:.4f} m, Remaining yaw: {remaining_yaw:.4f} rad')

            # Check if the vehicle is within the specified tolerances for position and yaw
            if remaining_distance <= DISTANCE_TOLERANCE and remaining_yaw <= YAW_TOLERANCE:
                break  # Exit the loop once the target is reached

            # Sleep for the specified duration to avoid frequent updates and reduce CPU load
            time.sleep(sleep_duration)

        # Log that the target position has been reached
        self.get_logger().info('Target position reached.')

        # Set the flag to indicate the target has been reached
        self.target_reached = True


    def timer_callback(self, x: float, y: float, z: float, yaw: float):
        """Callback function for the timer to check position and cancel when reached."""
        self.publish_trajectory_setpoint(x, y, z, yaw)

        # Calculate remaining distance to target position
        remaining_distance = math.sqrt(
            (self.vehicle_local_position.x - x) ** 2 +
            (self.vehicle_local_position.y - y) ** 2 +
            (self.vehicle_local_position.z - z) ** 2
        )
        # Calculate remaining yaw difference
        remaining_yaw = abs(self.normalize_yaw(self.vehicle_local_position.heading - yaw))
        self.get_logger().info(f'Remaining distance: {remaining_distance:.4f}, Remaining yaw: {remaining_yaw:.4f}')
        if remaining_distance < DISTANCE_TOLERANCE and remaining_yaw < YAW_TOLERANCE:
            self.get_logger().info('Target position reached. Stopping the timer.')
            if self.timer:
                self.timer.cancel()
                self.timer = None
            self.target_reached = True

    def normalize_yaw(self, yaw_diff: float) -> float:
        """Normalize yaw to be within the range [-pi, pi]."""
        while yaw_diff > math.pi:
            yaw_diff -= 2 * math.pi
        while yaw_diff < -math.pi:
            yaw_diff += 2 * math.pi
        return abs(yaw_diff)


def get_target_position(node):
    """Prompt the user to input target position and yaw angle."""
    try:
        input_str = input("Enter target position X, Y, Z (meters, ENU) and yaw (radians), separated by commas: ")
        values = [float(item.strip()) for item in input_str.split(',')]
        if len(values) != 4:
            raise ValueError("Exactly four values are required.")
        node.get_logger().info(f"Received target position: x={values[0]}, y={values[1]}, z={values[2]}, yaw={values[3]}")
        return values
    except ValueError as e:
        node.get_logger().error(f"Invalid input format: {e}")
        return None


def main(args=None) -> None:
    """Main function to start the offboard control node."""
    rclpy.init(args=args)
    node = OffboardControl()
    node.get_logger().info('Starting offboard control node...')

    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.1)

            if not node.is_takeoff_complete:
                node.get_logger().info("Waiting for takeoff to complete...")
                continue

            target = get_target_position(node)
            if target:
                x, y, z, yaw = target
                node.fly_to_trajectory_position(x, y, z, yaw)
                node.target_reached = False

                # Wait until the target is reached
                while not node.target_reached and rclpy.ok():
                    rclpy.spin_once(node, timeout_sec=0.1)

    except KeyboardInterrupt:
        node.get_logger().info('Node interrupted by user.')

    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
