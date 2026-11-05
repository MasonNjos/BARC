
"""
Standalone sanity check: publishes robot_state_publisher +
joint_state_publisher_gui from this package's xacro file.

Run:
    ros2 launch robot2 description.launch.py
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


dirName = "robot2"
fileName = "robot2.xacro"


def generate_launch_description():
    pkg_share = get_package_share_directory(dirName)
    default_xacro_path = os.path.join(pkg_share, "xacro", fileName)

    declare_model = DeclareLaunchArgument(
        "model",
        default_value=default_xacro_path,
        description="Absolute path to the robot xacro/urdf file",
    )

    robot_description = ParameterValue(
        Command(["xacro ", LaunchConfiguration("model")]),
        value_type=str,
    )

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[
            {"robot_description": robot_description},
            {"use_tf_static": False},
            {"publish_frequency": 200.0},
            {"ignore_timestamp": True},
            {"use_sim_time": False},
        ],
    )

    joint_state_publisher_gui_node = Node(
        package="joint_state_publisher_gui",
        executable="joint_state_publisher_gui",
        output="screen",
    )

    return LaunchDescription(
        [
            declare_model,
            robot_state_publisher_node,
            joint_state_publisher_gui_node,
        ]
    )
