#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from px4_msgs.msg import OffboardControlMode, TrajectorySetpoint, VehicleCommand, VehicleLocalPosition, VehicleStatus
from std_msgs.msg import Bool
import time, math
from rclpy.executors import MultiThreadedExecutor
from px4_msgs.msg import GotoSetpoint
import numpy as np  
import array

class OffboardControl(Node):
    """Node for controlling a vehicle in offboard mode."""

    def __init__(self) -> None:
        super().__init__('offboard_control_takeoff')

        # Configure QoS profile for publishing and subscribing
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )

        # Create publishers
        self.offboard_control_mode_publisher = self.create_publisher(
            OffboardControlMode, '/fmu/in/offboard_control_mode', qos_profile)
        self.trajectory_setpoint_publisher = self.create_publisher(
            TrajectorySetpoint, '/fmu/in/trajectory_setpoint', qos_profile)
        self.goto_setpoint_publisher = self.create_publisher(GotoSetpoint, '/fmu/in/goto_setpoint', 10)
        self.vehicle_command_publisher = self.create_publisher(
            VehicleCommand, '/fmu/in/vehicle_command', qos_profile)
        self.vehicle_takeoff_publisher = self.create_publisher(
            Bool, '/takeoff_status', qos_profile)


        # Create subscribers
        self.vehicle_local_position_subscriber = self.create_subscription(
            VehicleLocalPosition, '/fmu/out/vehicle_local_position', self.vehicle_local_position_callback, qos_profile)
        self.vehicle_status_subscriber = self.create_subscription(
            VehicleStatus, '/fmu/out/vehicle_status', self.vehicle_status_callback, qos_profile)
        self.vehicle_trajectory_setpoint_subscriber = self.create_subscription(
            TrajectorySetpoint, '/position_target', self.trajectory_setpoint_callback, qos_profile)
        self.vehicle_goto_setpoint_subscriber = self.create_subscription(
            GotoSetpoint, '/goto_setpoint', self.goto_setpoint_callback, qos_profile)

        # Initialize variables
        self.offboard_setpoint_counter = 0
        self.takeoff_height = 4.0
        self.trajectory_setpoint = TrajectorySetpoint()
        self.goto_setpoint = GotoSetpoint()
        print(self.goto_setpoint)
        self.vehicle_local_position = VehicleLocalPosition()
        self.vehicle_status = VehicleStatus()
        

        # Create a timer to periodically publish control commands
        self.timer1 = self.create_timer(0.1, self.timer1_callback)
        self.timer2 = None

        # Takeoff and Hover state
        self.is_takeoff_complete = Bool()
        self.is_takeoff_complete.data = False
        self.is_hovering = False

    def ned_to_enu(self, x_ned, y_ned, z_ned):
        """Convert NED coordinates to ENU coordinates."""
        x_enu = y_ned
        y_enu = x_ned
        z_enu = -z_ned
        return float(x_enu), float(y_enu), float(z_enu)
    
    def enu_to_ned(self, x_enu, y_enu, z_enu):
        """Convert ENU (East-North-Up) coordinates to NED (North-East-Down) coordinates.

        Returns:
            tuple: Converted (x_ned, y_ned, z_ned) coordinates.
        """
        x_ned = y_enu      # East becomes North
        y_ned = x_enu      # North becomes East
        z_ned = -z_enu     # Up becomes Down
        return float(x_ned), float(y_ned), float(z_ned)

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

    def vehicle_status_callback(self, vehicle_status):
        """Callback function for vehicle_status topic subscriber."""
        self.vehicle_status = vehicle_status

    def trajectory_setpoint_callback(self, trajectory_setpoint):
        self.trajectory_setpoint = trajectory_setpoint

    def goto_setpoint_callback(self, goto_setpoint):
        self.goto_setpoint = goto_setpoint
        # Process speed constraints if they are set
        if goto_setpoint.flag_set_max_horizontal_speed:
            self.get_logger().info(f"Max Horizontal Speed: {goto_setpoint.max_horizontal_speed:.2f} m/s")
        if goto_setpoint.flag_set_max_vertical_speed:
            self.get_logger().info(f"Max Vertical Speed: {goto_setpoint.max_vertical_speed:.2f} m/s")
        if goto_setpoint.flag_set_max_heading_rate:
            self.get_logger().info(f"Max Heading Rate: {goto_setpoint.max_heading_rate:.2f} rad/s")

    def is_trajectory_setpoint_set(self) -> bool:
        """Check if the trajectory_setpoint has been updated."""
        return (
            self.trajectory_setpoint.position != [0.0, 0.0, 0.0] # Check if position is not default
        )

    def is_goto_setpoint_set(self) -> bool:
        """Check if the goto_setpoint has been updated from its default values."""
        default_position = np.array([0., 0., 0.], dtype=np.float32)

        return (
            not np.array_equal(self.goto_setpoint.position, default_position) or
            self.goto_setpoint.flag_control_heading or
            self.goto_setpoint.flag_set_max_horizontal_speed or
            self.goto_setpoint.flag_set_max_vertical_speed or
            self.goto_setpoint.flag_set_max_heading_rate or
            self.goto_setpoint.heading != 0.0 or
            self.goto_setpoint.max_horizontal_speed != 0.0 or
            self.goto_setpoint.max_vertical_speed != 0.0 or
            self.goto_setpoint.max_heading_rate != 0.0
        )

    def arm(self):
        """Send an arm command to the vehicle."""
        self.publish_vehicle_command(
            VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, param1=1.0)
        self.get_logger().info('Arm command sent')
        # identify takeoff position and RTL position
        self.trajectory_setpoint.position[0] = self.vehicle_local_position.x
        self.trajectory_setpoint.position[1] = self.vehicle_local_position.y
        self.trajectory_setpoint.position[2] = self.takeoff_height

    def disarm(self):
        """Send a disarm command to the vehicle."""
        self.publish_vehicle_command(
            VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, param1=0.0)
        self.get_logger().info('Disarm command sent')

    def engage_offboard_mode(self):
        """Switch to offboard mode."""
        self.publish_vehicle_command(
            VehicleCommand.VEHICLE_CMD_DO_SET_MODE, param1=1.0, param2=6.0)
        self.get_logger().info("Switching to offboard mode")

    def publish_offboard_control_heartbeat_signal(self, control_mode='position'):
        """
        Publish the offboard control mode.

        Args:
            control_mode (str): The control mode to use. Options are 'position', 'velocity', 'acceleration',
                                'attitude', or 'body_rate'. Default is 'position'.
        """
        # Create an instance of OffboardControlMode message
        msg = OffboardControlMode()

        # Reset all control modes to False by default
        msg.position = False
        msg.velocity = False
        msg.acceleration = False
        msg.attitude = False
        msg.body_rate = False

        # Set the appropriate control mode based on the argument
        if control_mode == 'position':
            msg.position = True
        elif control_mode == 'velocity':
            msg.velocity = True
        elif control_mode == 'acceleration':
            msg.acceleration = True
        elif control_mode == 'attitude':
            msg.attitude = True
        elif control_mode == 'body_rate':
            msg.body_rate = True
        else:
            # Handle invalid control mode
            self.get_logger().warn(f"Invalid control mode '{control_mode}'. Defaulting to 'position'.")
            msg.position = True  # Default to position if an invalid mode is passed

        # Set the current timestamp (in microseconds)
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)

        # Publish the message
        self.offboard_control_mode_publisher.publish(msg)

    def publish_trajectory_setpoint(self, x: float, y: float, z: float, yaw:float):
        """Publish the trajectory setpoint."""
        msg = TrajectorySetpoint()
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        # Convert the position from ENU (East-North-Up) to NED (North-East-Down) and store as a flat list
        msg.position = list(self.enu_to_ned(x, y, z)) 
        # aligns the yaw to the NED frame
        msg.yaw = -yaw + math.radians(90)
        msg.velocity = [0.0, 0.0, -0.0]
        
        self.trajectory_setpoint_publisher.publish(msg)
        self.get_logger().info(f"Publishing trajectory setpoints in enu {[x, y, z, yaw]}")


    def publish_gotosetpoint(self, x: float, y: float, z: float, **constraints):
        """Publish a GotoSetpoint message with optional constraints.
        Args:
            x (float): Target x-coordinate in ENU frame.
            y (float): Target y-coordinate in ENU frame.
            z (float): Target z-coordinate in ENU frame.
            yaw (float): Target yaw angle in radians.
            **constraints: Optional constraints for speed and heading control.
                        Supported keys: 'heading', 'max_horizontal_speed',
                        'max_vertical_speed', 'max_heading_rate'.
        """
        msg = GotoSetpoint()
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        # Convert position from ENU to NED frame
        msg.position = list(self.enu_to_ned(x, y, z))
        # Control heading if heading is specified
        heading = constraints.get("heading")
        if heading is not None:
            msg.flag_control_heading = True
            msg.heading = -heading + math.radians(90)
        # Set maximum horizontal speed constraint if provided
        max_horizontal_speed = constraints.get("max_horizontal_speed")
        if max_horizontal_speed is not None:
            msg.flag_set_max_horizontal_speed = True
            msg.max_horizontal_speed = max_horizontal_speed
        # Set maximum vertical speed constraint if provided
        max_vertical_speed = constraints.get("max_vertical_speed")
        if max_vertical_speed is not None:
            msg.flag_set_max_vertical_speed = True
            msg.max_vertical_speed = max_vertical_speed
        # Set maximum heading rate constraint if provided
        max_heading_rate = constraints.get("max_heading_rate")
        if max_heading_rate is not None:
            msg.flag_set_max_heading_rate = True
            msg.max_heading_rate = max_heading_rate
            # Publish the message
        self.goto_setpoint_publisher.publish(msg)
        self.get_logger().info(f"Published GotoSetpoint in ENU: Position={[x, y, z]}, Heading={heading:.2f}")


    def publish_vehicle_command(self, command, **params) -> None:
        """Publish a vehicle command."""
        msg = VehicleCommand()
        msg.command = command
        msg.param1 = params.get("param1", 0.0)
        msg.param2 = params.get("param2", 0.0)
        msg.param3 = params.get("param3", 0.0)
        msg.param4 = params.get("param4", 0.0)
        msg.param5 = params.get("param5", 0.0)
        msg.param6 = params.get("param6", 0.0)
        msg.param7 = params.get("param7", 0.0)
        msg.target_system = 1
        msg.target_component = 1
        msg.source_system = 1
        msg.source_component = 1
        msg.from_external = True
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.vehicle_command_publisher.publish(msg)

    def hover_and_react(self):
        """Control vehicle to hover at the takeoff height."""

        self.get_logger().info("Hovering at height: %f" % self.takeoff_height)

        if self.timer2 is None:
            self.get_logger().info(f'Starting timer with 0.1 second interval')
            self.timer2 = self.create_timer(0.1, self.timer2_callback)
        else:
            self.get_logger().info('Timer is already running')

    def timer2_callback(self)-> None:
        #offboard_control_mode needs to be paired with trajectory_setpoint or goto_setpoint
        self.publish_offboard_control_heartbeat_signal()
        self.get_logger().info("publish target position")
        if self.is_goto_setpoint_set():
           print("set check passed, will go to publish goto_setpoint function")
           self.publish_gotosetpoint(self.goto_setpoint.position[0],
                                     self.goto_setpoint.position[1],
                                     self.goto_setpoint.position[2],
                                     heading = self.goto_setpoint.heading,
                                     max_horizontal_speed = self.goto_setpoint.max_horizontal_speed)
        else:
            self.publish_trajectory_setpoint(self.trajectory_setpoint.position[0], 
                                self.trajectory_setpoint.position[1], 
                                self.trajectory_setpoint.position[2], 
                                self.trajectory_setpoint.yaw)

    def timer1_callback(self) -> None:
        """Callback function for the timer."""
        

        if self.offboard_setpoint_counter == 10:
            self.engage_offboard_mode()
            self.arm()

        if self.vehicle_local_position.z < self.takeoff_height:
           #offboard_control_mode needs to be paired with trajectory_setpoint
           self.publish_offboard_control_heartbeat_signal()
           self.publish_trajectory_setpoint(self.vehicle_local_position.x, self.vehicle_local_position.y, self.takeoff_height, 0.0)

        elif self.vehicle_local_position.z > self.takeoff_height - 0.5:
            self.is_takeoff_complete.data = True
            self.vehicle_takeoff_publisher.publish(self.is_takeoff_complete)
            self.hover_and_react()
            self.timer1.cancel()

        if self.offboard_setpoint_counter < 11:
            self.offboard_setpoint_counter += 1

def main(args=None):
    rclpy.init(args=args)
    node = OffboardControl()
    executor = MultiThreadedExecutor()
    try:
        rclpy.spin(node, executor=executor)
    except KeyboardInterrupt:
        node.get_logger().info('Node interrupted by user')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
