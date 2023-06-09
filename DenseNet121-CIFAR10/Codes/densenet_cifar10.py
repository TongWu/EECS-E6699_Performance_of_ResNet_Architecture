# -*- coding: utf-8 -*-
"""DenseNet-CIFAR10.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1g2E3SAaQCyaWF6he1uJ348lUggIqlqDU

# Download packages
"""

!pip install git+https://github.com/qubvel/classification_models.git

!pip install tensorflow-addons

"""# Initialisation and data cleaning"""

# Import lib
import tensorflow as tf
from tensorflow.keras.layers import Input, Conv2D, BatchNormalization, Activation, Add, Flatten, Dense, GlobalAveragePooling2D, MaxPooling2D
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.datasets import cifar10
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.applications.densenet import DenseNet121
import matplotlib.pyplot as plt
from tensorflow.keras.optimizers import Adam, SGD, Nadam
import time
from classification_models.keras import Classifiers
import tensorflow_addons as tfa
from keras import backend as K

import subprocess
print(subprocess.getoutput('nvidia-smi'))

(x_train, y_train), (x_test, y_test) = cifar10.load_data()

# Normalize pixel values to be between 0 and 1
x_train, x_test = x_train / 255.0, x_test / 255.0

# Convert class vectors to binary class matrices
y_train = to_categorical(y_train, 10)
y_test = to_categorical(y_test, 10)
def preprocess_image(image, label):
    image = tf.image.resize(image, (224, 224))
    image = tf.keras.applications.vgg16.preprocess_input(image)
    return image, label

train_ds = tf.data.Dataset.from_tensor_slices((x_train, y_train))
train_ds = train_ds.map(preprocess_image).batch(32)

val_ds = tf.data.Dataset.from_tensor_slices((x_test, y_test))
val_ds = val_ds.map(preprocess_image).batch(32)

"""# Build VGGNet-16 and padam"""

num_classes = 10
base_model = DenseNet121(weights='imagenet', include_top=False, input_shape=(224, 224, 3))
x = Flatten()(base_model.output)
x = Dense(1024, activation='relu')(x)
x = Dense(512, activation='relu')(x)
output = Dense(num_classes, activation='softmax')(x)
model = Model(inputs=base_model.input, outputs=output)

