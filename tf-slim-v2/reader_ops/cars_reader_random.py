import time
import sys
import os
import threading
import time
import numpy as np
import tensorflow as tf
#import scipy
#from scipy.spatial.distance import cosine
#from sklearn.metrics.pairwise import cosine_similarity as cosine
#from sklearn.preprocessing import normalize
#from preprocessing import vgg_preprocessing as vp

base_dir = os.path.expanduser('~/data/cars198/')
file_name = os.path.join(base_dir,'profile/cars_train.lst')
#####train lst
with open(file_name,'r') as f:
    namelst = [a.strip() for a in f]
####label set
vector = {}
names = []
labels = []
for a in namelst:
    cur = a.split('\t')
    name,fg = cur[0],cur[1]
    names.append(name)
    labels.append(fg)
    if fg not in vector:
        vector[fg] = []
    vector[fg].append(name)
print 'len(names):',len(names)
print 'len(labels):',len(labels)
name2label = dict(zip(names,labels))

item_lsts = vector.keys()
item_lsts = sorted(item_lsts)
#######################
def data_iter():
    file_lists = names
    count_file = len(file_lists)
    file_lists = np.array(file_lists)
    while True:
        idxs = np.arange(0,count_file)
        np.random.shuffle(idxs)
        shuf_lists = file_lists[idxs]

        for batch_idx in xrange(0,len(shuf_lists)):
            img_a = shuf_lists[batch_idx].strip()
            #TODO should read to string.
            cur_fg = name2label[img_a]
            img_p = np.random.choice(vector[cur_fg])
            #TODO sampling negs according similarity
            negs = np.random.choice(item_lsts,6)
            while cur_fg in negs:negs = np.random.choice(item_lsts,6)

            a = open(base_dir+img_a,'r').read()
            p = open(base_dir+img_p,'r').read()
            n1 = open(base_dir+np.random.choice(vector[negs[0]]),'r').read()
            n2 = open(base_dir+np.random.choice(vector[negs[1]]),'r').read()
            n3 = open(base_dir+np.random.choice(vector[negs[2]]),'r').read()
            n4 = open(base_dir+np.random.choice(vector[negs[3]]),'r').read()
            n5 = open(base_dir+np.random.choice(vector[negs[4]]),'r').read()
            n6 = open(base_dir+np.random.choice(vector[negs[5]]),'r').read()
            yield a,p,n1,n2,n3,n4,n5,n6

class CustomRunner(object):
    def __init__(self,batch_size=10,shuffle=True,vp=None):
        self.batch_size = batch_size
        self.image_a = tf.placeholder(tf.string,[])
        self.image_p = tf.placeholder(tf.string,[])
        self.image_n1 = tf.placeholder(tf.string,[])
        self.image_n2 = tf.placeholder(tf.string,[])
        self.image_n3 = tf.placeholder(tf.string,[])
        self.image_n4 = tf.placeholder(tf.string,[])
        self.image_n5 = tf.placeholder(tf.string,[])
        self.image_n6 = tf.placeholder(tf.string,[])
        self.vp=vp
        # The actual queue of data. The queue contains a vector for
        # the mnist features, and a scalar label.
        c_sp=[224,224,3]
        c_shapes=[c_sp]*8
        c_dtypes=[tf.float32]*8
        if shuffle:
            self.queue = tf.RandomShuffleQueue(shapes=c_shapes,
                                  dtypes=c_dtypes,
                                  capacity=16,
                                  min_after_dequeue=9)
        else:
            self.queue = tf.FIFOQueue(shapes=c_shapes,
                                  dtypes=c_dtypes,
                                  capacity=16)
        # The symbolic operation to add data to the queue
        # we could do some preprocessing here or do it in numpy. In this example
        # we do the scaling in numpy
        img_a = self.transfer(self.image_a,'anchor')
        img_p = self.transfer(self.image_p,'positive')
        img_n1 = self.transfer(self.image_n1,'neg1')
        img_n2 = self.transfer(self.image_n2,'neg2')
        img_n3 = self.transfer(self.image_n3,'neg3')
        img_n4 = self.transfer(self.image_n4,'neg4')
        img_n5 = self.transfer(self.image_n5,'neg5')
        img_n6 = self.transfer(self.image_n6,'neg6')
        features=[img_a,img_p,img_n1,img_n2,img_n3,img_n4,img_n5,img_n6]
        self.enqueue_op = self.queue.enqueue_many(features)
    def transfer(self,input_string,prefix):
    	img = tf.cast(tf.image.decode_jpeg(input_string,channels=3),tf.float32)
    	return tf.expand_dims(self.vp(img,224,224,prefix=prefix),0)
    def get_inputs(self):
        """
        Return's tensors containing a batch of images and labels
        """
        #TODO fixed batch_size
        images_batch= self.queue.dequeue_many(self.batch_size)
        return images_batch

    def thread_main(self, sess,coord):
        """
        Function run on alternate thread. Basically, keep adding data to the queue.
        """
        for a,p,n1,n2,n3,n4,n5,n6 in data_iter():
            feed_d = {self.image_a:a,
                      self.image_p:p,
                      self.image_n1:n1,
                      self.image_n2:n2,
                      self.image_n3:n3,
                      self.image_n4:n4,
                      self.image_n5:n5,
                      self.image_n6:n6,}
            sess.run(self.enqueue_op, feed_dict=feed_d)
            if coord.should_stop():
                break

    def start_threads(self, sess,coord,n_threads=2):
        """ Start background threads to feed queue """
        threads = []
        for n in range(n_threads):
            t = threading.Thread(target=self.thread_main, args=(sess,coord,))
            t.daemon = True # thread will close when parent quits
            t.start()
            threads.append(t)
        return threads
if __name__ == '__main__':
    # Doing anything with data on the CPU is generally a good idea.
    with tf.device("/cpu:0"):
        custom_runner = CustomRunner(4)
        images_batch = custom_runner.get_inputs()
    print images_batch
    square_op = tf.concat(0,images_batch)
    with tf.Session() as sess:
        init = tf.initialize_all_variables()
        sess.run(init)
        # start the tensorflow QueueRunner's
        tf.train.start_queue_runners(sess=sess)
        # start our custom queue runner's threads
        coord = tf.train.Coordinator()
        threads = custom_runner.start_threads(sess,coord)
        try:
            for a in xrange(10):
                if coord.should_stop():
                    break
                print sess.run(square_op).shape
        except Exception,e:
            coord.request_stop(e)
        finally:
            coord.request_stop()
            coord.join(threads)
        print 'finish'
