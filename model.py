import tensorflow as tf
import numpy as np
from ops import *

from tardis import TardisStateTuple, TardisCell

def cnn():
    x = tf.placeholder(tf.float32, [None, width * height])
    obs = tf.reshape(x, [-1, width, height, 1])
    #x = tf.placeholder(tf.float32, [None, width, height, 1])
    
    # 3 conv layers
    #obs = batch_norm(conv2d(obs, 4, 'conv1', (3, 3), (2, 2)))
    #obs = batch_norm(conv2d(obs, 4, 'conv2', (3, 3), (2, 2)))
    #obs = batch_norm(conv2d(obs, 4, 'conv3', (3, 3), (2, 2)))
    
    obs = tf.nn.relu(conv2d(obs, 4, 'conv1', (3, 3), (2, 2)))
    obs = tf.nn.relu(conv2d(obs, 4, 'conv2', (3, 3), (2, 2)))
    #obs = tf.nn.relu(conv2d(obs, 4, 'conv3', (3, 3), (2, 2)))
    
    #obs = conv2d(obs, 4, 'conv1', (3, 3), (2, 2))
    #obs = conv2d(obs, 4, 'conv2', (3, 3), (2, 2))
    #obs = conv2d(obs, 4, 'conv3', (3, 3), (2, 2))
    #obs = conv2d(obs, 4, 'conv4', (3, 3), (2, 2))
    obs = flatten(obs)
    
    # linear layer
    #obs = linear(x, 100, 'linear_a')
    #obs = linear(obs, 50, 'linear0')
    #obs = linear(obs, 25, 'linear1')
    obs = linear(obs, num_classes, 'linear2')
    
    
    y = tf.placeholder(tf.float32, [None, num_classes])
    loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=obs, labels=y))
    train_op = tf.train.AdamOptimizer(1e-2).minimize(loss)
    
    correct_prediction = tf.equal(tf.argmax(obs, 1), tf.argmax(y, 1))
    accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))
    
    return x, y, loss, train_op, accuracy
    

def length(sequence):
  used = tf.sign(tf.reduce_max(tf.abs(sequence), 2))
  length = tf.reduce_sum(used, 1)
  length = tf.cast(length, tf.int32)
  return length  
  
# Force everything to be max length
def length_all(sequence):
  used = tf.sign(tf.reduce_max(tf.abs(sequence), 2) + 1)
  length = tf.reduce_sum(used, 1)
  length = tf.cast(length, tf.int32)
  return length  
    
# https://danijar.com/variable-sequence-lengths-in-tensorflow/
# http://www.wildml.com/2016/08/rnns-in-tensorflow-a-practical-guide-and-undocumented-features/
def rnn():

    rnn_size = 128
    
    x = tf.placeholder(tf.float32, [None, width * height])
    
    # batch_size, max_time, chunk_size
    sequence = obs = tf.reshape(x, [-1, width, height])
    print(sequence.get_shape())
    
    seq_len = length_all(obs)
    #obs = tf.transpose(obs, [1, 0, 2])
    
    #obs = tf.split(obs, width, 0)
    #obs = tf.concat(obs, axis=0)
    #obs = tf.reshape(x, [-1, 1, width])
    
    print('1', type(obs), obs, tf.shape(obs)[:1])
    lstm = tf.contrib.rnn.BasicLSTMCell(rnn_size)
    
    
    lstm_outputs, lstm_state = tf.nn.dynamic_rnn(lstm, obs, dtype=tf.float32, sequence_length=seq_len)
    #lstm_outputs, lstm_state = tf.nn.dynamic_rnn(lstm, obs, dtype=tf.float32, sequence_length=l)
    
    print(lstm_outputs)
    
    obs = linear(flatten(lstm_outputs), num_classes, 'linear0')

    y = tf.placeholder(tf.float32, [None, num_classes])
    loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=obs, labels=y))
    train_op = tf.train.AdamOptimizer(1e-2).minimize(loss)
    
    correct_prediction = tf.equal(tf.argmax(obs, 1), tf.argmax(y, 1))
    accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

    return x, y, loss, train_op, accuracy, seq_len
    
    
    

def omniglot_rnn(num_classes):

    lstm_size = 64
    memory_size = 16
    word_size = 16
    
    width = 28
    height = 28
    
    with tf.variable_scope('omni_rnn'):
    
        # image concatenated with prev step's answer
        x = tf.placeholder(tf.float32, [None, width * height + num_classes])
        
        
        with tf.variable_scope('FeatureExtractor'):
            obs, prev = tf.split(x, (width * height, num_classes), axis=1)

            obs = tf.reshape(obs, [-1, width, height, 1])

            obs = tf.nn.relu(conv2d(obs, 4, 'conv1', (3, 3), (2, 2)))
            obs = tf.nn.relu(conv2d(obs, 4, 'conv2', (3, 3), (2, 2)))
            obs = tf.nn.relu(conv2d(obs, 4, 'conv3', (3, 3), (2, 2)))
            
            obs = flatten(obs)
            
            obs = tf.concat((obs, prev), 1)
        
        
        # add fake time of 1
        obs = tf.expand_dims(obs, [0])

        seq_len = length_all(obs)
        
        cell = TardisCell(lstm_size, memory_size, word_size)
        
        
        c_init = np.zeros((1, cell.state_size.c), np.float32)
        h_init = np.zeros((1, cell.state_size.h), np.float32)
        m_init = np.zeros((1, cell.state_size.m), np.float32)
        
        zero_state = TardisStateTuple(c_init, h_init, m_init)
        
        c_placeholder = tf.placeholder(tf.float32, [None, cell.state_size.c])
        h_placeholder = tf.placeholder(tf.float32, [None, cell.state_size.h])
        m_placeholder = tf.placeholder(tf.float32, [None, cell.state_size.m])
        
        state_init = TardisStateTuple(c_placeholder, h_placeholder, m_placeholder)
        
        tardis_outputs, tardis_state = tf.nn.dynamic_rnn(
            cell=cell, 
            inputs=obs, 
            initial_state=state_init,
            #dtype=tf.float32, 
            sequence_length=seq_len, 
            time_major=False)
        
        obs = linear(flatten(tf.transpose(tardis_outputs, (1, 0, 2))), num_classes, 'linear0')
        
        guess = tf.argmax(obs, 1)
        
        var_list = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, tf.get_variable_scope().name)
        
        print(var_list)
        
        trainable_var_list = [var for var in var_list if 'FeatureExtractor' not in var.op.name]
        
        print(trainable_var_list)

        y = tf.placeholder(tf.float32, [None, num_classes])
        loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=obs, labels=y))
        train_op = tf.train.AdamOptimizer(1e-3).minimize(loss, var_list=trainable_var_list)
        
        correct_prediction = tf.equal(tf.argmax(obs, 1), tf.argmax(y, 1))
        accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

        return x, y, loss, train_op, accuracy, seq_len, state_init, tardis_state, cell, guess, obs