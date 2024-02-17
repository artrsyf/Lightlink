import websocket
from websocket._core import WebSocket
import json
import asyncio
import websockets
import threading
import time
from time import time
from pyforkurento import client

class KurentoBaseClient(object):
    def __init__(self, kurento_url: str):
        self.kurento_url = kurento_url
        self.current_operation_num = 1
        self.replies = {}
        self.kurento_conn = websocket.WebSocket()
        self.kurento_conn.connect(kurento_url)

        self.server_replies_thread = threading.Thread(target=self.listen_to_replies)
        self.server_replies_thread.daemon = True
        self.server_replies_thread.start()
    
    async def reconnect(self):
        if not self.kurento_conn.connected:
            try:
                await self.kurento_conn.connect(self.kurento_url)
            except Exception as ex:
                return ex
    
    async def disconnect(self):
        if self.kurento_conn.connected:
            await self.kurento_conn.close()
        
    def process_reply(self, server_reply_json):
        server_reply = json.loads(server_reply_json)
        id = server_reply["id"]
        jsonrpc = server_reply["jsonrpc"]
        if "error" in server_reply:
            status = "error"
            payload = server_reply["error"]
        elif "result" in server_reply:
            status = "success"
            payload = server_reply["result"]
        else:
            raise Exception(f"Unrecognized repy status: {server_reply}")
        return {"status": status, "reply": payload, "id": id, "jsonrpc": jsonrpc}
        
    def listen_to_replies(self):
        while self.kurento_conn.connected:
            try:
                server_reply_json = self.kurento_conn.recv()
                processed_reply = self.process_reply(server_reply_json)
                self.replies[int(processed_reply["id"])] = processed_reply
            except Exception as ex:
                return ex
            
    def prepare_payload(self, operation_number: int, payload_method: str, payload_params: dict):
        payload = {
            "jsonrpc": "2.0",
            "id": operation_number,
            "method": payload_method,
            "params": payload_params
        }
        return json.dumps(payload)

    async def send_payload(self, payload_method: str, payload_params: dict = {}):
        try:
            op_id = self.current_operation_num
            self.current_operation_num += 1
            prepared_payload = self.prepare_payload(op_id, payload_method, payload_params)
            await self.kurento_conn.send(prepared_payload)

        except Exception as ex:
            return ex
        
class ReeadyKClient(KurentoBaseClient):
    def __init__(self, kurento_url: str):
        super().__init__(kurento_url)

    async def _send_payload(self, payload_method: str, payload_params: dict = {}):
        return await super().send_payload(payload_method, payload_params)
    
    async def _reconnect(self):
        return await super().reconnect()
    
    def _prepare_payload(self, operation_number: int, payload_method: str, payload_params: dict):
        return super().prepare_payload(operation_number, payload_method, payload_params)
    
    def _process_reply(self, server_reply_json):
        return super().process_reply(server_reply_json)
    
    async def disconnect(self):
        return await super().disconnect()
        
    def _listen_to_replies(self):
        return super().listen_to_replies()
    
    async def _get_answer(self, op_id: int):
        while True:
            if op_id in self.replies:
                return self.replies[op_id]

    async def make_transaction(self, payload_method: str, payload_params: dict = {}):
        operation_id = self.current_operation_num
        await self._send_payload(payload_method, payload_params)
        return await self._get_answer(operation_id)
        
class PureKurentoApi():
    operation_number = 1

    @classmethod
    def customProcessOffer(cls, ep_id, session_id, session_desc_offer):
        kurento_conn = websocket.WebSocket()
        kurento_conn.connect("ws://lightlink_kurento:8888/kurento")
        payload = {
            "jsonrpc": "2.0",
            "id": cls.operation_number,
            "method": "invoke",
            "params": {
                "object": f"{ep_id}",
                "operation": "processOffer",
                "operationParams":{
                    "offer": session_desc_offer
                },
                "sessionId": f"{session_id}"
            }
        }
        kurento_conn.send(json.dumps(payload))
        return kurento_conn.recv()
    
    @classmethod
    def printLocalDescr(cls, ep_id, session_id):
        kurento_conn = websocket.WebSocket()
        kurento_conn.connect("ws://lightlink_kurento:8888/kurento")
        payload = {
            "jsonrpc": "2.0",
            "id": cls.operation_number,
            "method": "invoke",
            "params": {
                "object": f"{ep_id}",
                "operation": "getRemoteSessionDescriptor",
                "sessionId": f"{session_id}"
            }
        }
        kurento_conn.send(json.dumps(payload))
        print(kurento_conn.recv())

