FROM redislabs/redisai:latest-cpu-x64-bionic as redisai
FROM redislabs/redistimeseries:latest as redistimeseries
FROM redislabs/redisgears:latest

ENV LD_LIBRARY_PATH=/usr/lib/redis/modules

ARG MODULES=/var/opt/redislabs/lib/modules
ARG RG=${MODULES}/redisgears.so
ARG REDIS="redis-server --loadmodule ${RG} PythonHomeDir /opt/redislabs/lib/modules/python3"

ARG DEPS="python3-opencv"
ARG REQ="numpy \
    Pillow \
    opencv-python"

# Set up a build environment
WORKDIR /data
RUN set -ex;\
    deps="$DEPS";\
    apt-get update;\
    apt-get install -y --no-install-recommends $deps;

# Copy RedisTimeSeries
COPY --from=redistimeseries ${LD_LIBRARY_PATH}/*.so ${LD_LIBRARY_PATH}/

# Copy RedisAI
COPY --from=redisai ${LD_LIBRARY_PATH}/redisai.so ${LD_LIBRARY_PATH}/
COPY --from=redisai ${LD_LIBRARY_PATH}/backends ${LD_LIBRARY_PATH}/backends

# Start Redis and install Deps
RUN nohup bash -c "${REDIS}&" && sleep 4 && redis-cli RG.PYEXECUTE "GearsBuilder().run()" REQUIREMENTS $REQ \
    && redis-cli save

ENTRYPOINT ["redis-server"]
CMD ["--loadmodule", "/usr/lib/redis/modules/redistimeseries.so", \
    "--loadmodule", "/usr/lib/redis/modules/redisai.so", \
    "--loadmodule", "/var/opt/redislabs/lib/modules/redisgears.so", \
    "PythonHomeDir", "/opt/redislabs/lib/modules/python3"]