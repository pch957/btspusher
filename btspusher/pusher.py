# -*- coding: utf-8 -*-
import asyncio
from autobahn.asyncio.wamp import ApplicationSession
from autobahn.wamp import auth
from btspusher.wamp import ApplicationRunner


class PusherComponent(ApplicationSession):
    future = None  # a future from asyncio
    instance = None
    login_info = None
    cb = None
    co = None

    @staticmethod
    def login(login_info):
        PusherComponent.login_info = login_info

    @asyncio.coroutine
    def onJoin(self, details):
        print("join")
        PusherComponent.instance = self
        if self.future:
            self.future.set_result(1)
            self.future = None
        if self.cb:
            self.cb(self)
        if self.co:
            yield from self.co(self)

    def onConnect(self):
        print("connected")
        if self.login_info:
            self.join(self.config.realm, [u"wampcra"], self.login_info["user"])
        else:
            self.join(self.config.realm)

    def onChallenge(self, challenge):
        key = self.login_info["password"].encode('utf8')
        signature = auth.compute_wcs(
            key, challenge.extra['challenge'].encode('utf8'))
        return signature.decode('ascii')

    def onLeave(self, details):
        print("session left")

    def onDisconnect(self):
        PusherComponent.instance = None
        print("lost connect")


class Pusher(object):
    def __init__(
            self, loop, login_info=None, co=None, cb=None):
        url = u"wss://pusher.btsbots.com/ws"
        realm = u"realm1"
        try:
            if login_info:
                PusherComponent.login(login_info)
            PusherComponent.future = asyncio.Future()
            PusherComponent.co = co
            PusherComponent.cb = cb
            runner = ApplicationRunner(url, realm)
            runner.run(PusherComponent)
            loop.run_until_complete(
                asyncio.wait_for(PusherComponent.future, 10))
        except Exception:
            print("can't connect to pusher.btsbots.com")

    def publish(self, *args, **kwargs):
        kwargs["__t"] = args[0]
        if PusherComponent.instance:
            PusherComponent.instance.publish(*args, **kwargs)

    def sync_subscribe(self, *args, **kwargs):
        if PusherComponent.instance:
            asyncio.wait(PusherComponent.instance.subscribe(*args, **kwargs))

    @asyncio.coroutine
    def subscribe(self, *args, **kwargs):
        if PusherComponent.instance:
            yield from PusherComponent.instance.subscribe(*args, **kwargs)

    def sync_call(self, *args, **kwargs):
        if PusherComponent.instance:
            asyncio.wait(PusherComponent.instance.call(*args, **kwargs))

    @asyncio.coroutine
    def call(self, *args, **kwargs):
        if PusherComponent.instance:
            yield from PusherComponent.instance.call(*args, **kwargs)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    bts_pusher = Pusher(loop)

    def on_event(i):
        print("Got event: {}".format(i))

    # bts_pusher.sync_subscribe(on_event, "public.test")
    bts_pusher.publish("public.test", "hello", a="bb")

    loop.run_forever()
    loop.close()
