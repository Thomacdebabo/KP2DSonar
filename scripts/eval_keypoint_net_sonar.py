# Copyright 2020 Toyota Research Institute.  All rights reserved.
# Example usage: python scripts/eval_keypoint_net.sh --pretrained_model /data/models/kp2dsonar/v4.pth --input_dir /data/datasets/kp2dsonar/HPatches/

import argparse

import torch
import os
import json

from datetime import datetime
from termcolor import colored
from torch.utils.data import DataLoader

from kp2dsonar.datasets.sonarsim import SonarSimLoader
from kp2dsonar.evaluation.evaluate import evaluate_keypoint_net_sonar
from kp2dsonar.networks.keypoint_net import KeypointNet
from kp2dsonar.networks.keypoint_resnet import KeypointResnet
from kp2dsonar.datasets.augmentations import to_tensor_sonar_sample, resize_sample
from kp2dsonar.datasets.noise_model import NoiseUtility

def _print_result(result_dict):
    for k in result_dict.keys():
        print("%s: %.3f" %( k, result_dict[k]))

def _load_model(model_path, device):
    checkpoint = torch.load(model_path, map_location=torch.device(device))
    model_args = checkpoint['config']['model']['params']

    print('Loaded KeypointNet from {}'.format(model_path))
    print('KeypointNet params {}'.format(model_args))
    print(checkpoint['config'])

    if 'keypoint_net_type' in checkpoint['config']['model']['params']:
        net_type = checkpoint['config']['model']['params']['keypoint_net_type']
    else:
        net_type = 'KeypointNet'  # default when no type is specified

    if net_type == 'KeypointNet':
        keypoint_net = KeypointNet(use_color=model_args['use_color'],
                                   do_upsample=model_args['do_upsample'],
                                   do_cross=model_args['do_cross'])
    elif net_type == 'KeypointResnet':
        keypoint_net = KeypointResnet()
    else:
        raise KeyError("net_type not recognized: " + str(net_type))

    keypoint_net.load_state_dict(checkpoint['state_dict'])
    keypoint_net = keypoint_net.to(device)
    keypoint_net.eval()

    return keypoint_net, checkpoint['config']

def image_transforms(noise_util):
    def train_transforms(sample):
        sample = resize_sample(sample, image_shape=noise_util.shape)

        sample = noise_util.pol_2_cart_sample(sample)
        sample = noise_util.augment_sample(sample)

        sample = noise_util.filter_sample(sample)
        sample = noise_util.cart_2_pol_sample(sample)
        if noise_util.post_noise:
            sample = noise_util.add_noise_function(sample)
        sample = to_tensor_sonar_sample(sample)


        return sample

    return {'train': train_transforms}

