import argparse
import sys
import cv2
import redis
import urllib.parse

'''
Capture frames from Camera and save to Redis Streams
Example: python3 edge-camera.py -u redis://192.168.7.100:6379 --fps 6 --rotate-90-clockwise true
'''
if __name__ == '__main__':
    '''
    Parse arguments
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--url', help='Redis URL',
                        type=str, default='redis://localhost:6379')
    parser.add_argument(
        '-o', '--output', help='Output stream key name', type=str, default='camera:0')
    parser.add_argument('--fmt', help='Frame storage format',
                        type=str, default='.jpg')
    parser.add_argument(
        '--fps', help='Frames per second (webcam)', type=float, default=1.0)
    parser.add_argument(
        '--maxlen', help='Maximum length of output stream', type=int, default=1000)
    parser.add_argument(
        '--width', help='Width of the frame', type=int, default=640)
    parser.add_argument(
        '--height', help='Height of the frame', type=int, default=480)
    parser.add_argument(
        '--rotate-90-clockwise', help='Angle to rotate', type=bool)
    args = parser.parse_args()

    '''
    Set up Redis connection
    '''
    url = urllib.parse.urlparse(args.url)
    conn = redis.Redis(host=url.hostname, port=url.port)
    if not conn.ping():
        raise Exception('Redis unavailable')
    print('Connected to Redis: {}'.format(url))

    '''
    Open the camera device at the ID 0
    '''
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise Exception('Could not open video device')

    '''
    Set camera resolution and FPS
    '''
    cap.set(cv2.CAP_PROP_FPS, args.fps)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    '''
    Capture frames
    '''
    while(True):
        try:
            ret, frame = cap.read()

            '''
            Rotate 90 degree clockwise if required
            '''
            if args.rotate_90_clockwise:
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)

            '''
            Encode and add frame to Redis Stream
            '''
            _, data = cv2.imencode(args.fmt, frame)
            img = data.tobytes()
            id = conn.execute_command(
                'xadd', args.output, 'MAXLEN', '~', args.maxlen, '*', 'img', img)
            print('id: {}, size: {}'.format(id, len(img)))

        except:
            print('Releasing the capture and exiting...')

            '''
            Release the capture
            '''
            cap.release()
            cv2.destroyAllWindows()
            sys.exit()
