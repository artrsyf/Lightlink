import websocket
from websocket._core import WebSocket
import json
import asyncio
import websockets
import threading
import time
from time import time
from pyforkurento import client

class AsyncKurentoBaseClient(object):
    @classmethod
    async def create(cls, kurento_url: str):
        self = cls(kurento_url)
        return self
    
    def __init__(self, kurento_url: str):
        self.kurento_url = kurento_url
        self.current_operation_num = 1
        self.replies = {}
    
    async def make_transaction(self, payload_method: str, payload_params: dict = {}):
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
    
    async def _make_transaction(self, payload_method: str, payload_params: dict = {}):
        return await super().make_transaction(payload_method, payload_params)
    
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

async def main():
    conn = await AsyncKurentoClient.create("ws://localhost:8888/kurento")
    resp = await conn._make_transaction("ping", {})
    print(resp)

if __name__ == "__main__":
    asyncio.run(main())