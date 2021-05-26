import argparse
import cv2
import redis
import urllib.parse
import base64

if __name__ == '__main__':
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
    args = parser.parse_args()

    # Set up Redis connection
    url = urllib.parse.urlparse(args.url)
    conn = redis.Redis(host=url.hostname, port=url.port)
    if not conn.ping():
        raise Exception('Redis unavailable')
    print('Connected to Redis')

    # Open the camera device at the ID 0
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise Exception('Could not open video device')

    # Set camera resolution and FPS
    cap.set(cv2.CAP_PROP_FPS, args.fps)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    # Capture frames
    while(True):
        ret, frame = cap.read()
        _, data = cv2.imencode(args.fmt, frame)

        # Add frame to Redis Stream
        _id = conn.execute_command('xadd', args.output, 'MAXLEN', '~',
                                   args.maxlen, '*', 'img', base64.b64encode(data.tobytes()))
        print('id: {}'.format(_id))

        # Waits for a user input to quit the application
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

# Release the capture
cap.release()
cv2.destroyAllWindows()
