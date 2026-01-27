#!/bin/bash

cd "$(dirname "$0")"

if [ ! -f .pid ]; then
    echo "服务未运行"
    exit 0
fi

pid=$(cat .pid)

if ps -p $pid > /dev/null 2>&1; then
    kill $pid
    rm -f .pid
    echo "服务已停止 (PID: $pid)"
else
    rm -f .pid
    echo "服务未运行"
fi
