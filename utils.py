import os
import matplotlib.pylab as plt
import numpy as np
import torch.nn as nn
import torch
import matplotlib.cm as cm
from tqdm import tqdm
from skimage.measure import label
from scipy.spatial.distance import directed_hausdorff


def show_data(data_sample):
    """
    Plot the original image and the mask of the image
    :param data_sample: one sample data in a KDR dataset
    """
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    image = data_sample[1].numpy().transpose((1, 2, 0))
    mask = data_sample[2][0].numpy()

    axes[0].imshow(image)
    axes[0].set_title('Image')
    axes[1].imshow(mask)
    axes[1].set_title('Segmentation Mask')
    for ax in axes:
        ax.axis('off')
    plt.show()


def dice_coefficient(y_true, y_pred):
    """
    Calculates the dice coefficient of a batch of generated masks and a batch of
    ground truth masks
    :param y_true: a batch of ground truth mask, a Tensor of shape (batch size,
    height, width)
    :param y_pred: a batch of generated mask, a Tensor of shape (batch size,
    height, width)
    :return: the mean dice coefficient of the batch
    """
    smooth = 1e-6
    y_true = y_true.view(y_true.size(0), -1)
    y_pred = y_pred.view(y_pred.size(0), -1)
    intersection = (y_true * y_pred).sum(dim=1)
    dice = (2. * intersection + smooth) / (y_true.sum(dim=1) + y_pred.sum(dim=1) + smooth)
    return dice.mean()


def dice_loss(y_true, y_pred):
    """
    Dice_loss, negative dice coefficient
    :param y_true: a batch of ground truth mask, a Tensor of shape (batch size,
    height, width)
    :param y_pred: a batch of generated mask, a Tensor of shape (batch size,
    height, width)
    :return: the mean dice loss of the batch
    """
    return -dice_coefficient(y_true, y_pred)


def iou(y_true, y_pred):
    """
    Calculates the iou of a batch of generated masks and a batch of ground truth
    masks
    :param y_true: a batch of ground truth mask, a Tensor of shape (batch size,
    height, width)
    :param y_pred: a batch of generated mask, a Tensor of shape (batch size,
    height, width)
    :return: the mean iou of the batch
    """
    smooth = 1e-6
    y_true = y_true.view(y_true.size(0), -1)
    y_pred = y_pred.view(y_pred.size(0), -1)
    intersection = (y_true * y_pred).sum(dim=1)
    iouu = (1. * intersection + smooth) / (y_true.sum(dim=1) + y_pred.sum(dim=1) - intersection + smooth)
    return iouu.mean()


def iou_loss(y_true, y_pred):
    """
    Iou loss, negative dice coefficient
    :param y_true: a batch of ground truth mask, a Tensor of shape (batch size,
    height, width)
    :param y_pred: a batch of generated mask, a Tensor of shape (batch size,
    height, width)
    :return: the mean iou loss of the batch
    """
    return -iou(y_true, y_pred)


class CELDice:
    def __init__(self, dice_weight=0, num_classes=1):
        self.nll_loss = nn.CrossEntropyLoss()
        self.jaccard_weight = dice_weight
        self.num_classes = num_classes

    def __call__(self, outputs, targets):
        loss = (1 - self.jaccard_weight) * self.nll_loss(outputs, targets)
        if self.jaccard_weight:
            eps = 1e-15
            for cls in range(self.num_classes):
                jaccard_target = (targets == cls).float()
                jaccard_output = outputs[:, cls].exp()
                intersection = (jaccard_output * jaccard_target).sum()
                union = jaccard_output.sum() + jaccard_target.sum()
                loss -= torch.log((2*intersection + eps) / (union + eps)) * self.jaccard_weight
        return loss


