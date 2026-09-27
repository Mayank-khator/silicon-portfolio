"""At-least-once outbox publisher using leases and RabbitMQ confirms.

SQL mutations create outbox rows in the same transaction. A crash between broker
confirmation and database acknowledgement can duplicate delivery. Consumers must
deduplicate the durable event UUID (`message_id`), not assume exactly-once.
"""
import asyncio
import json
import logging
import os
import socket
from uuid import uuid4

import aio_pika
import httpx

logger = logging.getLogger('silicon.outbox')


class OutboxGateway:
    def __init__(self, client: httpx.AsyncClient, worker_id: str):
        self.client = client
        self.worker_id = worker_id

    async def rpc(self, name, body):
        response = await self.client.post('/rest/v1/rpc/' + name, json=body)
        response.raise_for_status()
        return response.json()

    async def claim(self):
        return await self.rpc('claim_outbox_events', {'p_limit': 5, 'p_worker_id': self.worker_id})

    async def acknowledge(self, event_id):
        acknowledged = await self.rpc('acknowledge_outbox_event', {'p_id': event_id, 'p_worker_id': self.worker_id})
        if acknowledged is not True:
            raise RuntimeError('Outbox lease was lost before acknowledgement')

    async def fail(self, event_id, error):
        await self.rpc('fail_outbox_event', {'p_id': event_id, 'p_worker_id': self.worker_id, 'p_error': error[:100]})


async def deliver_batch(gateway, publish) -> int:
    events = await gateway.claim()

    async def deliver(event):
        try:
            await publish(event)
            await gateway.acknowledge(event['id'])
            return 1
        except Exception as exc:
            # Do not persist exception strings: URLs can contain credentials.
            error_type = type(exc).__name__
            try:
                await gateway.fail(event['id'], error_type)
            except Exception as fail_exc:
                logger.warning('Could not release event lease: %s', type(fail_exc).__name__)
            logger.warning('Event publish deferred: %s', error_type)
            return 0

    # Five events fit within the 60-second SQL lease; broker confirmation times
    # out after 10 seconds and database requests after 15 seconds.
    return sum(await asyncio.gather(*(deliver(event) for event in events)))


async def run():
    url = os.environ.get('SUPABASE_URL', '').rstrip('/')
    service_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
    rabbit_url = os.environ.get('RABBITMQ_URL', '')
    if not all((url, service_key, rabbit_url)):
        raise RuntimeError('Worker requires SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY and RABBITMQ_URL')
    worker_id = socket.gethostname() + '-' + str(uuid4())
    connection = await aio_pika.connect_robust(rabbit_url, timeout=15)
    async with connection:
        channel = await connection.channel(publisher_confirms=True, on_return_raises=True)
        exchange = await channel.declare_exchange('silicon.events', aio_pika.ExchangeType.TOPIC, durable=True)
        queue = await channel.declare_queue('silicon.events.audit', durable=True)
        await queue.bind(exchange, routing_key='#')

        async def publish(event):
            message = aio_pika.Message(
                body=json.dumps(event, sort_keys=True).encode('utf-8'),
                content_type='application/json', message_id=str(event['id']),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            )
            await exchange.publish(message, routing_key=event['event_type'], mandatory=True, timeout=10)

        async with httpx.AsyncClient(base_url=url, timeout=15, headers={
            'apikey': service_key, 'Authorization': f'Bearer {service_key}',
        }) as client:
            gateway = OutboxGateway(client, worker_id)
            while True:
                try:
                    delivered = await deliver_batch(gateway, publish)
                    if not delivered:
                        await asyncio.sleep(2)
                except Exception as exc:
                    logger.warning('Outbox poll deferred: %s', type(exc).__name__)
                    await asyncio.sleep(5)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    asyncio.run(run())
