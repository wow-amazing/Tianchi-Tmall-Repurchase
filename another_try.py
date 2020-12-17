#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2020/12/17 13:25
# @Author : gsg
# @Site : 
# @File : another_try.py
# @Software: PyCharm
import gc
import os
import time

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score
from torch import optim, nn
from torch.utils.data import Dataset, DataLoader, random_split
from torch.utils.tensorboard import SummaryWriter

from model import mlp

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

feature_path = './feature/'
model_path = './model/'

writer = SummaryWriter()

lr = 0.01
epochs = 5
batch_size = 64
matrix = pd.read_csv(os.path.join(feature_path, 'data.csv'))

train_data = matrix[matrix['origin'] == 'train'].drop(['origin'], axis=1).drop(['user_id'], axis=1).drop(
    ['merchant_id'], axis=1)
# test_data = matrix[matrix['origin'] == 'test'].drop(['label', 'origin'], axis=1)
# print(np.array(train_data).shape)
# print(np.array(test_data).shape)
train_X, train_y = train_data.drop(['label'], axis=1), train_data['label']
del matrix
gc.collect()


# print(type(train_data))

# targetencoder = LabelEncoder().fit(gatrain.group)
# y = targetencoder.transform(gatrain.group)
# nclasses = len(targetencoder.classes_)
# one_hot = torch.eye(nclasses)[y, :]

class DDataset(Dataset):
    def __init__(self):
        x = np.array(train_X)
        y = np.array(train_y)
        # print(x.shape)
        self.x_data = torch.from_numpy(x)
        self.y_data = torch.from_numpy(y)
        self.len = self.x_data.shape[0]
        # print(self.len)

    def __getitem__(self, item):
        return self.x_data[item], self.y_data[item]

    def __len__(self):
        return self.len


net = mlp(45)  # 修改为不用硬编码的格式
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
net.to(device)

optimizer = optim.Adam(net.parameters(), lr=lr, weight_decay=0.1)

t_v_set = DDataset()
train_set, val_set = random_split(t_v_set, [int(len(t_v_set) * 0.8), len(t_v_set) - int(len(t_v_set) * 0.8)])
train_loader = DataLoader(dataset=train_set, batch_size=batch_size, shuffle=True)
val_loader = DataLoader(dataset=val_set, batch_size=batch_size, shuffle=False)

best_loss = 1000
for epoch in range(epochs):
    start = time.time()

    net.train()
    train_loss, val_losses = 0, 0
    train_acc, val_acc = 0, 0
    n, m = 0, 0

    for feature, label in train_loader:
        n += 1
        feature, label = feature.float().to(device), label.long().to(device)
        net.zero_grad()
        score = net(feature)
        criterion = nn.CrossEntropyLoss()
        loss = criterion(score, label)
        loss.backward()
        optimizer.step()
        train_acc += accuracy_score(label.cpu().data, torch.argmax(score.cpu(), dim=1))
        train_loss += loss

    net.eval()
    label_pred = []
    with torch.no_grad():
        for feature, label in val_loader:
            m += 1
            feature, label = feature.float().to(device), label.long().to(device)
            score = net(feature)
            criterion = nn.CrossEntropyLoss()
            loss = criterion(score, label)
            val_acc += accuracy_score(label.cpu(), torch.argmax(score.cpu().data, dim=1))
            val_losses += loss
            label_pred.append(torch.argmax(score.cpu().data, dim=1))
    end = time.time()
    runtime = end - start
    writer.add_scalars("result", {
        "training_loss": train_loss.data / n,
        "validation_loss": val_losses.data / m,
        "train_acc": train_acc / n,
        "val_acc": val_acc / m
    })
    if (val_losses.data / m) < best_loss:
        print("find new best")
        best_loss = val_losses.data / m
        with open(os.path.join(model_path, 'checkpoint'), "wb") as fout:
            torch.save(net, fout)
    print('epoch: %d, train loss: %.4f, train acc: %.2f, test loss: %.4f, test acc: %.2f, time: %.2f' %
          (epoch, train_loss.data / n, train_acc / n, val_losses.data / m, val_acc / m, runtime))
