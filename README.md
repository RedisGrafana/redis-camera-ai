# Analyzing camera feed using RedisAI, OpenCV and Grafana

![Camera AI](https://raw.githubusercontent.com/RedisGrafana/redis-camera-ai/main/images/camera-ai.png)

[![Grafana 7](https://img.shields.io/badge/Grafana-7-orange)](https://www.grafana.com)
[![Redis Data Source](https://img.shields.io/badge/dynamic/json?color=blue&label=Redis%20Data%20Source&query=%24.version&url=https%3A%2F%2Fgrafana.com%2Fapi%2Fplugins%2Fredis-datasource)](https://grafana.com/grafana/plugins/redis-datasource)
[![Redis Application plug-in](https://img.shields.io/badge/dynamic/json?color=blue&label=Redis%20Application%20plug-in&query=%24.version&url=https%3A%2F%2Fgrafana.com%2Fapi%2Fplugins%2Fredis-app)](https://grafana.com/grafana/plugins/redis-app)
[![Docker](https://github.com/RedisGrafana/redis-camera-ai/actions/workflows/docker.yml/badge.svg)](https://github.com/RedisGrafana/redis-camera-ai/actions/workflows/docker.yml)

## Introduction

This project demonstrates how to analyze camera feed stored as [Redis Streams](https://redis.io/topics/streams-intro) using serverless engine [RedisGears](https://oss.redislabs.com/redisgears/), [RedisAI](https://redisai.io/) and display analyzed frames with metrics in Grafana.

![Redis-Camera-AI](https://raw.githubusercontent.com/RedisGrafana/redis-camera-ai/main/images/redis-camera-ai.png)

## Requirements

- [Docker](https://docker.com) to start Redis and Grafana.
- [Python](https://www.python.org/) to run scripts.

## Redis with OpenCV Docker image

This project provides Docker image with Redis, RedisTimeSeries, RedisGears, RedisAI and installed [OpenCV for Python](https://docs.opencv.org/master/d6/d00/tutorial_py_root.html) library.

```bash
docker run -p 6379:6379 --name=redis-opencv ghcr.io/redisgrafana/redis-opencv:latest
```

## OpenCV requirements

Check that OpenCV with dependencies downloaded, installed and registered in the RedisGears requirements:

```bash
cluster.remote:6379> rg.pydumpreqs
1)  1) "GearReqVersion"
    2) (integer) 1
    3) "Name"
    4) "Pillow"
    5) "IsDownloaded"
    6) "yes"
    7) "IsInstalled"
    8) "yes"
    9) "CompiledOs"
   10) "linux-buster-x64"
   11) "Wheels"
   12) 1) "Pillow-8.2.0-cp37-cp37m-manylinux1_x86_64.whl"
2)  1) "GearReqVersion"
    2) (integer) 1
    3) "Name"
    4) "opencv-python"
    5) "IsDownloaded"
    6) "yes"
    7) "IsInstalled"
    8) "yes"
    9) "CompiledOs"
   10) "linux-buster-x64"
   11) "Wheels"
   12) 1) "numpy-1.20.3-cp37-cp37m-manylinux_2_12_x86_64.manylinux2010_x86_64.whl"
       2) "opencv_python-4.5.2.52-cp37-cp37m-manylinux2014_x86_64.whl"
3)  1) "GearReqVersion"
    2) (integer) 1
    3) "Name"
    4) "numpy"
    5) "IsDownloaded"
    6) "yes"
    7) "IsInstalled"
    8) "yes"
    9) "CompiledOs"
   10) "linux-buster-x64"
   11) "Wheels"
   12) 1) "numpy-1.20.3-cp37-cp37m-manylinux_2_12_x86_64.manylinux2010_x86_64.whl"
```

## Import AI model and script

To load AI model and [PyTorch](https://pytorch.org/) script to the Redis database run:

```bash
cd ai/
cat tiny-yolo-voc.pb | redis-cli -h redis -x AI.MODELSET yolo:model TF CPU INPUTS input OUTPUTS output BLOB
cat ai-yolo-script.py| redis-cli -h redis -x AI.SCRIPTSET yolo:script CPU SOURCE
```

## Start Grafana

Grafana can be started using Docker Compose or installed locally with [Redis plug-ins for Grafana](https://redisgrafana.github.io) and [Volkov Labs Image panel](https://github.com/VolkovLabs/grafana-image-panel).

```bash
docker-compose pull
docker-compose up
```

When starting using Docker Compose, dashboard and plug-ins will be auto-provisioned and available in Grafana.

## Register RedisGears script

Select `Camera Processing` dashboard and copy-paste `gears-yolo.py` script to RedisGears Script editor panel. Click on the `Run script` button and you should see registered script `StreamReader` on the Registrations panel.

![RedisGears Script Editor](https://raw.githubusercontent.com/RedisGrafana/redis-camera-ai/main/images/gears-script-editor.png)

## Start Camera

Copy script `edge-camera.py` and `requirements.txt` to IoT or any device with camera. Run script by specifying Redis URL, number of frames per second and rotate camera if required.

```bash
cd camera/
pip3 install -r requirements.txt
python3 edge-camera.py -u redis://redis:6379 --fps 6 --rotate-90-clockwise true
```

You should see output with Stream's Id and size of the jpeg file.

```bash
# python3 camera.py -u redis://red:6379 --fps 6 --rotate-90-clockwise true
Connected to Redis: ParseResult(scheme='redis', netloc='redis:6379', path='', params='', query='', fragment='')
id: b'1622145939609-0', size: 5479
id: b'1622145939769-0', size: 10006
id: b'1622145939928-0', size: 6709
id: b'1622145940100-0', size: 6037
id: b'1622145940266-0', size: 6468
id: b'1622145940435-0', size: 11607
id: b'1622145940597-0', size: 5577
id: b'1622145940768-0', size: 6041
id: b'1622145940926-0', size: 5570
id: b'1622145941098-0', size: 5916
```

## Learn more

- Redis plug-ins for Grafana [Documentation](https://redisgrafana.github.io/)
- [My Other Stack Is RedisEdge](https://redislabs.com/blog/my-other-stack-is-redisedge/)
- [RedisEdge Real-time Video Analytics](https://github.com/RedisGears/EdgeRealtimeVideoAnalytics)

## Contributing

- Fork the repository.
- Find an issue to work on and submit a pull request.
- Could not find an issue? Look for documentation, bugs, typos, and missing features.

## License

- Apache License Version 2.0, see [LICENSE](https://github.com/RedisGrafana/redis-camera-ai/blob/main/LICENSE).
