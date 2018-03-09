#!/usr/bin/env python
"""
This component generates a list of poses around a target pose based on a set of
parameters (SphericalSamplerParameters).

**Input(s):**
  * `target_pose`: The target pose from which to create a set of poses around that
  object.
  * `sampling_parameters`: A message specifying the parameters, and constraints,
  of the pose to be sampled around an object, if any.

**Output(s):**
  * `poses_list`: The list of poses around the target pose as defined by the
  `sampling_parameters`.

**Parameter(s):**
  * `linear_step`: Sampling step for linear variables (in meters).
  * `angular_step`: Sampling step for angular variables (in degrees).
  * `max_poses`: Maximum amount of samples to be generated (int).
  * `gripper`: Configuration matrix of the gripper to be used (as a string).
  * `loop_rate`: Node cycle rate (in hz).

"""
#-*- encoding: utf-8 -*-

import math
import tf
import rospy
import mcr_pose_generation.transformations as transformations
import mcr_pose_generation_ros.pose_generator_utils as utils
import std_msgs.msg
import geometry_msgs.msg
import mcr_manipulation_msgs.msg


class PoseGenerator:
    """
    Generates a list of Cartesian poses, based on the specified spherical sample
    parameters and their constraints.

    """
    def __init__(self):
        # the sampling step for linear variables (in meters)
        self.linear_step = 0.01
        # the sampling step for angular variables (in radians)
        self.angular_step =  math.pi/12
        # the maximum amount of samples to be generated
        self.max_samples = 50

        self.gripper_config_matrix = None

    def set_linear_step(self, linear_step):
        self.linear_step = linear_step

    def set_angular_step(self, angular_step):
        self.angular_step = angular_step

    def set_max_samples(self, max_samples):
        self.max_samples = max_samples

    def set_gripper_config_matrix(self, gripper_config_matrix):
        self.gripper_config_matrix = gripper_config_matrix


    def calculate_poses_list(self, target_pose, sample_parameters, number_of_fields=5):
        """
        Calculates a list of poses around a target pose based on the spherical sampler parameters.

        :param target_pose: The target pose.
        :type target_pose: geometry_msgs.msg.PoseStamped()

        :param sample_parameters: The parameters to specify a spherical sampling.
        :type sample_parameters: mcr_manipulation_msgs.msg.SphericalSamplerParameters()

        :param number_of_fields: The number of fields the SphericalSamplerParameters
            message has.
        :type number_of_fields: int

        :return: A list of poses around the target pose.
        :rtype: geometry_msgs.msg.PoseArray()

        """
        poses = geometry_msgs.msg.PoseArray()
        poses.header.frame_id = target_pose.header.frame_id
        poses.header.stamp = target_pose.header.stamp

        object_matrix = tf.transformations.quaternion_matrix([
            target_pose.pose.orientation.x, target_pose.pose.orientation.y,
            target_pose.pose.orientation.z, target_pose.pose.orientation.w
        ])
        object_matrix[0, 3] = target_pose.pose.position.x
        object_matrix[1, 3] = target_pose.pose.position.y
        object_matrix[2, 3] = target_pose.pose.position.z

        height_offsets = utils.generate_samples(
            sample_parameters.height.minimum, sample_parameters.height.maximum,
            self.linear_step, (self.max_samples / number_of_fields)
        )
        zeniths = utils.generate_samples(
            sample_parameters.zenith.minimum, sample_parameters.zenith.maximum,
            self.angular_step, (self.max_samples / number_of_fields)
        )
        azimuths = utils.generate_samples(
            sample_parameters.azimuth.minimum, sample_parameters.azimuth.maximum,
            self.angular_step, (self.max_samples / number_of_fields)
        )
        wrist_rolls = utils.generate_samples(
            sample_parameters.yaw.minimum, sample_parameters.yaw.maximum,
            self.angular_step, (self.max_samples / number_of_fields)
        )
        radials = utils.generate_samples(
            sample_parameters.radial_distance.minimum,
            sample_parameters.radial_distance.maximum, self.linear_step,
            (self.max_samples / number_of_fields)
        )

        transforms = [
            transformations.generate_grasp_matrix(
                object_matrix, self.gripper_config_matrix, height_offset,
                zenith, azimuth, wrist_roll, radial
            ) for height_offset in height_offsets for zenith in zeniths
            for azimuth in azimuths for wrist_roll in wrist_rolls for radial in radials
        ]

        for transform in transforms:
            pose = utils.matrix_to_pose(transform)
            poses.poses.append(pose)

        return poses

    def reset_component_data(self):
        """
        Clears the data of the component.

        """
        self.event = None
        self.target_pose = None
        self.sampling_parameters = None


def main():
    rospy.init_node('pose_generator_node', anonymous=True)
    pose_generator = PoseGenerator()
    pose_generator.start()