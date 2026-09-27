import pytest

from services.worker.outbox import deliver_batch


class Gateway:
    def __init__(self):
        self.acknowledged = []
        self.failed = []

    async def claim(self):
        return [{'id': 'event-1', 'event_type': 'projects.updated', 'payload': {'id': 'p1'}, 'attempts': 1}]

    async def acknowledge(self, event_id):
        self.acknowledged.append(event_id)

    async def fail(self, event_id, error):
        self.failed.append((event_id, error))


@pytest.mark.asyncio
async def test_outbox_acknowledges_only_after_publish_confirmation():
    gateway = Gateway()
    events = []
    async def publish(event):
        assert gateway.acknowledged == []
        events.append(event)
    delivered = await deliver_batch(gateway, publish)
    assert delivered == 1
    assert events[0]['id'] == 'event-1'
    assert gateway.acknowledged == ['event-1']
    assert gateway.failed == []


@pytest.mark.asyncio
async def test_outbox_publish_failure_leaves_event_retryable_and_unacknowledged():
    gateway = Gateway()
    async def publish(event):
        raise ConnectionError('amqp://user:password@private-host')
    assert await deliver_batch(gateway, publish) == 0
    assert gateway.acknowledged == []
    assert gateway.failed == [('event-1', 'ConnectionError')]
