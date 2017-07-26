import os
from scipy.ndimage import imread
import numpy as np

class Sample():
    def __init__(self, filepath, classId, sampleId):
        self.filepath = filepath
        self.classId = classId
        self.sampleId = sampleId
        
        
    def load(self):
        # flatten to gray scale
        I = imread(self.filepath,flatten=True)
        return I
        
    def __str__(self):
        return '{}, {}, {}'.format(self.filepath, self.classId, self.sampleId)


class Character():
    def __init__(self, classId):
        self.samples = []
        self.classId = classId
        
    def add(self, sample):
        self.samples.append(sample)
        
    def load(self, n=1, flatten=False):
        return [(sample.load().flatten() if flatten else sample.load()) for sample in np.random.choice(self.samples, n, replace=False)]
        
        
class Omniglot():
    def __init__(self):
        # generate list of omniglot images on disk
        self.trainChars = {}
        self.testChars = {}
        
        for root, dirnames, filenames in os.walk('images_background'):
            for filename in filenames:
                classId = int(filename[:4])
                sampleId = int(filename[5:7])
                
                sample = Sample(os.path.join(root, filename), classId, sampleId)
                if classId not in self.trainChars:
                    self.trainChars[classId] = Character(classId)
                    
                self.trainChars[classId].add(sample)
                
                
        for root, dirnames, filenames in os.walk('images_evaluation'):
            for filename in filenames:
                classId = int(filename[:4])
                sampleId = int(filename[5:7])
                
                sample = Sample(os.path.join(root, filename), classId, sampleId)
                if classId not in self.testChars:
                    self.testChars[classId] = Character(classId)
                    
                self.testChars[classId].add(sample)
                
    def _GetBatch(self, sampleDict, batchSize, numClasses=1, samplesPerChar=1, one_hot=True, flatten=True):
    
        assert(batchSize <= numClasses * samplesPerChar)
    
        # generate random sample
        samples = np.random.choice(list(sampleDict.keys()), numClasses)
        
        x = []
        y = []
        
        for i in range(len(samples)):
            sample = samples[i]
            character = sampleDict[sample]
            x.extend(character.load(samplesPerChar, flatten=flatten))
            
            if one_hot:
                y_label = np.zeros(numClasses)
                y_label[i] = 1
            else:
                y_label = i
            
            y.extend([y_label] * samplesPerChar)
            
            
        zipped = list(zip(x, y))
        np.random.shuffle(zipped)
            
        x, y = list(zip(*zipped))
        x = list(x)
        y = list(y)
        
        return x[:batchSize], y[:batchSize]
        
    
    def TrainBatch(self, batchSize, classes=1, samples=1, one_hot=True):
        return self._GetBatch(self.trainChars, batchSize, classes, samples, one_hot)
    
    def TestBatch(self, batchSize, classes=1, samples=1, one_hot=True):
        return self._GetBatch(self.testChars, batchSize, classes, samples, one_hot)
            
# test
if __name__ == '__main__':
    og = Omniglot()
    x, y = og.TrainBatch(1, classes=1, samples=1)
    print(x, y)