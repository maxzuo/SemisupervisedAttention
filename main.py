import torch.optim as optim
from train import train
from metrics.UnsupervisedMetrics import visualizeLossPerformance
from visualizer.visualizer import visualizeImageBatch, show_cam_on_image
from model.resnet import resnet50
from data_loader.new_pascal_runner import loadPascalData
from data_loader.cifar_data_loader import loadCifarData
import os
import numpy as np
from torch import nn
import torchvision.models as models
import torchvision.transforms as transforms
import torchvision
import torch
import cv2
import sys
sys.path.append("./")

from pdb import set_trace as bp

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


# from data_loader.pascal_runner import loadPascalData
# from model.loss import calculateLoss

if __name__ == '__main__':
    learning_rate = float(sys.argv[7])  # 0.00001
    numEpochs = int(sys.argv[8])  # 400
    batch_size = int(sys.argv[9])  # 4
    resolutionMatch = int(sys.argv[10])  # 2
    similarityMetric = int(sys.argv[11])  # 2
    alpha = int(sys.argv[12])  # 2

    print('Training Mode: ', sys.argv[5])
    print('Learning Rate: ', learning_rate)
    print('Number of Epochs: ', numEpochs)
    print('Batch Size: ', batch_size)
    print('Resolution Match Mode: ', resolutionMatch)
    print('Similarity Metric Mode: ', similarityMetric)
    print('Alpha: ', alpha)



    if os.path.isdir('/scratch/'):
        batchDirectory = '/scratch/groups/rubin/krish05m/AttentionMap/saved_batches/' + \
            sys.argv[6] + '/'
    else:
        batchDirectory = ''
    # Load the CIFAR Dataset
    # suptrainloader,unsuptrainloader, testloader = loadPascalData(batch_size=batch_size)
    # suptrainloader, unsuptrainloader, testloader = loadPascalData(
    #     batch_size=batch_size)
    suptrainloader, unsuptrainloader, validloader, testloader = loadCifarData(batch_size=batch_size)
    
    print(len(suptrainloader.dataset))
    print(len(unsuptrainloader.dataset))
    print(len(validloader.dataset))
    print(len(testloader.dataset))

    CHECK_FOLDER = os.path.isdir(batchDirectory + "saved_figs")
    if not CHECK_FOLDER:
        os.makedirs(batchDirectory + "saved_figs")
        print("Made Saved_Figs folder")

    CHECK_FOLDER = os.path.isdir(batchDirectory + "saved_checkpoints")
    if not CHECK_FOLDER:
        os.makedirs(batchDirectory + "saved_checkpoints")
        print("Made Saved_Checkpoints folder")

    model = models.resnet50(pretrained=False)
    # model = resnet50(pretrained=True)

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    model.fc = nn.Linear(int(model.fc.in_features), 10)

    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    # lr = [1e-5, 5e-3]
    # optimizer = optim.SGD([
    #     {'params': list(model.parameters())[:-1], 'lr': lr[0], 'momentum': 0.9},
    #     {'params': list(model.parameters())[-1], 'lr': lr[1], 'momentum': 0.9}
    #     ])
    # scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, 12, eta_min=0, last_epoch=-1)

    # optimizer = torch.optim.SGD(model.parameters(),
    #                            lr=learning_rate, momentum=0.9, weight_decay=0.0001)
    scheduler = None

    # all_checkpoints = os.listdir('saved_checkpoints')
    epoch = 0

    print(model.fc.weight)
    # model.conv1.padding_mode = 'reflect'
    # for x in model.layer1:
    #     x.conv2.padding_mode = 'reflect'
    # for x in model.layer2:
    #     x.conv2.padding_mode = 'reflect'
    # for x in model.layer3:
    #     x.conv2.padding_mode = 'reflect'
    # for x in model.layer4:
    #     x.conv2.padding_mode = 'reflect'

    def loadCheckpoint(path, model):
        checkpoint = torch.load(path, map_location=device)
        try:
            model.load_state_dict(checkpoint)
        except:
            model.load_state_dict(checkpoint['model_state_dict'])
        # optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        try:
            epoch = checkpoint['epoch']
        except:
            epoch = 0

    if sys.argv[1] == 'loadCheckpoint':
        PATH = "/scratch/groups/rubin/cifar_best.pt"
        print('Loading Saved Model', PATH)
        loadCheckpoint(PATH, model)

    print(model.fc.weight)

    target_layer = model.layer4[-1]  # this is the layer before the pooling

    use_cuda = torch.cuda.is_available()
    # load a few images from CIFAR and save
    if sys.argv[2] == 'visualLoss':
        from model.loss import CAMLoss
        CAMLossInstance = CAMLoss(model, target_layer, use_cuda, resolutionMatch, similarityMetric)
        dataiter = iter(testloader)

        device = torch.device("cuda:0" if use_cuda else "cpu")
        model.eval()

        # def findWord(arr, idx2label):
        #     for item in arr:
        #         ones = np.argwhere(item.numpy())
        #         ones = [i[0] for i in ones]
        #         print(idx2label[ones[0]])

        # f = open("imagenet_class_index.json",)
        # class_idx = json.load(f)
        # idx2label = [class_idx[str(k)][1] for k in range(len(class_idx))]

        # def showImg(arr):
        #     fig, axs = plt.subplots(1,4)
        #     counter = 0
        #     for item in arr:
        #         bb = np.moveaxis(arr[counter].numpy(),0,-1)
        #         bb -= np.min(bb)
        #         bb = bb/ np.max(bb)
        #         axs[counter].imshow(bb)
        #         counter += 1
        #     plt.show()

        idx2label = ['plane', 'car', 'bird', 'cat','deer', 'dog', 'frog', 'horse', 'ship', 'truck']

        for i in range(3):
            images, labels = dataiter.next()
            images = images.to(device)
            labels = labels.to(device)
            # images.to("cpu")
            # model.to(device)
            with torch.no_grad():
                # calculate outputs by running images through the network
                outputs = model(images)
                # the class with the highest energy is what we choose as prediction
                _, predicted = torch.max(outputs.data, 1)
                predicted = predicted.tolist()
                # print(predicted)
                predictedNames = [idx2label[p] for p in predicted]
                labels = labels.cpu().numpy()
                actualLabels = [labels[p, predicted[p]]
                                for p in range(len(predicted))]
                # print(predictedNames)
                print(actualLabels)
                # print(predictedNames)
            imgTitle = "epoch_" + str(epoch) + "_batchNum_" + str(i)

            visualizeLossPerformance(
                CAMLossInstance, images, labels=actualLabels, imgTitle=imgTitle, imgLabels=predictedNames)

    # visualizeImageBatch(images, labels)

    target_category = None

    # need to set params?

    # model.fc = nn.Linear(int(model.fc.in_features), 10)

    whichTraining = sys.argv[5]
    if whichTraining not in ['supervised', 'unsupervised', 'alternating']:
        print('invalid Training. will alternate')
        whichTraining = 'alternating'
    if sys.argv[3] == 'train':
        trackLoss = sys.argv[4] == 'trackLoss'
        print(trackLoss)
        train(model, numEpochs, suptrainloader, unsuptrainloader, validloader, optimizer, target_layer, target_category, use_cuda, resolutionMatch,
              similarityMetric, alpha, trackLoss=trackLoss, training=whichTraining, batchDirectory=batchDirectory, scheduler=scheduler, batch_size=batch_size)