class AsyncKurentoBaseClient(object):
    @classmethod
    async def create(cls, kurento_url: str):
        self = cls(kurento_url)
        return self
    
    def __init__(self, kurento_url: str):
        self.kurento_url = kurento_url
        self.current_operation_num = 1
        self.replies = {}
    
    async def make_transaction(self, payload_method: str, payload_params: dict = {}, continious_transaction: bool = False):
        if continious_transaction:
            ws = await websockets.connect(self.kurento_url)
            op_id = self.current_operation_num
            self.current_operation_num += 1
            prepared_payload = self.prepare_payload(op_id, payload_method, payload_params)
            await ws.send(prepared_payload)
            server_response_json = await ws.recv()
            processed_server_reply = self.process_reply(server_response_json)
            return (ws, processed_server_reply)
        else:
            async with websockets.connect(self.kurento_url) as ws:
                op_id = self.current_operation_num
                self.current_operation_num += 1
                prepared_payload = self.prepare_payload(op_id, payload_method, payload_params)
                await ws.send(prepared_payload)
                server_response_json = await ws.recv()
                processed_server_reply = self.process_reply(server_response_json)
                return processed_server_reply
    
    def process_reply(self, server_reply_json: str):
        server_reply = json.loads(server_reply_json)
        id = server_reply["id"]
        jsonrpc = server_reply["jsonrpc"]
        if "error" in server_reply:
            status = "error"
            payload = server_reply["error"]
        elif "result" in server_reply:
            status = "success"
            payload = server_reply["result"]
        else:
            raise Exception(f"Unrecognized repy status: {server_reply}")
        return {"status": status, "value": payload, "id": id, "jsonrpc": jsonrpc}

    def prepare_payload(self, operation_number: int, payload_method: str, payload_params: dict):
        payload = {
            "jsonrpc": "2.0",
            "id": operation_number,
            "method": payload_method,
            "params": payload_params
        }
        return json.dumps(payload)

class AsyncKurentoClient(AsyncKurentoBaseClient):
    def __init__(self, kurento_url: str) -> None:
        super().__init__(kurento_url)
    
    async def _make_transaction(self, payload_method: str, payload_params: dict = {}, continious_transaction: bool = False):
        return await super().make_transaction(payload_method, payload_params, continious_transaction)
    
    def _process_reply(self, server_reply_json: str):
        return super().process_reply(server_reply_json)

    def _prepare_payload(self, operation_number: int, payload_method: str, payload_params: dict):
        return super().prepare_payload(operation_number, payload_method, payload_params)
    
    async def release_element(self, element_id, session_id):
        payload_method = "release"
        payload_params = {
            "object": element_id,
            "sessionId": session_id
        }

        return await self._make_transaction(payload_method, payload_params)
    
    async def process_offer(self, endpoint_id, session_id, session_desc_offer):
        payload_method = "invoke"
        payload_params = {
            "object": endpoint_id,
            "operation": "processOffer",
            "operationParams": {
                "offer": session_desc_offer
            },
            "sessionId": session_id
        }

        return await self._make_transaction(payload_method, payload_params)
    
    async def _invoke(self, payload_params):
        return await self._make_transaction("invoke", payload_params)
    
    async def _subscribe(self, payload_params): 
        response = await self._make_transaction("subscribe", payload_params, True)
        return response
    
    async def _create_element(self, payload_params):
        response = await self._make_transaction("create", payload_params)
        return response
    
    async def _on_event(self, _event, callback, ws_connection):
        print("ON EVENT LISTENING")
        while True:
            try:
                incoming_event_response = await ws_connection.recv()
                print(incoming_event_response)
                await callback(incoming_event_response)
            except websockets.exceptions.ConnectionClosed:
                print("conenction is closed")
                await asyncio.sleep(2) # timeout before reconnect
            except Exception as ex:
                print(ex)

    async def create_media_pipeline(self):
        create_params = {
            "type": "MediaPipeline",
            "constructorParams": {},
            "properties": {}
        }

        response = await self._create_element(create_params)
        pipeline_id = response["value"]["value"]
        session_id = response["value"]["sessionId"]

        pipeline = AsyncMediaPipeLine(session_id, pipeline_id, self)
        return pipeline



    async def add_ice_candidate(self, endpoint_id, session_id, candidate):
        payload_method = "invoke"
        payload_params = {
            "object": endpoint_id,
            "operation": "addIceCandidate",
            "operationParams": {
                "candidate": candidate
            },
            "sessionId": session_id
        }

        return await self._make_transaction(payload_method, payload_params)
    
    async def get_remote_session_descriptor(self, endpoint_id, session_id):
        payload_method = "invoke"
        payload_params = {
            "object": endpoint_id,
            "operation": "getRemoteSessionDescriptor",
            "sessionId": session_id
        }

        return await self._make_transaction(payload_method, payload_params)

