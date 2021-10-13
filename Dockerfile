FROM redislabs/redisai:edge-cpu-bionic as redisai
FROM redislabs/redistimeseries:edge as redistimeseries
FROM redislabs/redisgears:edge

ENV LD_LIBRARY_PATH=/usr/lib/redis/modules

ARG MODULES=/var/opt/redislabs/lib/modules
ARG RG=${MODULES}/redisgears.so
ARG REDIS="redis-server --loadmodule ${RG} Plugin /var/opt/redislabs/modules/rg/plugin/gears_python.so"

ARG REQ="numpy \
    Pillow \
    opencv-python-headless"

# Set up a build environment
WORKDIR /data
RUN set -ex;\
    apt-get update;

# Copy RedisTimeSeries
COPY --from=redistimeseries ${LD_LIBRARY_PATH}/*.so ${LD_LIBRARY_PATH}/

# Copy RedisAI
COPY --from=redisai ${LD_LIBRARY_PATH}/redisai.so ${LD_LIBRARY_PATH}/
COPY --from=redisai ${LD_LIBRARY_PATH}/backends ${LD_LIBRARY_PATH}/backends

# Start Redis and install Deps
RUN nohup bash -c "${REDIS}&" && sleep 4 && redis-cli RG.PYEXECUTE "import cv2; GearsBuilder().run()" REQUIREMENTS $REQ \
    && redis-cli save

ENTRYPOINT ["redis-server"]
CMD ["--loadmodule", "/usr/lib/redis/modules/redistimeseries.so", \
    "--loadmodule", "/usr/lib/redis/modules/redisai.so", \
    "--loadmodule", "/var/opt/redislabs/lib/modules/redisgears.so", \
    "Plugin", "/var/opt/redislabs/modules/rg/plugin/gears_python.so"]