def plot_progression(cost_list, val_iou_list, train_iou_list, path):
    """
    Plot the three statistics in one duo-axis graph, save the graph
    :param path: the path to store the plot
    :param cost_list: a list costs
    :param val_iou_list: a list of dic coefficients (same length as above)
    :param train_iou_list: a list of IoUs (intersection over union, same length as
    above)
    """
    n = len(cost_list)
    assert(len(cost_list) == len(val_iou_list) and len(val_iou_list) == len(train_iou_list))
    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()
    iterations = [_ for _ in range(n)]
    ax1.plot(iterations, val_iou_list, 'o', color=(139 / 255, 0, 0), label="Validation IoU", alpha=0.5)
    ax1.plot(iterations, train_iou_list, 'x', color=(139 / 255, 0, 0), label="Training IoU")
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Validation accuracy', color=(139/255, 0, 0))
    ax1.legend(title="metric", loc="center right", bbox_to_anchor=(1, 0.5))
    ax1.tick_params('y', colors=(139/255, 0, 0))
    ax2.plot(iterations, cost_list, '-', color=(0, 0, 139/255))
    ax2.set_ylabel('Training loss', color=(0, 0, 139/255))
    ax2.tick_params('y', colors=(0, 0, 139/255))
    plt.title('Training loss and validation accuracy progression')
    plt.savefig('/home/mason2/AGVon1080Ti/{}.png'.format(path))
    plt.close()


def generate_mask(model, sample_point, model_name):
    """
    show the ultrasound image of the sample point along with the ground truth
    segmentation and the generated mask by the models of the sample
    :param model_name: the models name, determines which folder to save the
    figure to
    :param model: a UNet model
    :param sample_point: tuple, an item from the KDR dataset
    :return:
    """
    path = "Logging{}".format(model_name)
    if not os.path.isdir(path):
        os.mkdir(path)
    fig, axes = plt.subplots(1, 3, figsize=(12, 6))
    p = model(sample_point[1].unsqueeze(0))
    prediction = (p > 0.5).float()[0].numpy().transpose((1, 2, 0))
    image = sample_point[1].numpy().transpose((1, 2, 0))
    mask = sample_point[2][0].numpy()

    axes[0].imshow(image)
    axes[0].set_title('Image')
    axes[1].imshow(mask)
    axes[1].set_title('Ground Truth')
    axes[2].imshow(prediction)
    axes[2].set_title('Prediction')

    for ax in axes:
        ax.axis('off')
    fig.suptitle(sample_point[0])
    plt.savefig(os.path.join(path, sample_point[0]))
    plt.close()


def compare_three_models(model1, model2, model3, sample_point):
    """
    show the ultrasound image of the sample point along with the ground truth
    segmentation and the generated masks by the models of the sample, side by
    side comparison of one particular data point
    :param model1: UNet model 1
    :param model2: UNet model 2
    :param model3: UNet model 3
    :param path: the path to the folder to which we save the comparison
    :param sample_point: tuple, an item from the KDR dataset
    :return:
    """
    fig, axes = plt.subplots(1, 5, figsize=(12, 6))
    p1 = model1(sample_point[1].unsqueeze(0))
    prediction1 = (p1 > 0.5).float()[0].numpy().transpose((1, 2, 0))
    p2 = model2(sample_point[1].unsqueeze(0))
    prediction2 = (p2 > 0.5).float()[0].numpy().transpose((1, 2, 0))
    p3 = model3(sample_point[1].unsqueeze(0))
    prediction3 = (p3 > 0.5).float()[0].numpy().transpose((1, 2, 0))
    image = sample_point[1].numpy().transpose((1, 2, 0))
    mask = sample_point[2][0].numpy()

    axes[0].imshow(image)
    axes[0].set_title('Image')
    axes[1].imshow(mask)
    axes[1].set_title('Ground Truth')
    axes[2].imshow(prediction1)
    axes[2].set_title(model1.__class__.__name__)
    axes[3].imshow(prediction2)
    axes[3].set_title(model2.__class__.__name__)
    axes[4].imshow(prediction3)
    axes[4].set_title(model3.__class__.__name__)

    for ax in axes:
        ax.axis('off')
    fig.suptitle(sample_point[0])
    plt.savefig("newComparison")
    plt.close()


def write_description(model, path):
    """
    write the models description into a txt file and save it
    :param path: the name to of the txt file
    :param model: the models of interest
    :return: none
    """
    with open(path, "w") as file:
        file.write(str(model))


