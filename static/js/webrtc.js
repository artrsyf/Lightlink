const ICE_CONF = {'iceServers': [{'urls': 'stun:stun.l.google.com:19302'}]}

const WEBRTC_SOCKET = new WebSocket(
    "ws://"
    + window.location.host
    + '/ws/service/webrtc/'
    + '1' // for test
    + '/'
)

perrConnection = async (USER_DATA) => {
    const PEER_CONNECTION = new RTCPeerConnection(ICE_CONF)

    WEBRTC_SOCKET.onmessage = async (e) => {
        const DATA = JSON.parse(e.data)

        if (DATA.type == "RTCPeerConnectionAnswer")
        {
            const ANSWER = new RTCSessionDescription(DATA.body)
            await PEER_CONNECTION.setRemoteDescription(ANSWER)
        }
        else if (DATA.type == "RTCPeerConnectionOffer")
        {
            PEER_CONNECTION.setRemoteDescription(new RTCSessionDescription(DATA.body))
            const ANSWER = await PEER_CONNECTION.createAnswer();
            await PEER_CONNECTION.setLocalDescription(ANSWER);
            if (WEBRTC_SOCKET.readyState == 1) // open ws connection
            {
                WEBRTC_SOCKET.send(JSON.stringify({
                    type: "webrtc.peer_connection",
                    head: "RTCPeerConnectionAnswer",
                    sender_user_id: USER_DATA.user_id,
                    body: ANSWER
                }))
            }
        }
    }

    const OFFER = await PEER_CONNECTION.createOffer()
    await PEER_CONNECTION.setLocalDescription(OFFER)

    if (WEBRTC_SOCKET.readyState == 1) // open ws connection
    {
        WEBRTC_SOCKET.send(JSON.stringify({
            type: "webrtc.peer_connection",
            head: "RTCPeerConnectionOffer",
            sender_user_id: USER_DATA.user_id,
            body: OFFER
        }))
    }
}

fetch('/vw/get_user_data')
    .then(response => response.json())
    .then((data) => {
        perrConnection(data)
    })