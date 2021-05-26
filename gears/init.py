# RedisEdge realtime video analytics initialization script
import argparse
import redis
from urllib.parse import urlparse

if __name__ == '__main__':
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-i', '--camera_id', help='Input video stream key camera ID', type=str, default='0')
    parser.add_argument('-p', '--camera_prefix',
                        help='Input video stream key prefix', type=str, default='camera')
    parser.add_argument('-u', '--url', help='RedisEdge URL',
                        type=str, default='redis://127.0.0.1:6379')
    args = parser.parse_args()

    # Set up some vars
    input_stream_key = '{}:{}'.format(
        args.camera_prefix, args.camera_id)  # Input video stream key name

    # Set up Redis connection
    url = urlparse(args.url)
    conn = redis.Redis(host=url.hostname, port=url.port)
    if not conn.ping():
        raise Exception('Redis unavailable')

    print('Creating timeseries keys and downsampling rules - ', end='')
    # RedisTimeSeries replies list
    res = []
    labels = ['LABELS', args.camera_prefix, args.camera_id,
              '__name__']  # A generic list of timeseries keys labels

    # Create the main timeseries key
    res.append(conn.execute_command(
        'TS.CREATE', '{}:people'.format(input_stream_key), *labels, 'people'))

    # Set up timeseries downsampling keys and rules
    wins = [1, 5, 15]             # Downsampling windows
    aggs = ['avg', 'min', 'max']  # Downsampling aggregates
    for w in wins:
        for a in aggs:
            res.append(conn.execute_command('TS.CREATE', '{}:people:{}:{}m'.format(
                input_stream_key, a, w), *labels, 'people_{}_{}m'.format(a, w)))
            res.append(conn.execute_command('TS.CREATERULE', '{}:people'.format(
                input_stream_key), '{}:people:{}:{}m'.format(input_stream_key, a, w), 'AGGREGATION', a, w*60))

    # Set up fps timeseries keys
    res.append(conn.execute_command(
        'TS.CREATE', '{}:in_fps'.format(input_stream_key), *labels, 'in_fps'))
    res.append(conn.execute_command('TS.CREATE', '{}:out_fps'.format(
        input_stream_key), *labels, 'out_fps'))

    # Set up profiler timeseries keys
    metrics = ['read', 'resize', 'model', 'script', 'boxes', 'store', 'total']
    for m in metrics:
        res.append(conn.execute_command('TS.CREATE', '{}:prf_{}'.format(
            input_stream_key, m), *labels, 'prf_{}'.format(m)))
    print(res)

    # Load the gear
    print('Loading gear - ', end='')
    with open('yolo.py', 'rb') as f:
        gear = f.read()
        res = conn.execute_command('RG.PYEXECUTE', gear)
        print(res)
