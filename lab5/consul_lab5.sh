#!/bin/sh

sleep 5

curl --request PUT \
     --data '{
  "hosts":["hazelcast1:5701","hazelcast2:5701","hazelcast3:5701"],
  "cluster_name":"dev"
}' \
     http://consul:8500/v1/kv/hazelcast/config

curl --request PUT \
     --data '{
  "bootstrap_servers":["kafka1:9092","kafka2:9093","kafka3:9094"],
  "topic":"messages"
}' \
     http://consul:8500/v1/kv/kafka/config
