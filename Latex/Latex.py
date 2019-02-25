import numpy as np
from os import listdir
from skimage import io
import matplotlib.pyplot as plt
from skimage.transform import resize, rotate
from skimage.util import random_noise, invert
import tensorflow as tf
import tensorflow.contrib.legacy_seq2seq as seq2seq
import math
import sklearn.model_selection as sk
import cv2
from scipy import ndimage
import copy, re
from Seq2SeqModel.Seq2SeqModel import Seq2SeqModel

class Latex(object):
    def __init__(self, model_dir=None, mean_train=None, std_train=None, plotting=False, verbose=False):
        tf.logging.set_verbosity(tf.logging.WARN)
        if model_dir is None:
            raise ValueError("model_dir needs to be defined")
        if mean_train is None:
            raise ValueError("mean_train needs to be defined")
        if std_train is None:
            raise ValueError("std_train needs to be defined")

        self.model_dir = model_dir
        self.mean_train = mean_train
        self.std_train = std_train
        self.plotting = plotting
        self.verbose = verbose
        self.label_names = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '-', '+', '=', 'leq', 'neq', 'geq', 'alpha',
                            'beta', 'lambda', 'lt', 'gt', 'x', 'y']
        self.ltokens = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '-', '+', '=', '#leq', '#neq', '#geq', '#alpha',
                            '#beta', '#lambda', '#lt', '#gt', 'x', 'y', '^', '#frac', '{', '}' ,' ']
        self.nof_labels = len(self.label_names)
        self.labels_dict = dict()
        i = 0
        for label in self.label_names:
            self.labels_dict[label] = i
            i += 1
        self.classifier = tf.estimator.Estimator(
            model_fn=self.cnn_model_fn, model_dir=self.model_dir
        )
        self.seqModel = Seq2SeqModel()
        self.seq_sess = tf.Session()
        self.seqModel.restore(self.seq_sess)

    def train(self, train_images, train_labels, steps):
        """ Further train the network

        Parameters
        ----------
        train_images : numpy array [X,48,48]
            Already normalized train images (-mean /std)
        train_labels : numpy array [X]
            Train labels (integer) coresponding to the train images 
        steps: 
            Number of steps for training
        """
        
        train_input_fn = tf.estimator.inputs.numpy_input_fn(
            x = {"x": train_images},
            y = train_labels,
            batch_size = 500,
            num_epochs = None,
            shuffle = True
        )
        self.classifier.train(
            input_fn = train_input_fn,
            steps = steps,
        )

    def normalize_single(self, symbol):
        symbol = np.copy(symbol).astype(np.float32)

        # range 0-1
        symbol /= np.max(symbol)
        
        rows, cols = symbol.shape
        # scale to 40x40
        inner_size = 40
        if rows > cols:
            factor = inner_size/rows
            rows = inner_size
            cols = int(round(cols*factor))
            cols = cols if cols > 2 else 2
            inner = cv2.resize(symbol, (cols,rows))
        else:
            factor = inner_size/cols
            cols = inner_size
            rows = int(round(rows*factor))
            rows = rows if rows > 2 else 2
            inner = cv2.resize(symbol, (cols, rows))
            
        # pad to 48x48
        outer_size = 48
        colsPadding = (int(math.ceil((outer_size-cols)/2.0)),int(math.floor((outer_size-cols)/2.0)))
        rowsPadding = (int(math.ceil((outer_size-rows)/2.0)),int(math.floor((outer_size-rows)/2.0)))
        outer = np.pad(inner,(rowsPadding,colsPadding),'constant', constant_values=(1,1))
        
        # center the mass
        shiftx,shifty = self.getBestShift(outer)
        shifted = self.shift(outer,shiftx,shifty)
        return shifted
        
    def getBestShift(self, img):
        inv = invert(img)
        cy,cx = ndimage.measurements.center_of_mass(inv)

        rows,cols = img.shape
        shiftx = np.round(cols/2.0-cx).astype(int)
        shifty = np.round(rows/2.0-cy).astype(int)

        return shiftx,shifty

    def shift(self, img,sx,sy):
        rows,cols = img.shape
        M = np.float32([[1,0,sx],[0,1,sy]])
        shifted = cv2.warpAffine(img,M,(cols,rows), borderValue=1)
        return shifted  

    def add_rectangles(self, img, bounding_boxes):
        img_color = np.asarray(np.dstack((img, img, img)), dtype=np.uint8)
        for bounding_box in bounding_boxes:
            xmin, xmax = bounding_box['xmin'], bounding_box['xmax']
            ymin, ymax = bounding_box['ymin'], bounding_box['ymax']
            img_color[ymin,xmin:xmax] = [255,0,0]
            img_color[ymax-1,xmin:xmax] = [255,0,0]
            img_color[ymin:ymax,xmin] = [255,0,0]
            img_color[ymin:ymax,xmax-1] = [255,0,0]
        return img_color

    def crop(self,img):
        crop = np.copy(img)/255
        h,w = img.shape
        left = 0
        while left < w//2 and np.sum(crop[:,left]) >= 0.98*h:
            left += 1
        right = w-1
        while right > w//2 and np.sum(crop[:,right]) >= 0.98*h:
            right -= 1
        if left > 0:
            left -1
        if right < h-1:
            right += 1
        crop = crop[:,left:right]
        
        top = 0
        while top < h//2 and np.sum(crop[top,:]) >= 0.98*w:
            top += 1
        bottom = h-1
        while bottom > h//2 and np.sum(crop[bottom,:]) >= 0.98*w:
            bottom -= 1
        if top > 0:
            top -= 1
        if bottom < h-1:
            bottom += 1
        crop = crop[top:bottom,:]*255
        return crop

    def cnn_model_fn(self, features, labels, mode):
        input_layer = tf.reshape(features["x"], [-1,48,48,1])
        
        conv1 = tf.layers.conv2d(
            inputs = input_layer,
            filters = 32,
            kernel_size = [7,7],
            padding="same",
            activation=tf.nn.relu
        )
        
        pool1 = tf.layers.max_pooling2d(
            inputs = conv1,
            pool_size=[2,2],
            strides=2
        )
        
        conv2 = tf.layers.conv2d(
            inputs = pool1,
            filters = 64,
            kernel_size = [7,7],
            padding="same",
            activation=tf.nn.relu
        )
        
        pool2 = tf.layers.max_pooling2d(
            inputs = conv2,
            pool_size=[2,2],
            strides=2
        )
        
        conv3 = tf.layers.conv2d(
            inputs = pool2,
            filters = 128,
            kernel_size = [7,7],
            padding="same",
            activation=tf.nn.relu
        )
        
        pool3 = tf.layers.max_pooling2d(
            inputs = conv3,
            pool_size=[2,2],
            strides=2
        )
        
        pool3_flat = tf.reshape(pool3, [-1, 6*6*128])
        dense = tf.layers.dense(inputs=pool3_flat, units=2048, activation=tf.nn.relu)
        dropout = tf.layers.dropout(
            inputs=dense,
            rate=0.4,
            training=mode == tf.estimator.ModeKeys.TRAIN
        )
        
        logits = tf.layers.dense(inputs=dropout, units=self.nof_labels)
        
        predictions = {
            "classes": tf.argmax(input=logits, axis=1),
            "probabilities": tf.nn.softmax(logits, name="softmax_tensor")
        }
        
        if mode == tf.estimator.ModeKeys.PREDICT:
            return tf.estimator.EstimatorSpec(mode=mode,predictions=predictions)
        
        onehot_labels = tf.one_hot(indices=tf.cast(labels, tf.int32), depth=self.nof_labels)
        loss = tf.losses.softmax_cross_entropy(
            onehot_labels=onehot_labels, logits=logits
        )
        
        if mode == tf.estimator.ModeKeys.TRAIN:
            optimizer = tf.train.GradientDescentOptimizer(learning_rate=0.01)
            train_op = optimizer.minimize(
                loss = loss,
                global_step=tf.train.get_global_step()
            )
            return tf.estimator.EstimatorSpec(mode=mode, loss=loss, train_op=train_op)
        
        eval_metric_ops = {
            "accuracy": tf.metrics.accuracy(
                labels=labels,
                predictions=predictions["classes"]
            )
        }
        return tf.estimator.EstimatorSpec(mode=mode, loss=loss, eval_metric_ops=eval_metric_ops)

    def get_bounding_boxes(self):
        ret, thresh = cv2.threshold(self.formula,220,255,cv2.THRESH_BINARY_INV)
        if self.plotting:
            print("Start threshold: ")
            plt.figure(figsize=(20,10)) 
            plt.imshow(thresh, cmap="gray")
            plt.show()
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        
        bounding_boxes = []
        id_c = 0
        for cnt in contours:
            x,y,w,h = cv2.boundingRect(cnt)
            # bounding boxes should not be too small
            if h > 10 or w > 10:
                bounding_boxes.append({
                    'id': id_c,
                    'xmin': x,
                    'xmax': x+w,
                    'ymin': y,
                    'ymax': y+h,
                    'combined': []
                })
                id_c += 1
        bounding_boxes = sorted(bounding_boxes, key=lambda k: (k['xmin'], k['ymin'])) 
        formula_rects = self.add_rectangles(self.formula, bounding_boxes)
        if self.plotting:
            print("Start bounding boxes: ")
            plt.figure(figsize=(20,10)) 
            plt.imshow(formula_rects, cmap="gray")
            plt.show()

        self.bounding_boxes = bounding_boxes    

    def normalize(self):
        self.possible_symbol_img = []
        self.pred_pos = []
        for bounding_box in self.bounding_boxes:
            xmin, xmax = bounding_box['xmin'], bounding_box['xmax']
            ymin, ymax = bounding_box['ymin'], bounding_box['ymax']
            dy = ymax-ymin
            dx = xmax-xmin

            normalized = self.normalize_single(self.formula[ymin:ymax,xmin:xmax])
            normalized -= self.mean_train
            normalized /= self.std_train
            
            self.possible_symbol_img.append(normalized)
            self.pred_pos.append(bounding_box)
        
    def predict(self, formula):
        self.formula = formula
        self.get_bounding_boxes()
        self.normalize()

        eval_input_fn = tf.estimator.inputs.numpy_input_fn(
            x = {"x": np.array(self.possible_symbol_img)},
            shuffle = False
        )

        pred_results = self.classifier.predict(input_fn=eval_input_fn)
        good_bounding_boxes = []
        formula_text = ""

        pred_pos = self.pred_pos

        skip = []
        c = 0

        lastYmin = None
        lastYmax = None
        for pred_result,pos in zip(pred_results,pred_pos):              
            symbol_no = pred_result['classes']
            symbol = self.label_names[symbol_no]
            acc = pred_result['probabilities'][symbol_no]
            if self.verbose:
                print("Recognized a %s with %.2f %% accuracy" % (symbol,acc*100))
            
            xmin, xmax = pos['xmin'],pos['xmax']
            ymin, ymax = pos['ymin'],pos['ymax']
            
            good_bounding_boxes.append({
                'xmin': xmin,
                'xmax': xmax,
                'ymin': ymin,
                'ymax': ymax,
                'symbol': symbol,
                'probs': pred_result['probabilities']
            })
            formula_text += symbol
            
            lastYmax = ymax
            lastYmin = ymin
            c += 1

        seq_data = self.seqModel.get_sequence_data(self.formula, self.nof_labels, good_bounding_boxes)

        bb_image = self.add_rectangles(formula, good_bounding_boxes)
        
        seq = self.seqModel.predict_single(self.seq_sess, seq_data[:26])

        return {'equation': seq, 'seq_data': seq_data, 'formula': self.post_process_latex(formula_text), 'output_image': bb_image, 'data': good_bounding_boxes}
    
    def post_process_latex(self, formula_text):
        formula_text = formula_text.replace("=", " = ")
        for symbol in ["leq","neq","geq"]:
            formula_text = formula_text.replace(symbol, " \\"+symbol+" ")
        for symbol in ["lambda","alpha","beta"]:
            formula_text = formula_text.replace(symbol, "\\"+symbol)
        formula_text = formula_text.replace("#lt", "<")
        formula_text = formula_text.replace("#gt", ">")
        return formula_text

    def filename2formula(self, filename):
        pos = filename.rfind("_")
        correct = filename[:pos]
        for symbol in ["leq","neq","geq","lambda","alpha","beta","frac"]:
            correct = correct.replace("#"+symbol, "\\"+symbol)
        correct = correct.replace("#lt", "<")
        correct = correct.replace("#gt", ">")
        return correct

    def filename2seq(self, filename):
        """ Convert a filename to the sequence array """
        pos = filename.rfind("_")
        correct = filename[:pos]
        parts = list(correct)
        tokens = []
        pi = -1
        pattern = re.compile("(#|[a-z])")
        while pi < len(parts)-1:
            pi += 1
            p = parts[pi]
            if p !="#":
                tokens.append(p)
            else:
                sp = pi
                while pattern.match(p):
                    pi += 1
                    p = parts[pi]
                tokens.append(''.join(parts[sp:pi]))
                pi -= 1
       
        
        tokens_dict = dict()
        i = 0
        for label in self.ltokens:
            tokens_dict[label] = i
            i += 1
        
        seq = []
        for token in tokens:
            seq.append(tokens_dict[token]) 
        return seq