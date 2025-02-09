# Observable-AE.py
# 2025 Kai Fukami (Tohoku University, kfukami1@tohoku.ac.jp)

## Authors:
# Koji Fukagata and Kai Fukami
## We provide no guarantees for this code.  Use as-is and for academic research use only; no commercial use allowed without permission. For citation, please use the reference below:
#     Ref: K. Fukagata and K. Fukami,
#     “Compressing fluid flows with nonlinear machine learning: mode decomposition, latent modeling, and flow control,”
#     in Review
#
# The code is written for educational clarity and not for speed.
# -- version 1: Feb 9, 2025

#import os
#os.environ["CUDA_VISIBLE_DEVICES"] = "1"

from keras.layers import Input, Add, Dense, Conv2D, Conv2DTranspose, MaxPooling2D, AveragePooling2D, UpSampling2D, Flatten, Reshape, LSTM, Concatenate, Conv2DTranspose
from keras.models import Model
from keras import backend as K
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
import tensorflow as tf
from tqdm import tqdm as tqdm
from scipy.io import loadmat


import pickle
import os, sys
import urllib.request


#########################################
# 1. Download files used in this code
#########################################
# [NOTICE] In this code, we use 2000 snapshots (1 pickle file) with float16 precision to make the file size small altough we use 10000 snapshots (5} pickle files) with float64 precision in the original paper.
# You need about 600MB free space in total for the downloading files.
# The pickle file is loaded in "3. Load flow field."

def dl_progress(count, block_size, total_size):
    sys.stdout.write('\r %d%% of %d MB' %(100*count*block_size/total_size, total_size/1024/1024))

savename = "flow_field_data0.pickle"
if(not os.path.exists(savename)):
    url = "https://dl.dropboxusercontent.com/s/3pnuoxrx9xvqxi2/flow_field_data0.pickle"
    print('Downloading:',savename)
    urllib.request.urlretrieve(url, savename, dl_progress)
    print('')

savename = "mode0.csv"
if(not os.path.exists(savename)):
    url = "https://dl.dropboxusercontent.com/s/x3bw3h1zfwty84x/mode0.csv"
    print('Downloading:',savename)
    urllib.request.urlretrieve(url, savename, dl_progress)
    print('')

#########################################
# 2. Load flow field
#########################################
# Flow fields are stored in "pickle" files
X=[]
for i in tqdm(range(1)):
    fnstr="./flow_field_data" + '{0:01d}'.format(i)+".pickle"
    # Pickle load
    with open(fnstr, 'rb') as f:
        obj = pickle.load(f)
    if i==0:
        X=obj
    else:
        X=np.concatenate([X,obj],axis=0)
print(X.shape)
# The size of X is (# of snapshots, 384(Nx), 192(Ny), 2(u&v))

# Load average field
mode0=pd.read_csv("./mode0.csv", header=None, delim_whitespace=None)
mode0=mode0.values

x_num0=384; y_num0=192;
Uf0=mode0[0:x_num0*y_num0]
Vf0=mode0[x_num0*y_num0:x_num0*y_num0*2]
Uf0=np.reshape(Uf0,[x_num0,y_num0])
Vf0=np.reshape(Vf0,[x_num0,y_num0])

# We consider fluctuation component of flow field
for i in range(len(X)):
    X[i,:,:,0]=X[i,:,:,0]-Uf0
    X[i,:,:,1]=X[i,:,:,1]-Vf0



#import tensorflow._api.v2.compat.v1 as tf

#tf.disable_v2_behavior()


#########################################
# 3. CNN-AE construction
#########################################

act = 'tanh'
input_img = Input(shape=(384,192,2))

x1 = Conv2D(16, (3,3),activation=act, padding='same')(input_img)
x1 = MaxPooling2D((2,2),padding='same')(x1)
x1 = Conv2D(8, (3,3),activation=act, padding='same')(x1)
x1 = MaxPooling2D((2,2),padding='same')(x1)
x1 = Conv2D(8, (3,3),activation=act, padding='same')(x1)
x1 = MaxPooling2D((2,2),padding='same')(x1)
x1 = Conv2D(8, (3,3),activation=act, padding='same')(x1)
x1 = MaxPooling2D((2,2),padding='same')(x1)
x1 = Conv2D(4, (3,3),activation=act, padding='same')(x1)
x1 = MaxPooling2D((2,2),padding='same')(x1)
x1 = Conv2D(4, (3,3),activation=act, padding='same')(x1)
x1 = MaxPooling2D((2,2),padding='same')(x1)
x1 = Reshape([6*3*4])(x1)

x_lat = Dense(2,activation=act)(x1)

x1 = Dense(72,activation=act)(x1)
x1 = Reshape([6,3,4])(x1)
x1 = UpSampling2D((2,2))(x1)
x1 = Conv2D(4, (3,3),activation=act, padding='same')(x1)
x1 = UpSampling2D((2,2))(x1)
x1 = Conv2D(8, (3,3),activation=act, padding='same')(x1)
x1 = UpSampling2D((2,2))(x1)
x1 = Conv2D(8, (3,3),activation=act, padding='same')(x1)
x1 = UpSampling2D((2,2))(x1)
x1 = Conv2D(8, (3,3),activation=act, padding='same')(x1)
x1 = UpSampling2D((2,2))(x1)
x1 = Conv2D(16, (3,3),activation=act, padding='same')(x1)
x1 = UpSampling2D((2,2))(x1)
x_final = Conv2D(2, (3,3),padding='same')(x1)
autoencoder = Model(input_img, [x_final])


autoencoder.compile(optimizer='adam', loss='mse')



#########################################
# 4. Model training
#########################################



from keras.callbacks import ModelCheckpoint,EarlyStopping
X_train, X_test  = train_test_split(X, test_size=0.2, random_state=None)
model_cb=ModelCheckpoint('./Model.hdf5', monitor='val_loss',save_best_only=True,verbose=1)
early_cb=EarlyStopping(monitor='val_loss', patience=200,verbose=1)
cb = [model_cb, early_cb]
history = autoencoder.fit(X_train,[X_train],epochs=50000,batch_size=128,verbose=1,callbacks=cb,shuffle=True,validation_data=(X_test, [X_test]))
import pandas as pd
df_results = pd.DataFrame(history.history)
df_results['epoch'] = history.epoch
df_results.to_csv(path_or_buf='./History.csv',index=False)


