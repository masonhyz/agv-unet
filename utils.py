import os
import matplotlib.pylab as plt


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
    return -iou(y_true, y_pred)


def plot_progression(cost_list, val_iou, train_iou, path):
    """
    Plot the three statistics in one duo-axis graph, save the graph
    :param path: the path to store the plot
    :param cost_list: a list costs
    :param val_iou: a list of dic coefficients (same length as above)
    :param train_iou: a list of IoUs (intersection over union, same length as
    above)
    """
    n = len(cost_list)
    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()
    iterations = [_ for _ in range(n)]
    ax1.plot(iterations, val_iou, 'o', color=(139 / 255, 0, 0), label="Validation IoU", alpha=0.5)
    ax1.plot(iterations, train_iou, 'x', color=(139 / 255, 0, 0), label="Training IoU")
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Validation accuracy', color=(139/255, 0, 0))
    ax1.legend(title="metric", loc="center right", bbox_to_anchor=(1, 0.5))
    ax1.tick_params('y', colors=(139/255, 0, 0))
    ax2.plot(iterations, cost_list, '-', color=(0, 0, 139/255))
    ax2.set_ylabel('Training loss', color=(0, 0, 139/255))
    ax2.tick_params('y', colors=(0, 0, 139/255))
    plt.title('Training loss and validation accuracy progression')
    plt.savefig('/home/mason2/AGVon1080Ti/Prog{}.png'.format(path))
    plt.close()


def predict(model, sample_point, path):
    """
    show the ultrasound image of the sample point along with the ground truth
    segmentation and the generated mask by the models of the sample
    :param path: the path to the folder to which we save the predictions
    :param model: a UNet models
    :param sample_point: tuple, an item from the KDR dataset
    :return:
    """
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


def write_description(model, path):
    """
    write the models description into a txt file and save it
    :param path: the name to of the txt file
    :param model: the models of interest
    :return: none
    """
    with open("Desc{}.txt".format(path), "w") as file:
        file.write(str(model))