def visualize_attention(model, sample_point, model_name):
    """
    Given a model and a data point, plot the attention maps of the specific
    input at all spatial levels
    :param model: the model
    :param sample_point: a data point from the KRD dataset, where the first
    index is the image
    :return: None
    """
    path = "Logging{}".format(model_name)
    fig, axes = plt.subplots(1, 5, figsize=(12, 6))
    model(sample_point[1].unsqueeze(0))
    image = sample_point[1].numpy().transpose((1, 2, 0))
    turbo = cm.get_cmap('turbo')

    axes[0].imshow(image)
    axes[1].imshow(turbo(model.ag1.map[0][0].detach().numpy()))
    axes[2].imshow(turbo(model.ag2.map[0][0].detach().numpy()))
    axes[3].imshow(turbo(model.ag3.map[0][0].detach().numpy()))
    axes[4].imshow(turbo(model.ag4.map[0][0].detach().numpy()))

    for ax in axes:
        ax.axis('off')
    filename = "AttentionMap"
    plt.savefig(f"{path}/{filename}{sample_point[0]}")
    plt.close()


def evaluate_model(model, data_loader, metric=iou, report=False):
    """
    the evaluate function in the models evaluation phase, returns the statistic
    of the whole dataset evaluated by the metric of interest.
    :param report: whether we print results out
    :param model: the model to evaluate
    :param data_loader: the data loader in the training process
    :param metric: iou, dice_coefficient, percentage_one_piece, or
    fragmentation, (default iou,) needs to be a binary operator and able to do
    calculation of a batch
    :return: the metric of the whole dataset.
    """
    total = 0
    total_num = 0
    for __, images, targets in tqdm(data_loader, desc="Eval", leave=False):
        p = model(images)
        predictions = (p > 0.5).float()
        batch = metric(predictions.detach(), targets.detach())
        total += batch * images.shape[0]
        total_num += images.shape[0]
    result = total / total_num
    if report:
        print("{}: {}".format(metric.__name__, result))
    return result


def disable_running(model):
    """
    The bug that was found in model.eval() phase. Disables track_running_mean,
    clears running_mean and running_var to activate proper model evaluation
    :param model: the model of interest
    :return: None
    """
    for m in model.modules():
        if isinstance(m, nn.BatchNorm2d):
            m.track_running_stats = False
            m.running_mean = None
            m.running_var = None


def one_piece(mask):
    """
    Test if a given binary mask is one-piece or not using 4-connectivity
    :param mask: the binary mask with 0 as background and 1 as foreground, a
    numpy array
    :return: True iff the mask is one-piece
    """
    labeled_mask = label(mask, connectivity=1)
    unique_labels = set(labeled_mask.flatten())
    num_labels = len(unique_labels) - (1 if 0 in unique_labels else 0)
    return num_labels == 1


def percentage_one_piece(y_pred, y_true):
    """
    Calculates the percentage of one-piece masks in a batch of generated masks
    :param y_true: un-used
    :param y_pred: a batch of generated mask, a Tensor of shape (batch size,
    height, width)
    :return: the percentage of one-piece masks of the batch
    """
    y_pred = y_pred.numpy()
    one_piece_count = sum(one_piece(mask) for mask in y_pred)
    percentage = (one_piece_count / len(y_pred)) * 100
    return percentage


def hausdorff_distance(y_pred, y_true):
    """
    Returns the symmetrical hausdorff distance between two masks, a measure of
    similarity
    :param y_true: a ground truth mask, a Tensor of shape (height, width)
    :param y_pred: a generated mask, a Tensor of shape (height, width)
    :return: the hausdorff distance loss of the two masks
    """
    return max(directed_hausdorff(y_pred, y_true)[0], directed_hausdorff(y_true, y_pred)[0])


def batch_hausdorff(y_pred, y_true):
    """
    Returns the mean symmetrical hausdorff distance between two masks, a measure
    of similarity
    :param y_true: a batch of ground truth mask, a Tensor of shape (batch size,
    height, width)
    :param y_pred: a batch of generated mask, a Tensor of shape (batch size,
    height, width)
    :return: the mean hausdorff distance loss of the batch
    """
    y_pred, y_true = y_pred.numpy(), y_true.numpy()
    hau = sum(hausdorff_distance(mask[0], truth[0]) for mask, truth in zip(y_pred, y_true))
    mean = hau / len(y_pred)
    return mean


def instantiate_unet(config):
    """
    Instantiate and return an instance of a UNet regardless of its type
    :param config: model config dict
    :return: created UNet
    """
    return config["type"](config)