def main():

    parser = argparse.ArgumentParser(
        description='Script for KeyPointNet testing',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--input_dir", required=True, type=str, help="Folder containing input images")
    parser.add_argument("--device", required=False, type=str, help="cuda or cpu", default='cpu')

    args = parser.parse_args()

    model_paths = [r"C:\Users\Dr. Paul von Immel\Downloads\sonar_sim_noise\V4_A4.ckpt",
                   r"C:\Users\Dr. Paul von Immel\Downloads\sonar_sim_noise\V_6.ckpt",
                   r"C:\Users\Dr. Paul von Immel\Downloads\sonar_sim_noise\V_5.ckpt",
                   r"C:\Users\Dr. Paul von Immel\Downloads\sonar_sim_noise\row.ckpt",
                   r"D:\PycharmProjects\KP2D\data\models\kp2d\v4.ckpt"]


    top_k = 1500
    res = 512
    conf_threshold = 0.9
    debug = True

    eval_params = [
        {'name': 'V6 V4_A4 config',
         'res': (res, res),
         'top_k': top_k,
         'fov': 60,
         'r_min': 0.1,
         'r_max': 5.0,
         'super_resolution': 1,
         'normalize': True,
         'preprocessing_gradient': True,
         'add_row_noise': True,
         'add_artifact': True,
         'add_sparkle_noise': False,
         'add_normal_noise': False,
         'add_speckle_noise': False,
         'blur': True,
         'patch_ratio': 0.8,
         'scaling_amplitude': 0.2,
         'max_angle_div': 12},
        {'name': 'V5 config',
         'res': (res, res),
         'top_k': top_k,
         'fov': 60,
         'r_min': 0.1,
         'r_max': 5.0,
         'super_resolution': 1,
         'normalize': True,
         'preprocessing_gradient': True,
         'add_row_noise': True,
         'add_artifact': True,
         'add_sparkle_noise': True,
         'add_normal_noise': False,
         'add_speckle_noise': False,
         'blur': True,
         'patch_ratio': 0.8,
         'scaling_amplitude': 0.2,
         'max_angle_div': 12},  # decided to not copy these values due to it being not very good at evaluating if big
        {'name': 'only row noise',
         'res': (res, res),
         'top_k': top_k,
         'fov': 60,
         'r_min': 0.1,
         'r_max': 5.0,
         'super_resolution': 1,
         'normalize': False,
         'preprocessing_gradient': False,
         'add_row_noise': True,
         'add_artifact': False,
         'add_sparkle_noise': False,
         'add_normal_noise': False,
         'add_speckle_noise': False,
         'blur': False,
         'patch_ratio': 0.8,
         'scaling_amplitude': 0.2,
         'max_angle_div': 12},
        {'name': 'no noise at all',
         'res': (res, res),
         'top_k': top_k,
         'fov': 60,
         'r_min': 0.1,
         'r_max': 5.0,
         'super_resolution': 1,
         'normalize': False,
         'preprocessing_gradient': False,
         'add_row_noise': False,
         'add_artifact': False,
         'add_sparkle_noise': False,
         'add_normal_noise': False,
         'add_speckle_noise': False,
         'blur': False,
         'patch_ratio': 0.8,
         'scaling_amplitude': 0.2,
         'max_angle_div': 4},
        {'name': 'all the noise',
         'res': (res, res),
         'top_k': top_k,
         'fov': 60,
         'r_min': 0.1,
         'r_max': 5.0,
         'super_resolution': 1,
         'normalize': True,
         'preprocessing_gradient': True,
         'add_row_noise': True,
         'add_artifact': True,
         'add_sparkle_noise': True,
         'add_normal_noise': False,
         'add_speckle_noise': True,
         'blur': True,
         'patch_ratio': 0.8,
         'scaling_amplitude': 0.2,
         'max_angle_div': 4}
    ]

    evaluation_results = {}

    for model_path in model_paths:

        keypoint_net, config = _load_model(model_path, args.device)
        model_name = model_path.split('\\')[-1]

        results = []

        for params in eval_params:
            run_name = model_name + " - " + params['name']

            noise_util = NoiseUtility(params['res'],
                                      fov=params['fov'],
                                      r_min=params['r_min'],
                                      r_max=params['r_max'],
                                      super_resolution=params['super_resolution'],
                                      normalize=params['normalize'],
                                      preprocessing_gradient=params['preprocessing_gradient'],
                                      add_row_noise=params['add_row_noise'],
                                      add_artifact=params['add_artifact'],
                                      add_sparkle_noise=params['add_sparkle_noise'],
                                      add_normal_noise=params['add_normal_noise'],
                                      add_speckle_noise=params['add_speckle_noise'],
                                      blur=params['blur'],
                                      patch_ratio=params['patch_ratio'],
                                      scaling_amplitude=params['scaling_amplitude'],
                                      max_angle_div=params['max_angle_div'])

            data_transforms = image_transforms(noise_util)
            hp_dataset = SonarSimLoader(args.input_dir, noise_util,data_transform=data_transforms['train'])
            data_loader = DataLoader(hp_dataset,
                                     batch_size=1,
                                     pin_memory=False,
                                     shuffle=False,
                                     num_workers=0,
                                     worker_init_fn=None,
                                     sampler=None)

            print(colored('Evaluating for {} -- top_k {}'.format(params['res'], params['top_k']),'green'))

            result_dict = evaluate_keypoint_net_sonar(
                data_loader,
                keypoint_net,
                noise_util=noise_util,
                output_shape=params['res'],
                top_k=params['top_k'],
                conf_threshold=conf_threshold,
                use_color=True,
                device=args.device,
                debug= debug)

            results.append({'run_name': run_name,
                            'result': result_dict})

            _print_result(result_dict)

        evaluation_results[model_name] = {'model_config': config,
                                          'evaluation': results}

    evaluation_results['eval_params'] = eval_params

    dt = datetime.now().strftime("_%d_%m_%Y__%H_%M_%S")
    pth = os.path.join('../data/eval', dt + "_eval_result.json")

    with open(pth, "w") as f:
        json.dump(evaluation_results, f, indent=4, separators=(", ", ": "))
        print("Saved evaluation results to:",pth)

if __name__ == '__main__':
    main()

