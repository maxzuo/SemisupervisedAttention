import torch.optim as optim
from train import train
from evaluate import evaluate
from metrics.UnsupervisedMetrics import visualizeLossPerformance
from visualizer.visualizer import visualizeImageBatch, show_cam_on_image
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
import json
import distutils.util
sys.path.append("./")


os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"



if __name__ == '__main__':
    toLoadCheckpoint = bool(distutils.util.strtobool(sys.argv[1]))
    toTrain = bool(distutils.util.strtobool(sys.argv[3]))
    toEvaluate = bool(distutils.util.strtobool(sys.argv[4])) #True
    whichTraining = sys.argv[5] #alternating
    learning_rate = float(sys.argv[7])  # 0.00001
    numEpochs = int(sys.argv[8])  # 400
    batch_size = int(sys.argv[9])  # 4
    resolutionMatch = int(sys.argv[10])  # 2
    similarityMetric = int(sys.argv[11])  # 2
    alpha = int(sys.argv[12])  # 2
    unsup_batch_size = int(sys.argv[13]) #12
    fullyBalanced = bool(distutils.util.strtobool(sys.argv[14])) #True
    useNewUnsupervised=bool(distutils.util.strtobool(sys.argv[15])) #True
    numOutputClasses = int(sys.argv[17]) #20
    reflectPadding = bool(distutils.util.strtobool(sys.argv[18])) #True
    
    try:
        unsupDatasetSize=int(sys.argv[16]) #None
    except:
        unsupDatasetSize=None
    try:
        numFiguresToCreate=int(sys.argv[2]) #None
    except:
        numFiguresToCreate=None
    try:
        perBatchEval=int(sys.argv[19]) #None to do per epoch eval
    except:
        perBatchEval=None
    try:
        saveRecurringCheckpoint=int(sys.argv[20])
    except:
        saveRecurringCheckpoint=None

    print('############## Run Settings: ###############')
    print('Loading Checkpoint: ', toLoadCheckpoint)
    print('Training: ', toTrain)
    print('Evaluating: ', toEvaluate)
    print('Training Mode: ', whichTraining)
    print('Learning Rate: ', learning_rate)
    print('Number of Epochs: ', numEpochs)
    print('Batch Size: ', batch_size)
    print('Resolution Match Mode: ', resolutionMatch)
    print('Similarity Metric Mode: ', similarityMetric)
    print('Alpha: ', alpha)
    print('Unsupervised Batch Size: ', unsup_batch_size)
    print('Fully Balanced Supervised Dataset: ', fullyBalanced)
    print('Using New Unsupervised Data', useNewUnsupervised)
    print('Number of output classes: ', numOutputClasses)
    print('Using Reflecting Padding: ', reflectPadding)
    print('UnsupervisedDatasetSize (Everything if None): ', unsupDatasetSize)
    print('Number of Figures to create: ', numFiguresToCreate)
    print('Evaluating Per How Many Batches (Per Epoch if None): ', perBatchEval)
    print('Saving Recurring Checkpoints (Only best checkpoints if None): ', saveRecurringCheckpoint)



    #json contains the paths required to launch on sherlock
    with open('./sherlock_launch.json') as f:
        sherlock_json = json.load(f)
        print(sherlock_json)

    print('########################################### \n\n')


    #checks if on sherlock, otherwise creates folder in the batchDirectory in home repo (usually when running on cpu)
    if os.path.isdir('/scratch/'):
        batchDirectory = sherlock_json['batch_directory_path'] + \
            sys.argv[6] + '/'
    else:
        batchDirectory = ''


    suptrainloader, unsuptrainloader, validloader, testloader = loadPascalData(
        batch_size=batch_size, unsup_batch_size=unsup_batch_size, fullyBalanced=fullyBalanced, 
        useNewUnsupervised=useNewUnsupervised, unsupDatasetSize=unsupDatasetSize)



    CHECK_FOLDER = os.path.isdir(batchDirectory + "saved_figs")
    if not CHECK_FOLDER:
        os.makedirs(batchDirectory + "saved_figs")
        print("Made Saved_Figs folder")

    CHECK_FOLDER = os.path.isdir(batchDirectory + "saved_checkpoints")
    if not CHECK_FOLDER:
        os.makedirs(batchDirectory + "saved_checkpoints")
        print("Made Saved_Checkpoints folder")

    model = models.resnet50(pretrained=True)

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    model.fc = nn.Linear(int(model.fc.in_features), numOutputClasses)

    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)


    # scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, 12, eta_min=0, last_epoch=-1)


    scheduler = None

    all_checkpoints = os.listdir('saved_checkpoints')
    epoch = 0


    def loadCheckpoint(path, model):
        checkpoint = torch.load(path, map_location=device)
        model.load_state_dict(checkpoint['model_state_dict'])
        # optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        try:
            epoch = checkpoint['epoch']
        except:
            epoch = 0
        
    if toLoadCheckpoint:
        if len(all_checkpoints) > 0:
            if os.path.isdir('/scratch/'):
                PATH = sherlock_json['load_checkpoint_path']
                ##wont load path2 unless numFiguresToCreate is not None
                PATH2 = sherlock_json['load_figure_comparison_checkpoint_path']
            else:
                PATH = 'saved_checkpoints/hot_bench_150s_model_best.pt'
                PATH2 = 'saved_checkpoints/hot_bench_150s_model_best.pt'

        print(model.fc.weight)
        loadCheckpoint(PATH, model)
        ## Sanity check to make sure the loaded weights are different after loading chekcpoint
        print(model.fc.weight)


    ## WHICH LAYER FOR GRADCAM
    target_layer = model.layer4[-1]  # this is the layer before the pooling

    
    if reflectPadding:
        model.conv1.padding_mode = 'reflect'
        for x in model.layer1:
            x.conv2.padding_mode = 'reflect'
        for x in model.layer2:
            x.conv2.padding_mode = 'reflect'
        for x in model.layer3:
            x.conv2.padding_mode = 'reflect'
        for x in model.layer4:
            x.conv2.padding_mode = 'reflect'



    use_cuda = torch.cuda.is_available()
    # load a few images from CIFAR and save
    if numFiguresToCreate is not None:
        from model.loss import CAMLoss        
        CAMLossInstance = CAMLoss(
            model, target_layer, use_cuda, resolutionMatch, similarityMetric)
        dataiter = iter(validloader)
        device = torch.device("cuda:0" if use_cuda else "cpu")
        model.eval()
        idx2label = ['aeroplane', 'bicycle', 'bird', 'boat', 'bottle', 'bus',
                     'car', 'cat', 'chair', 'cow', 'diningtable', 'dog', 'horse',
                     'motorbike', 'person', 'pottedplant', 'sheep', 'sofa', 'train', 'tvmonitor']

        for i in range(numFiguresToCreate):
            images, labels = dataiter.next()
            images = images.to(device)
            labels = labels.to(device)
            # images.to("cpu")
            # model.to(device)
            with torch.no_grad():
                # calculate outputs by running images through the network
                loadCheckpoint(PATH, model)
                outputs = model(images)
                loadCheckpoint(PATH2, model)
                outputs2 = model(images)
                # the class with the highest energy is what we choose as prediction
                val, predicted = torch.max(outputs.data, 1)
                mean = torch.mean(outputs.data, 1)
                val2, predicted2 = torch.max(outputs2.data, 1)
                mean2 = torch.mean(outputs2.data, 1)
                
                predicted = predicted.tolist()
                predicted2 = predicted2.tolist()
                print(predicted, predicted2)
                # if predicted != predicted2:

                predictedNames = [idx2label[p] for p in predicted]
                labels = labels.numpy()
                actualLabels = [labels[p, predicted[p]]
                                for p in range(len(predicted))]
                predictedNames2 = [idx2label[p] for p in predicted2]
                actualLabels2 = [labels[p, predicted2[p]]
                                for p in range(len(predicted2))]
                # print("DIFFERING!", actualLabels, actualLabels2)
                print("\n\n Val: ", val, val2, "\n\n")
                print("\n\n Mean: ", mean, mean2, "\n\n")
                    
            ### To only create figures with differing predictions, wrap the following lines with if predicted != predicted2:
            loadCheckpoint(PATH, model)
            imgTitle = "which_0_epoch_" + str(epoch) + "_batchNum_" + str(i)
            visualizeLossPerformance(
                CAMLossInstance, images, labels=actualLabels, imgTitle=imgTitle, imgLabels=predictedNames)
            loadCheckpoint(PATH2, model)
            imgTitle = "which_1_epoch_" + str(epoch) + "_batchNum_" + str(i)
            visualizeLossPerformance(
                CAMLossInstance, images, labels=actualLabels2, imgTitle=imgTitle, imgLabels=predictedNames2)


    target_category = None

    
    if whichTraining not in ['supervised', 'unsupervised', 'alternating', 'combining']:
        print('invalid Training. Choose between supervised, unsupervised, alternating')
        sys.exit()
    if toTrain:
        print('Beginning Training')
        train(model, numEpochs, suptrainloader, unsuptrainloader, validloader, optimizer, target_layer, target_category, use_cuda, resolutionMatch,
              similarityMetric, alpha, training=whichTraining, batchDirectory=batchDirectory, batch_size=batch_size, 
              unsup_batch_size=unsup_batch_size, perBatchEval=perBatchEval, saveRecurringCheckpoint=saveRecurringCheckpoint)
        print("Training Complete.")

    if toEvaluate:
        print("Evaluating on Test Set...")
        ##load the best checkpoint and evaulate it. 
        checkpoint = torch.load(batchDirectory + "saved_checkpoints/model_best.pt", map_location=device)
        model.load_state_dict(checkpoint['model_state_dict'])
        evaluate(model, testloader, device, batchDirectory=batchDirectory)
        print("Finished Evaluating")