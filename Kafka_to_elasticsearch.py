from kafka import KafkaConsumer
from elasticsearch import Elasticsearch
from prefect import task, Flow
from prefect.schedules import IntervalSchedule
from datetime import timedelta
import json
from hashlib import sha256
import os

SERVER_HOST = os.getenv('SERVER_HOST')
KAFKA_TOPIC = 'news1'

@task
def consume_kafka_data():
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=[f'{SERVER_HOST}:19094'],
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    data = []
    for message in consumer:
        record = message.value
        record_id = sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
        record['_id'] = record_id
        data.append(record)
    return data

@task
def send_to_elasticsearch(data):
    es = Elasticsearch([{'host': SERVER_HOST, 'port': 19200}])
    for record in data:
        if not es.exists(index="news1", id=record['_id']):
            es.index(index="news1", id=record['_id'], body=record)

schedule = IntervalSchedule(interval=timedelta(minutes=1))

with Flow("Kafka to Elasticsearch", schedule=schedule) as flow:
    data = consume_kafka_data()
    send_to_elasticsearch(data)

if __name__ == "__main__":
    flow.run()
