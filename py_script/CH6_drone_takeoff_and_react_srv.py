import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from functools import partial
from px4_msgs.msg import OffboardControlMode, TrajectorySetpoint, VehicleCommand, VehicleLocalPosition
from px4_msgs.srv import VehicleCommand as VehicleCommandSrv
from time import sleep
from std_msgs.msg import Bool
import math


class OffboardControl(Node):
    """Node for offboard control using PX4 services."""

    def __init__(self, px4_namespace):
        super().__init__('offboard_control_srv')
        self.state = 'init'
        self.service_result = 0
        self.takeoff_height = 5.0
        self.service_done = False
        self.vehicle_local_position = VehicleLocalPosition()
        self.position_target = TrajectorySetpoint()
        self.is_takeoff_complete = Bool()
        self.is_takeoff_complete.data = False

        # Configure QoS profile for publishing and subscribing
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )


        # Publishers for OffboardControlMode, Trajectory Setpoint, takeoff_status
        self.offboard_control_mode_publisher = self.create_publisher(
            OffboardControlMode, px4_namespace + 'in/offboard_control_mode', qos_profile)
        self.trajectory_setpoint_publisher = self.create_publisher(
            TrajectorySetpoint, px4_namespace + 'in/trajectory_setpoint', qos_profile)
        self.vehicle_takeoff_publisher = self.create_publisher(
            Bool, '/takeoff_status', qos_profile)
        
        # Subscriber
        self.vehicle_trajectory_setpoint_subscriber = self.create_subscription(
            TrajectorySetpoint, '/position_target', self.position_target_callback, qos_profile)
        self.vehicle_local_position_subscriber = self.create_subscription(
            VehicleLocalPosition, '/fmu/out/vehicle_local_position', self.vehicle_local_position_callback, qos_profile)

        # Client for VehicleCommand service
        self.vehicle_command_client = self.create_client(
            VehicleCommandSrv, px4_namespace + 'vehicle_command')

        self.get_logger().info('Starting Offboard Control with PX4 services')
        self.get_logger().info(f'Waiting for {px4_namespace}vehicle_command service')

        while not self.vehicle_command_client.wait_for_service(timeout_sec=1.0):
            if not rclpy.ok():
                self.get_logger().error('Interrupted while waiting for the service. Exiting.')
                return
            self.get_logger().info('Service not available, waiting again...')

        # Timer for periodic tasks (100 ms)
        self.timer1 = self.create_timer(1, self.timer1_callback)
        self.timer2 = None

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


    def position_target_callback(self, position_target):
        self.position_target.position = position_target.position
        self.position_target.yaw = position_target.yaw

    def switch_to_offboard_mode(self):
        self.get_logger().info('Requesting switch to Offboard mode')
        self.request_vehicle_command(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, 1, 6)

    def arm(self):
        self.get_logger().info('Requesting arm')
        self.request_vehicle_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 1.0)
        # record takeoff position and RTL position
        self.position_target.position[0] = self.vehicle_local_position.x
        self.position_target.position[1] = self.vehicle_local_position.y
        self.position_target.position[2] = self.takeoff_height

    def disarm(self):
        self.get_logger().info('Requesting disarm')
        self.request_vehicle_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 0.0)

    def publish_offboard_control_mode(self):
        """Publish OffboardControlMode to enable position control."""
        msg = OffboardControlMode()
        msg.position = True
        msg.velocity = False
        msg.acceleration = False
        msg.attitude = False
        msg.body_rate = False
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.offboard_control_mode_publisher.publish(msg)

    def publish_trajectory_setpoint(self, x: float, y: float, z: float, yaw:float):
        """Publish the trajectory setpoint."""
        msg = TrajectorySetpoint()
        # Convert the position from ENU (East-North-Up) to NED (North-East-Down) and store as a flat list
        msg.position = list(self.enu_to_ned(x, y, z)) 
        # aligns the yaw to the NED frame
        msg.yaw = -yaw + math.radians(90)
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.trajectory_setpoint_publisher.publish(msg)
        self.get_logger().info(f"Publishing position setpoints and yaw {[x, y, z, yaw]}")

    def request_vehicle_command(self, command, param1=0.0, param2=0.0):
        """Send a vehicle command request."""
        request = VehicleCommandSrv.Request()
        msg = VehicleCommand()
        # Ensure the parameters are floats
        msg.param1 = float(param1)
        msg.param2 = float(param2)
        msg.command = command
        msg.target_system = 1
        msg.target_component = 1
        msg.source_system = 1
        msg.source_component = 1
        msg.from_external = True
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        request.request = msg
        self.service_done = False
        future = self.vehicle_command_client.call_async(request)
        print(f'future:{future}')
        future.add_done_callback(partial(self.response_callback))
        self.get_logger().info('Command sent')

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


    def response_callback(self, future):
        """Handle the response from the vehicle command service."""
        try:
            response = future.result()
            print(f'response:{response}')
            reply = response.reply
            self.service_result = response.reply.result
            if self.service_result == reply.VEHICLE_CMD_RESULT_ACCEPTED:
                self.get_logger().info('Command accepted')
            elif self.service_result == reply.VEHICLE_CMD_RESULT_TEMPORARILY_REJECTED:
                self.get_logger().warn('Command temporarily rejected')
            elif self.service_result == reply.VEHICLE_CMD_RESULT_DENIED:
                self.get_logger().warn('Command denied')
            elif self.service_result == reply.VEHICLE_CMD_RESULT_UNSUPPORTED:
                self.get_logger().warn('Command unsupported')
            elif self.service_result == reply.VEHICLE_CMD_RESULT_FAILED:
                self.get_logger().warn('Command failed')
            elif self.service_result == reply.VEHICLE_CMD_RESULT_IN_PROGRESS:
                self.get_logger().warn('Command in progress')
            elif self.service_result == reply.VEHICLE_CMD_RESULT_CANCELLED:
                self.get_logger().warn('Command cancelled')
            else:
                self.get_logger().warn('Command reply unknown')
            self.service_done = True

        except Exception as e:
            self.get_logger().error(f'Service call failed: {e}')

    def hover_and_react(self):
        """Control vehicle to hover at the takeoff height."""

        self.get_logger().info("Hovering at height: %f" % self.takeoff_height)

        if self.timer2 is None:
            self.get_logger().info(f'Starting timer2 with 0.1 second interval')
            self.timer2 = self.create_timer(0.1, self.timer2_callback)
        else:
            self.get_logger().info('Timer2 is already running')

    def timer2_callback(self)-> None:
        #offboard_control_mode needs to be paired with trajectory_setpoint
        self.publish_offboard_control_mode()
        self.publish_trajectory_setpoint(self.position_target.position[0], 
                                        self.position_target.position[1], 
                                        self.position_target.position[2], 
                                        self.position_target.yaw)


    def timer1_callback(self):
        """Main state machine for offboard control."""
        if self.vehicle_local_position.z < self.takeoff_height:
            for i in range(10):
                self.publish_offboard_control_mode()
                self.publish_trajectory_setpoint(self.position_target.position[0], self.position_target.position[1], self.takeoff_height, 0.0)
            
        elif self.vehicle_local_position.z > self.takeoff_height - 0.1:
            self.is_takeoff_complete.data = True
            self.vehicle_takeoff_publisher.publish(self.is_takeoff_complete)
            self.hover_and_react()
            self.timer1.cancel()

        if self.state == 'init':
            self.switch_to_offboard_mode()
            self.state = 'offboard_requested'

        elif self.state == 'offboard_requested' and self.service_done:
            if self.service_result == 0:
                self.get_logger().info('Entered offboard mode')
                self.state = 'wait_for_stable_offboard_mode'
            else:
                self.get_logger().error('Failed to enter offboard mode, try again')
                self.state = 'init'
        elif self.state == 'wait_for_stable_offboard_mode':
            sleep(1)  # Stabilization delay
            self.arm()
            self.state = 'arm_requested'

        elif self.state == 'arm_requested' and self.service_done:
            if self.service_result == 0:
                self.get_logger().info('Vehicle is armed')
                self.state = 'armed'
            else:
                self.get_logger().error('Failed to arm, try again')
                self.state == 'wait_for_stable_offboard_mode'

def main(args=None):
    rclpy.init(args=args)
    node = OffboardControl('/fmu/')
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
