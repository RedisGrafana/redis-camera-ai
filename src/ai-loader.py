import argparse
import redis
from urllib.parse import urlparse

'''
Loading AI model and script
Example: python3 ai-loader.py -u redis://cluster.remote:6379
'''
if __name__ == '__main__':
    '''
    Parse arguments
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--device', help='CPU or GPU',
                        type=str, default='CPU')
    parser.add_argument('-u', '--url', help='Redis URL',
                        type=str, default='redis://127.0.0.1:6379')
    args = parser.parse_args()

    '''
    Set up Redis connection
    '''
    url = urlparse(args.url)
    conn = redis.Redis(host=url.hostname, port=url.port)
    if not conn.ping():
        raise Exception('Redis unavailable')

    '''
    Load the RedisAI model
    '''
    print('Loading model...', end='')
    with open('./tiny-yolo-voc.pb', 'rb') as f:
        model = f.read()
        res = conn.execute_command('AI.MODELSET', 'yolo:model', 'TF',
                                   args.device, 'INPUTS', 'input', 'OUTPUTS', 'output', 'BLOB', model)
        print(res)

    '''
    Load the PyTorch post processing boxes script
    '''
    print('Loading script...', end='')
    with open('./ai-yolo-script.py', 'rb') as f:
        script = f.read()
        res = conn.execute_command(
            'AI.SCRIPTSET', 'yolo:script', args.device, 'SOURCE', script)
        print(res)
