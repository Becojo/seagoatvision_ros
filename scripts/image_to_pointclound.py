#! /usr/bin/env python


import rospy
from sensor_msgs.msg import Image, PointCloud2
import sensor_msgs.point_cloud2 as pc2
import tf
from cv_bridge import CvBridge
import numpy as np
import cv2
import cv2.cv as cv
from math import *

bridge = CvBridge()

# size of the output cloud. total width in meters is (k * w)*100
k = 20.0 # number of points per meter (float)
w = 100 # total points for width
h = 100 # total points for height

x = np.ravel(np.array([[j/k for i in xrange(0, w)] for j in xrange(-h/2,h/2)], dtype=np.float))
y = np.ravel(np.array([[i/k for i in xrange(-w/2, w/2)] for i in xrange(0,h)], dtype=np.float))
z = np.ravel(np.array([[0 for i in xrange(0, w)] for i in xrange(0,h)], dtype=np.float))
points_xyz = np.column_stack((x,y,z))

def handle_image(req):

    start = rospy.get_time()

    # Set up point cloud
    fields = [pc2.PointField() for _ in range(3)]

    fields[0].name = "x"
    fields[0].offset = 0
    fields[0].datatype = pc2.PointField.FLOAT32
    fields[0].count = 1

    fields[1].name = "y"
    fields[1].offset = 4
    fields[1].datatype = pc2.PointField.FLOAT32
    fields[1].count = 1

    fields[2].name = "z"
    fields[2].offset = 8
    fields[2].datatype = pc2.PointField.FLOAT32
    fields[2].count = 1

    field_id = 3
    fields.append(pc2.PointField())
    fields[field_id].name = "intensity"
    fields[field_id].datatype = pc2.PointField.FLOAT32
    fields[field_id].offset = 12
    fields[field_id].count = 1
    idx_intensity = field_id

    # add image
    img = bridge.imgmsg_to_cv2(req, desired_encoding="passthrough")
    img = cv2.cvtColor(img, cv.CV_BGR2GRAY)
    img = cv2.resize(img,(w,h))

    points = np.column_stack((points_xyz, np.flipud(np.ravel(img))))
    points = points[np.logical_not(points[:,3] == 0)]

    header = req.header
    header.frame_id = "img"

    global cloud_out
    cloud_out = pc2.create_cloud(header, fields, points)


class ImageToPointcloud:

    def __init__(self):

        rospy.init_node('image_to_pointcloud')


        topic_in = rospy.get_param('~in', "/image_in")
        topic_out = rospy.get_param('~out', "/cloud")

        rospy.Subscriber(topic_in, Image, handle_image)
        pub = rospy.Publisher(topic_out, PointCloud2, queue_size=2)

        #publish transform to image
        listener = tf.TransformListener()

        real_w = (k * w) /100.0
        real_h = (k * h) /100.0
        rospy.loginfo("Publishing cloud, size: " + str(real_w) + " x " + str(real_h))

        rate = rospy.Rate(50)
        while not rospy.is_shutdown():

            tf_found = False

            try:
                (camTrans,camRotQ) = listener.lookupTransform('/base_footprint', '/camera', rospy.Time(0))
                camRotE = tf.transformations.euler_from_quaternion(camRotQ)

                imgRotE = (-camRotE[0], -camRotE[1], -camRotE[2])
                imgRotQ = tf.transformations.quaternion_from_euler(*imgRotE)
                #print imgRotE

                br = tf.TransformBroadcaster()
                # dist en X = (hauteur camera) / cos(angle entre camera et axe vertical)
                br.sendTransform((-camTrans[2] / cos(imgRotE[1]- pi/2),0.0,0.0),imgRotQ,rospy.Time.now(), "img", "camera")
                if "cloud_out" in globals():
                    global cloud_out
                    pub.publish(cloud_out)

            except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
                # output error only if the tf was previously found and is now lost.
                if tf_found:
                    rospy.logerr("Error looking up tf")

            rate.sleep()


        rospy.spin()


if __name__ == "__main__":
    try:
        s = ImageToPointcloud()
    except rospy.ROSInterruptException:
        pass
