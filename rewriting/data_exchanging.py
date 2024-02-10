import websocket
import json

kurento_conn = websocket.WebSocket()
kurento_conn.connect("ws://localhost:8888/kurento")
payload = {
  "jsonrpc": "2.0",
  "id": 4,
  "method": "invoke",
  "params": {
    "object": "f1e58e56-4052-4550-adde-bd1443297476_kurento.MediaPipeline/cc5fe12f-e1c6-41bd-a7e5-d5c561f9d973_kurento.WebRtcEndpoint",
    "operation": "getRemoteSessionDescriptor",
    "sessionId": "3fb0d9ac-f237-45e8-b585-3b68ee87b891"
  }
}

kurento_conn.send(json.dumps(payload))

print(kurento_conn.recv())