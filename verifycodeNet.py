import os

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms


class LeNet(nn.Module):
    def __init__(self):
        super(LeNet, self).__init__()
        self.conv1 = nn.Sequential(nn.Conv2d(1, 6, 3, 1, 2), nn.ReLU(),
                                   nn.MaxPool2d(2, 2))

        self.conv2 = nn.Sequential(nn.Conv2d(6, 16, 5), nn.ReLU(),
                                   nn.MaxPool2d(2, 2))

        self.fc1 = nn.Sequential(nn.Linear(16 * 5 * 5, 120),
                                 nn.BatchNorm1d(120), nn.ReLU())

        self.fc2 = nn.Sequential(
            nn.Linear(120, 84),
            nn.BatchNorm1d(84),
            nn.ReLU(),
            nn.Linear(84, 10))

    def forward(self, x):
        x = self.conv1(x)
        x = self.conv2(x)
        x = x.view(x.size()[0], -1)
        x = self.fc1(x)
        x = self.fc2(x)
        return x


def verify(gifPath):
    """
    :param gifPath:从网页下载的图片路径
    :return: 返回识别的验证码
    """
    result = ""
    verificationcode_model = LeNet()
    verificationcode_model.load_state_dict(torch.load('verify_checkpoint.pth', map_location='cpu'))
    img = Image.open(gifPath)
    imgNp = np.array(img)
    for index in range(4):
        img = imgNp[6:-6, 1:-1][:, 25 * (index % 4):25 * (index % 4 + 1)]
        img = transforms.ToPILImage()(img)
        img = transforms.Resize((28, 28))(img)
        img = transforms.ToTensor()(img)
        img = 1 - img
        img = img.unsqueeze(0)
        verificationcode_model.eval()
        res = torch.argmax(verificationcode_model(img)).item()
        result += str(res)
    if os.path.exists(gifPath):
        os.remove(gifPath)
    return result
