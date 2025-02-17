from __future__ import print_function, division

from keras.datasets import mnist
from keras.layers import Input, Dense, Reshape, Flatten, Dropout
from keras.layers import BatchNormalization, Activation, ZeroPadding2D
from keras.layers.advanced_activations import LeakyReLU
from keras.layers.convolutional import UpSampling2D, Conv2D
from keras.models import Sequential, Model
from keras.optimizers import Adam
import keras.backend as K
import matplotlib.pyplot as plt
import sys
import numpy as np

class BGAN():
    """Reference: https://wiseodd.github.io/techblog/2017/03/07/boundary-seeking-gan/"""
    def __init__(self):
        self.img_rows = 28
        self.img_cols = 28
        self.channels = 1
        self.img_shape = (self.img_rows, self.img_cols, self.channels)
        self.latent_dim = 100

        optimizer = Adam(0.0002, 0.5)

        # Build and compile the discriminator
        self.discriminator = self.build_discriminator()
        self.discriminator.compile(loss='binary_crossentropy',optimizer=optimizer,metrics=['accuracy'])

        # Build the generator
        self.generator = self.build_generator()

        # The generator takes noise as input and generated imgs
        z = Input(shape=(self.latent_dim,))
        img = self.generator(z)

        # For the combined model we will only train the generator
        self.discriminator.trainable = False

        # The valid takes generated images as input and determines validity
        valid = self.discriminator(img)

        # The combined model  (stacked generator and discriminator)
        # Trains the generator to fool the discriminator
        self.combined = Model(z, valid)
        self.combined.compile(loss=self.boundary_loss, optimizer=optimizer)

    def build_generator(self):

        Input_g_noise = Input(shape=(self.latent_dim,))
        temp_x = Dense(256)(Input_g_noise)
        temp_x = LeakyReLU(alpha=0.2)(temp_x)
        temp_x = BatchNormalization(momentum=0.8)(temp_x)
        temp_x = Dense(512)(temp_x)
        temp_x = LeakyReLU(alpha=0.2)(temp_x)
        temp_x = BatchNormalization(momentum=0.8)(temp_x)
        temp_x = Dense(1024)(temp_x)
        temp_x = LeakyReLU(alpha=0.2)(temp_x)
        temp_x = BatchNormalization(momentum=0.8)(temp_x)
        temp_x = Dense(np.prod(self.img_shape), activation='tanh')(temp_x)
        temp_x = Reshape(self.img_shape)(temp_x)

        model = Model(input=Input_g_noise, output=temp_x)
        # G_Out = model(Input_g_noise)
        # Gen_Model = Model(input=Input_g_noise, output=G_Out)
        model.summary()

        return model

    def build_discriminator(self):

        Input_d_img = Input(shape=self.img_shape)
        temp_x = Flatten()(Input_d_img)
        temp_x = Dense(512)(temp_x)
        temp_x = LeakyReLU(alpha=0.2)(temp_x)
        temp_x = Dense(256)(temp_x)
        temp_x = LeakyReLU(alpha=0.2)(temp_x)
        temp_x = Dense(1, activation='sigmoid')(temp_x)

        model = Model(input=Input_d_img, output=temp_x)
        # D_Out = model(Input_d_img)
        # Dis_Model = Model(input=Input_d_img, output=D_Out)
        model.summary()

        return model

    def boundary_loss(self, y_true, y_pred):
        """
        Boundary seeking loss.
        Reference: https://wiseodd.github.io/techblog/2017/03/07/boundary-seeking-gan/
        """
        return 0.5 * K.mean((K.log(y_pred) - K.log(1 - y_pred))**2 + K.epsilon())

    def train(self, epochs, batch_size=128, sample_interval=50):

        # Load the dataset
        (X_train, y_train), (x_test, y_test) = mnist.load_data()

        print(X_train.shape, y_train.shape, x_test.shape, y_test.shape)
        # Rescale -1 to 1
        X_train = X_train / 127.5 - 1.
        X_train = np.expand_dims(X_train, axis=3)

        # Adversarial ground truths
        valid = np.ones((batch_size, 1))
        fake = np.zeros((batch_size, 1))

        for epoch in range(epochs):

            # ---------------------
            #  Train Discriminator
            # ---------------------

            # Select a random batch of images
            idx = np.random.randint(0, X_train.shape[0], batch_size)
            imgs = X_train[idx]

            noise = np.random.normal(0, 1, (batch_size, self.latent_dim))

            # Generate a batch of new images
            gen_imgs = self.generator.predict(noise)

            # Train the discriminator
            d_loss_real = self.discriminator.train_on_batch(imgs, valid)
            d_loss_fake = self.discriminator.train_on_batch(gen_imgs, fake)
            d_loss = 0.5 * np.add(d_loss_real, d_loss_fake)

            # ---------------------
            #  Train Generator
            # ---------------------

            g_loss = self.combined.train_on_batch(noise, valid)

            # Plot the progress
            # print(d_loss_real, d_loss_fake, d_loss, g_loss)
            print("{} [D loss: {:.2f}, acc.: {:.2f} %%] [G loss: {:.2f}]".format(epoch, d_loss[0], d_loss[1]*100, g_loss))

            # If at save interval => save generated image samples
            if epoch % sample_interval == 0:
                self.sample_images(epoch)

    def sample_images(self, epoch):
        r, c = 5, 5
        noise = np.random.normal(0, 1, (r * c, self.latent_dim))
        gen_imgs = self.generator.predict(noise)
        # Rescale images 0 - 1
        gen_imgs = 0.5 * gen_imgs + 0.5

        fig, axs = plt.subplots(r, c)
        cnt = 0
        for i in range(r):
            for j in range(c):
                axs[i,j].imshow(gen_imgs[cnt, :,:,0], cmap='gray')
                axs[i,j].axis('off')
                cnt += 1
        save_Path = 'Path / to / save / the / output / Images'
        fig.savefig("{}/mnist_{}.png".format(save_Path, epoch))
        plt.close()


if __name__ == '__main__':
    bgan = BGAN()
    bgan.train(epochs=30000, batch_size=32, sample_interval=200)
