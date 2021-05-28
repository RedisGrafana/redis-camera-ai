import io
import cv2
import redisAI
import numpy as np
from time import time
from PIL import Image, ImageDraw
import base64
from redisgears import executeCommand as execute


class SimpleMovingAverage(object):
    def __init__(self, value=0.0, count=7):
        '''
        @value - the initialization value
        @count - the count of samples to keep
        '''
        self.count = int(count)
        self.current = float(value)
        self.samples = [self.current] * self.count

    def __str__(self):
        return str(round(self.current, 3))

    def add(self, value):
        '''
        Adds the next value to the average
        '''
        v = float(value)
        self.samples.insert(0, v)

        o = self.samples.pop()
        self.current = self.current + (v-o)/self.count


class Profiler(object):
    names = []
    data = {}
    last = None

    def __init__(self):
        pass

    def __str__(self):
        s = ''
        for name in self.names:
            s = '{}{}:{}, '.format(s, name, self.data[name])

        return(s[:-2])

    def __delta(self):
        '''
        Returns the time delta between invocations in milliseconds
        '''
        now = time()*1000
        if self.last is None:
            self.last = now

        value = now - self.last
        self.last = now

        return value

    def start(self):
        '''
        Starts the profiler
        '''
        self.last = time()*1000
        return self

    def add(self, name):
        '''
        Adds/updates a step's duration
        '''
        value = self.__delta()

        if name not in self.data:
            self.names.append(name)
            self.data[name] = SimpleMovingAverage(value=value)
        else:
            self.data[name].add(value)

    def assign(self, name, value):
        '''
        Assigns a step with a value
        '''
        if name not in self.data:
            self.names.append(name)
            self.data[name] = SimpleMovingAverage(value=value)
        else:
            self.data[name].add(value)

    def get(self, name):
        '''
        Gets a step's value
        '''
        return self.data[name].current


def processImage(img, height):
    '''
    Resize a rectangular image to a padded square (letterbox)
    '''
    color = (127.5, 127.5, 127.5)
    shape = img.shape[:2]

    ratio = float(height) / max(shape)
    newShape = (int(round(shape[1] * ratio)), int(round(shape[0] * ratio)))

    dw = (height - newShape[0]) / 2
    dh = (height - newShape[1]) / 2
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))

    img = cv2.resize(img, newShape, interpolation=cv2.INTER_LINEAR)
    img = cv2.copyMakeBorder(img, top, bottom, left,
                             right, cv2.BORDER_CONSTANT, value=color)
    img = np.asarray(img, dtype=np.float32)

    '''
    Normalize 0..255 to 0..1.00
    '''
    img /= 255.0

    return img


def runYolo(x):
    '''
    Runs the model on an input image from the stream
    '''
    prf = Profiler().start()

    '''
    Read the image from the stream's message
    '''
    buf = io.BytesIO(x['value']['img'])
    pilImage = Image.open(buf)
    prf.add('read')

    '''
    Resize, normalize and tensorize the image for the model (number of images, width, height, channels)
    '''
    imageSize = round(pilImage.height/2)
    image = processImage(np.array(pilImage), imageSize)
    imageTensor = redisAI.createTensorFromBlob(
        'FLOAT', [1, imageSize, imageSize, 3], bytearray(image.tobytes()))
    prf.add('resize')

    '''
    Create the RedisAI model runner and run it
    '''
    modelRunner = redisAI.createModelRunner('yolo:model')
    redisAI.modelRunnerAddInput(modelRunner, 'input', imageTensor)
    redisAI.modelRunnerAddOutput(modelRunner, 'output')
    modelReplies = redisAI.modelRunnerRun(modelRunner)
    modelOutput = modelReplies[0]
    prf.add('model')

    '''
    The model's output is processed with a PyTorch script for non maxima suppression
    '''
    scriptRunner = redisAI.createScriptRunner('yolo:script', 'boxes_from_tf')
    redisAI.scriptRunnerAddInput(scriptRunner, modelOutput)
    redisAI.scriptRunnerAddOutput(scriptRunner)
    scriptReply = redisAI.scriptRunnerRun(scriptRunner)
    scriptOutput = scriptReply[0]

    '''
    The script outputs bounding boxes
    '''
    shape = redisAI.tensorGetDims(scriptOutput)
    scriptData = redisAI.tensorGetDataAsBlob(scriptOutput)
    scriptBoxes = np.frombuffer(scriptData, dtype=np.float32).reshape(shape)
    prf.add('script')

    boxes = []
    people = 0
    ratio = float(imageSize) / max(pilImage.width, pilImage.height)
    padX = (imageSize - pilImage.width * ratio) / 2
    padY = (imageSize - pilImage.height * ratio) / 2

    '''
    Iterate boxes to extract the people
    '''
    draw = ImageDraw.Draw(pilImage)
    for box in scriptBoxes[0]:

        '''
        Remove zero-confidence detections and not people
        '''
        if box[4] == 0.0 or box[-1] != 14:
            continue

        people += 1

        '''
        Descale bounding box coordinates back to original image size
        '''
        x1 = (imageSize * (box[0] - 0.5 * box[2]) - padX) / ratio
        y1 = (imageSize * (box[1] - 0.5 * box[3]) - padY) / ratio
        x2 = (imageSize * (box[0] + 0.5 * box[2]) - padX) / ratio
        y2 = (imageSize * (box[1] + 0.5 * box[3]) - padY) / ratio
        boxes += [x1, y1, x2, y2]

        '''
        Draw boxes on the frame
        '''
        draw.rectangle(((x1, y1), (x2, y2)), width=5, outline='red')

    prf.add('boxes')

    '''
    Encode image and add text
    '''
    key = x['key']
    id = x['id']
    numpyImage = np.array(pilImage)
    numpyImage = cv2.cvtColor(numpyImage, cv2.COLOR_BGR2RGB)
    cv2.putText(numpyImage, '{}:{} people {}'.format(key, id, people), (10, pilImage.height - 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 1, cv2.LINE_AA)
    _, img = cv2.imencode('.jpg', numpyImage)

    '''
    Store the output in the yolo stream
    '''
    yoloStreamId = execute('XADD', '{}:yolo'.format(key), 'MAXLEN', '~',
                           1000, '*', 'ref', id, 'boxes', boxes, 'people', people, 'img', base64.b64encode(img.tobytes()))

    labels = ['LABELS', 'camera', key]
    inputStreamMsec = int(str(id).split('-')[0])
    yoloStreamMsec = int(str(yoloStreamId).split('-')[0])

    '''
    Add a sample to the output people and fps timeseries
    '''
    execute('TS.ADD', '{}:people'.format(key),
            inputStreamMsec, people, *labels)
    prf.assign('total', yoloStreamMsec - inputStreamMsec)

    '''
    Record profiler steps
    '''
    for name in prf.names:
        execute('TS.ADD', '{}:prf_{}'.format(key, name), inputStreamMsec,
                prf.data[name].current, *labels, 'data', name)

    prf.add('store')


'''
Create and register a gear that for each message in the stream
'''
gb = GearsBuilder('StreamReader')
gb.map(runYolo)
gb.register('camera:0')