class Padam(tfa.optimizers.RectifiedAdam):
    def __init__(self, p=0.5, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.p = p
        
    def _resource_apply_dense(self, grad, var, apply_state=None):
        var_dtype = var.dtype.base_dtype
        local_step = tf.cast(self.iterations + 1, var_dtype)
        beta_1_t = tf.cast(self._get_hyper('beta_1', var_dtype), var_dtype)
        beta_2_t = tf.cast(self._get_hyper('beta_2', var_dtype), var_dtype)
        one_minus_beta_1_t = 1 - beta_1_t
        one_minus_beta_2_t = 1 - beta_2_t
        
        step_size = self._get_hyper('learning_rate', var_dtype) * (tf.sqrt(1 - tf.pow(beta_2_t, local_step)) / (1 - tf.pow(beta_1_t, local_step)))

        m = self.get_slot(var, 'm')
        m_t = (m * beta_1_t) + (grad * one_minus_beta_1_t)
        m_hat_t = m_t / (1 - tf.pow(beta_1_t, local_step))
        
        v = self.get_slot(var, 'v')
        v_t = (v * beta_2_t) + (tf.square(grad) * one_minus_beta_2_t)
        v_hat_t = v_t / (1 - tf.pow(beta_2_t, local_step))
        
        denom = tf.pow(tf.sqrt(v_hat_t) + K.epsilon(), self.p)
        var_t = var - step_size * (m_hat_t / denom)
        
        return tf.compat.v1.assign(var, var_t)

def train_model_with_optimizer(optimizer, batch_size, epochs):
    # Untested merge start #
    num_classes = 10
    base_model = DenseNet121(weights='imagenet', include_top=False, input_shape=(224, 224, 3))
    x = Flatten()(base_model.output)
    x = Dense(1024, activation='relu')(x)
    x = Dense(512, activation='relu')(x)
    output = Dense(num_classes, activation='softmax')(x)
    model = Model(inputs=base_model.input, outputs=output)
    # Untested merge finished #
    model.compile(optimizer=optimizer, loss='categorical_crossentropy', metrics=['accuracy', 'top_k_categorical_accuracy'])
    start_time = time.time()
    history = model.fit(train_ds, batch_size=batch_size, epochs=epochs, validation_data=val_ds, verbose=0)
    end_time = time.time()
    training_time = end_time - start_time
    return history, training_time, model

"""# Train Model"""

# 200 epochs (Same as the paper)
# Need to re-complie the model if ran 50 epochs before
optimizers = {
    'Adam': Adam(learning_rate=0.001),
    'SGD': SGD(learning_rate=0.001, momentum=0.9),
    'Nadam': Nadam(learning_rate=0.001),
    'Adam_Amsgrad': Adam(learning_rate=0.001, amsgrad=True),
    'Padam': Padam(learning_rate=0.1, total_steps=10000, p=0.125, beta_1=0.9, beta_2=0.999, weight_decay=5e-4)
}

histories = {}
training_times = {}
models = {}

for name, optimizer in optimizers.items():
    print(f"Training with {name} optimizer...")
    histories[name], training_times[name], models[name] = train_model_with_optimizer(optimizer, 32, 100)

for name, model in models.items():
    model.save(f'./Model/resnet_model_{name}.h5')

"""# Plot figure without padam"""

plt.figure(figsize=(12, 6))

for name, history in histories.items():
  if name != 'Padam':
    plt.plot(history.history['loss'], label=f"{name}")

plt.xlabel('Epochs')
plt.ylabel('Loss')
plt.legend()
plt.title('Training Loss Comparison for Different Optimizers')
# Save the figure before displaying it
plt.savefig('./Results/Train_Loss_nopadam.png', dpi=300, bbox_inches='tight')
plt.show()

plt.figure(figsize=(12, 6))

for name, history in histories.items():
  if name != 'Padam':
    test_error = [1 - accuracy for accuracy in history.history['val_accuracy']]
    plt.plot(test_error, label=f"{name}", linestyle='--')

plt.xlabel('Epochs')
plt.ylabel('Loss / Error')
plt.legend()
plt.title('Test Error Comparison for Different Optimizers')
# Save the figure before displaying it
plt.savefig('./Results/Test_Error_nopadam.png', dpi=300, bbox_inches='tight')
plt.show()

plt.figure(figsize=(10, 5))
for name, history in histories.items():
  if name != 'Padam':
    plt.plot(history.history['val_accuracy'], label=f"{name}")
plt.xlabel('Epochs')
plt.ylabel('Accuracy')
plt.legend()
plt.title('Validation Accuracy for Different Optimizers')
plt.savefig('./Results/validation_accuracy_nopadam.png', dpi=300, bbox_inches='tight')
plt.show()

plt.figure(figsize=(10, 5))

# Exclude the 'Padam' optimizer
filtered_optimizers = {k: v for k, v in training_times.items() if k != 'Padam'}

plt.bar(filtered_optimizers.keys(), filtered_optimizers.values())
plt.xlabel('Optimizer')
plt.ylabel('Time (s)')
plt.title('Training Time for Different Optimizers (excluding Padam)')

plt.savefig('./Results/training_time_nopadam.png', dpi=300, bbox_inches='tight')
plt.show()

fig, axes = plt.subplots(2, 2, figsize=(15, 10))

# Training Loss
for name, history in histories.items():
  if name != 'Padam':
    axes[0, 0].plot(history.history['loss'], label=f"{name}")
axes[0, 0].set_xlabel('Epochs')
axes[0, 0].set_ylabel('Loss')
axes[0, 0].legend()
axes[0, 0].set_title('Training Loss')

# Test Error
for name, history in histories.items():
  if name != 'Padam':
    test_error = [1 - accuracy for accuracy in history.history['val_accuracy']]
    axes[0, 1].plot(test_error, label=f"{name}")
axes[0, 1].set_xlabel('Epochs')
axes[0, 1].set_ylabel('Error')
axes[0, 1].legend()
axes[0, 1].set_title('Test Error')

# Validation Accuracy
for name, history in histories.items():
  if name != 'Padam':
    axes[1, 0].plot(history.history['val_accuracy'], label=f"{name}")
axes[1, 0].set_xlabel('Epochs')
axes[1, 0].set_ylabel('Accuracy')
axes[1, 0].legend()
axes[1, 0].set_title('Validation Accuracy')

# Training Time
filtered_optimizers = {k: v for k, v in training_times.items() if k != 'Padam'}
axes[1, 1].bar(filtered_optimizers.keys(), filtered_optimizers.values())
axes[1, 1].set_xlabel('Optimizer')
axes[1, 1].set_ylabel('Time (s)')
axes[1, 1].set_title('Training Time')

plt.tight_layout()
plt.savefig('./Results/matrix_nopadam.png', dpi=300, bbox_inches='tight')
plt.show()

"""# Plot figure with padam"""

plt.figure(figsize=(12, 6))

for name, history in histories.items():
    plt.plot(history.history['loss'], label=f"{name}")

plt.xlabel('Epochs')
plt.ylabel('Loss')
plt.legend()
plt.title('Training Loss Comparison for Different Optimizers')
# Save the figure before displaying it
plt.savefig('./Results/Train_Loss.png', dpi=300, bbox_inches='tight')
plt.show()

plt.figure(figsize=(12, 6))

for name, history in histories.items():
    # plt.plot(history.history['loss'], label=f"{name} Training Loss")
    test_error = [1 - accuracy for accuracy in history.history['val_accuracy']]
    plt.plot(test_error, label=f"{name}", linestyle='--')

plt.xlabel('Epochs')
plt.ylabel('Loss / Error')
plt.legend()
plt.title('Test Error Comparison for Different Optimizers')
# Save the figure before displaying it
plt.savefig('./Results/Test_Error.png', dpi=300, bbox_inches='tight')
plt.show()

plt.figure(figsize=(10, 5))
for name, history in histories.items():
    plt.plot(history.history['val_accuracy'], label=f"{name}")
plt.xlabel('Epochs')
plt.ylabel('Accuracy')
plt.legend()
plt.title('Validation Accuracy for Different Optimizers')
plt.savefig('./Results/validation_accuracy.png', dpi=300, bbox_inches='tight')
plt.show()

plt.figure(figsize=(10, 5))
plt.bar(training_times.keys(), training_times.values())
plt.xlabel('Optimizer')
plt.ylabel('Time (s)')
plt.title('Training Time for Different Optimizers')
plt.savefig('./Results/training_time.png', dpi=300, bbox_inches='tight')
plt.show()

fig, axes = plt.subplots(2, 2, figsize=(15, 10))

# Training Loss
for name, history in histories.items():
    axes[0, 0].plot(history.history['loss'], label=f"{name}")
axes[0, 0].set_xlabel('Epochs')
axes[0, 0].set_ylabel('Loss')
axes[0, 0].legend()
axes[0, 0].set_title('Training Loss')

# Test Error
for name, history in histories.items():
    test_error = [1 - accuracy for accuracy in history.history['val_accuracy']]
    axes[0, 1].plot(test_error, label=f"{name}")
axes[0, 1].set_xlabel('Epochs')
axes[0, 1].set_ylabel('Error')
axes[0, 1].legend()
axes[0, 1].set_title('Test Error')

# Validation Accuracy
for name, history in histories.items():
    axes[1, 0].plot(history.history['val_accuracy'], label=f"{name}")
axes[1, 0].set_xlabel('Epochs')
axes[1, 0].set_ylabel('Accuracy')
axes[1, 0].legend()
axes[1, 0].set_title('Validation Accuracy')

# Training Time
axes[1, 1].bar(training_times.keys(), training_times.values())
axes[1, 1].set_xlabel('Optimizer')
axes[1, 1].set_ylabel('Time (s)')
axes[1, 1].set_title('Training Time')

plt.tight_layout()
plt.savefig('./Results/matrix.png', dpi=300, bbox_inches='tight')
plt.show()

!zip -r Model.zip ./Model
!zip -r Result.zip ./Results
!cp Model.zip /content/drive/MyDrive/DenseNet/
!cp Result.zip /content/drive/MyDrive/DenseNet/