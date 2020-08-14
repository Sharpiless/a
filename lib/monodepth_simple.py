# Copyright UCL Business plc 2017. Patent Pending. All rights reserved.
#
# The MonoDepth Software is licensed under the terms of the UCLB ACP-A licence
# which allows for non-commercial use only, the full terms of which are made
# available in the LICENSE file.
#
# For any other use of the software not covered by the UCLB ACP-A Licence,
# please contact info@uclb.com

import cv2
from average_gradients import *
from monodepth_dataloader import *
from monodepth_model import *
import matplotlib.pyplot as plt
import scipy.misc
import tensorflow.contrib.slim as slim
import tensorflow as tf
import time
import re
import argparse
import numpy as np

from tensorflow.python.framework import graph_util
# only keep warnings and errors
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '0'


parser = argparse.ArgumentParser(
    description='Monodepth TensorFlow implementation.')

parser.add_argument('--encoder',          type=str,
                    help='type of encoder, vgg or resnet50', default='resnet50-forward')
parser.add_argument('--image_path',       type=str,
                    help='path to the image', default='./2.png')
parser.add_argument('--checkpoint_path',  type=str,
                    help='path to a specific checkpoint to load', default='./model/model.ckpt')
parser.add_argument('--input_height',     type=int,
                    help='input height', default=256)
parser.add_argument('--input_width',      type=int,
                    help='input width', default=512)

args = parser.parse_args()


def post_process_disparity(disp):
    _, h, w = disp.shape
    l_disp = disp[0, :, :]
    r_disp = np.fliplr(disp[1, :, :])
    m_disp = 0.5 * (l_disp + r_disp)
    l, _ = np.meshgrid(np.linspace(0, 1, w), np.linspace(0, 1, h))
    l_mask = 1.0 - np.clip(20 * (l - 0.05), 0, 1)
    r_mask = np.fliplr(l_mask)
    return r_mask * l_disp + l_mask * r_disp + (1.0 - l_mask - r_mask) * m_disp


def test_simple(params):
    """Test function."""

    left = tf.placeholder(
        tf.float32, [2, args.input_height, args.input_width, 3])
    model = MonodepthModel(params, "test", left, None, None, None, None)
    input_image = cv2.imread(args.image_path)
    input_image = cv2.cvtColor(input_image, cv2.COLOR_BGR2RGB)
    original_height, original_width, num_channels = input_image.shape
    input_image = cv2.resize(
        input_image, (int(args.input_width), int(args.input_height)))
    input_image = input_image.astype(np.float32) / 255
    input_images = np.stack((input_image, np.fliplr(input_image)), 0)

    # SESSION
    config = tf.ConfigProto(allow_soft_placement=True)
    train_saver = tf.train.Saver()
    with tf.Session(config=config) as sess:
        # INIT
        sess.run(tf.global_variables_initializer())

        # RESTORE
        restore_path = args.checkpoint_path
        train_saver.restore(sess, restore_path)
        print(model.invDepth_left_est[0])
        print(left)
        frozen_list = ['Placeholder', 'model/resnet50-forward/Conv_80/Sigmoid']
        constant_graph = graph_util.convert_variables_to_constants(sess, sess.graph_def, frozen_list)
        with tf.gfile.FastGFile('model.pb', mode='wb') as f:
            f.write(constant_graph.SerializeToString())

        disp = sess.run(model.invDepth_left_est[0], feed_dict={
                        left: input_images})
        disp_pp = post_process_disparity(disp.squeeze()).astype(np.float32)

        output_directory = os.path.dirname(args.image_path)
        output_name = os.path.splitext(os.path.basename(args.image_path))[0]

        disp_to_img = cv2.resize(
            disp_pp.squeeze(), (original_width, original_height))
        plt.imsave(os.path.join(output_directory, "{}_disp.png".format(
            output_name)), disp_to_img, cmap='jet')
        plt.imshow(disp_to_img, cmap='jet')
        plt.show()

    print('done!')


def main(_):

    params = monodepth_parameters(
        encoder=args.encoder,
        height=args.input_height,
        width=args.input_width,
        batch_size=2,
        num_threads=1,
        num_epochs=1,
        do_stereo=False,
        wrap_mode="border",
        use_deconv=False,
        alpha_image_loss=0,
        disp_gradient_loss_weight=0,
        lr_loss_weight=0,
        full_summary=False,
        lidar_weight=15.0,
        do_gradient_fix=True)

    test_simple(params)


if __name__ == '__main__':
    tf.app.run()