class AsyncMediaElement(object):
    @classmethod
    async def create(cls, sesison_id, element_id, async_kurento_client):
        self = cls(sesison_id, element_id, async_kurento_client)
        return self

    def __init__(self, sesison_id, element_id, async_kurento_client) -> None:
        self.session_id = sesison_id
        self.element_id = element_id
        self.async_kurento_client = async_kurento_client

    async def _connect(self, external_sink=None):
        sink_element_id = external_sink.element_id if external_sink is not None else self.element_id

        params = {
            "object" :self.element_id,
            "operation": "connect",
            "operationParams":{
                "sink": sink_element_id
            },
            "sessionId": self.session_id
        }

        response = await self.async_kurento_client._invoke(params)
        return response
    
    async def _subscribe(self, event):
        params = {
            "type": event,
            "object": self.element_id,
            "sessionId": self.session_id
        } 

        response = await self.async_kurento_client._subscribe(params)
        return response
    
    async def _on_event(self, event, callback, ws_connection):
        await self.async_kurento_client._on_event(event, callback, ws_connection)

    
    async def _add_event_listener(self, event, callback):
        expected = ["MediaFlowIn", "MediaFlowOut", "EndOfStream", "ElementConnected", "ElementDisconnected", "Error"]

        if event not in expected:
            raise Exception("Uknown event requested")
        elif not callable(callback):
            raise RuntimeError("Callback has to be callable e.g. a function")
        else:
            ws_connection, response = await self._subscribe(event)
            asyncio.create_task(super()._on_event(event, callback, ws_connection))

class AsyncEndPoint(AsyncMediaElement):
    def __init__(self, sesison_id, endpoint_id, async_kurento_client) -> None:
        super().__init__(sesison_id, endpoint_id, async_kurento_client)

    async def connect(self, external_sink=None):
        return await super()._connect(external_sink)

class AsyncWebRtcEndpoint(AsyncEndPoint):
    def __init__(self, sesison_id, endpoint_id, async_kurento_client) -> None:
        super().__init__(sesison_id, endpoint_id, async_kurento_client)

    async def gather_ice_candidates(self):
        params = {
            "object": self.element_id,
            "operation": "gatherCandidates",
            "sessionId": self.session_id
        }

        response = await self.async_kurento_client._invoke(params)
        print("GATHER RESP: ", response)

    async def add_event_listener(self, event, callback):
        expected = ["OnIceCandidate", "OnIceGatheringDone"]

        if event not in expected:
            await super()._add_event_listener(event, callback)
        else:   
            if not callable(callback):
                raise RuntimeError("Callback has to be callable e.g. a function")
            else:
                ws_connection, response = await super()._subscribe(event)
                asyncio.create_task(super()._on_event(event, callback, ws_connection))

class AsyncMediaPipeLine(object):
    def __init__(self, session_id, pipeline_id, async_kurento_client) -> None:
        self.session_id = session_id
        self.pipeline_id = pipeline_id
        self.async_kurento_client = async_kurento_client

        self.create_params = {
            "type": "",
            "constructorParams": {
                "mediaPipeline": self.pipeline_id
            },
            "sessionId": self.session_id
        }

    async def _create_element(self): # for future
        pass
    
    async def add_web_rtc_endpoint(self):
        params = self.create_params.copy()
        params["type"] = "WebRtcEndpoint"
        response = await self.async_kurento_client._create_element(params)
        print(response)
        endpoint_id = response["value"]["value"]
        session_id = response["value"]["sessionId"]

        return AsyncWebRtcEndpoint(session_id, endpoint_id, self.async_kurento_client)

async def callback_foo():
    print("Got ice")

async def main():
    conn = await AsyncKurentoClient.create("ws://localhost:8888/kurento")
    pipeline = await conn.create_media_pipeline()
    endpoint = await pipeline.add_web_rtc_endpoint()
    offer = "v=0\r\no=- 1113439286307267998 3 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\na=extmap-allow-mixed\r\na=msid-semantic: WMS\r\n"
    resp = await conn.process_offer(endpoint.element_id, endpoint.session_id, offer)
    print(resp)
    await endpoint.add_event_listener("OnIceCandidate", callback_foo)
    await endpoint.gather_ice_candidates()

if __name__ == "__main__":
    asyncio.run(main())