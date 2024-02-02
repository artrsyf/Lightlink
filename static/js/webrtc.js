const ICE_CONF = {'iceServers': [{'urls': 'stun:stun.l.google.com:19302'}]}
const VIDEO_CONF = {video: true, audio: false}

const WEBRTC_SOCKET = new WebSocket(
    "ws://"
    + window.location.host
    + '/ws/service/webrtc/'
    + '1' // for test
    + '/'
)
var PEER_CONNECTION = null

class AdaptiveWebSocket{
    constructor(ws_url){
        this.url = ws_url
        this.web_socket = new WebSocket(ws_url)
    }

    get readyState() {
        return this.web_socket.readyState;
    }

    open()
    {
        if (this.readyState == 1 || this.readyState == 2) return

        delete this.web_socket
        this.web_socket = new WebSocket(this.url)
    }

    onopen(onopen_func)
    {
        this.web_socket.onopen = onopen_func
    }

    onmessage(onmessage_func)
    {
        this.web_socket.onmessage = onmessage_func
    }

    onclose(onclose_func)
    {
        this.web_socket.onclose = onclose_func
    }

    close()
    {
        this.web_socket.close()
    }

    send(data){
        switch(ws.readyState)
        {
            case 1:
                ws.send(data)
                break

            case 2:
                ws.onopen = () => {
                    ws.send(data)
                }
                break
            
            case 3:
                console.error("Cant send data, WebSocket instance is closed")
                break

            default:
                console.error("Unrecognized WebSocket state")
        }
    }
}

class P2pConnection{
    constructor(channel_url, user_id, ice_conf)
    {
        this.webrtc_adaptive_web_socket = new AdaptiveWebSocket(channel_url)
        this.webrtc_adaptive_web_socket.onmessage = this.#handleSignal
        this.ICE_CONF = ice_conf
        this.user_id = user_id

        this.peer_connection = new RTCPeerConnection(ICE_CONF)
        this.peer_connection.addEventListener("track", this.#handleNewTrack)
        this.peer_connection.onicecandidate = this.#handleIcaCandidate
        this.peer_connection.addEventListener("connectionstatechange", this.#handleConnectionStateChanged)

        this.localStream = null
    }

    makeConnection = async () => {
        localStream = await navigator.mediaDevices.getUserMedia({ video: false, audio: true });
        localStream.getTracks().forEach(track => {
            this.peer_connection.addTrack(track, localStream);
        });
    }

    #handleConnectionStateChanged = (event) => {
        if (this.peer_connection.connectionState === "connected") {
            console.log("Peer connection successfully established")
        }
    }

    #handleSignal = async (event) => {
        const DATA = JSON.parse(event.data)
        switch(DATA.type){
            case "RTCPeerConnectionAnswer":
                const INCOMING_ANSWER = new RTCSessionDescription(DATA.body)
                await this.peer_connection.setRemoteDescription(INCOMING_ANSWER)
                break

            case "RTCPeerConnectionOffer":
                const INCOMING_OFFER = new RTCSessionDescription(DATA.body)
                await this.peer_connection.setRemoteDescription(INCOMING_OFFER)
                const CREATED_ANSWER = await this.peer_connection.createAnswer();
                await this.peer_connection.setLocalDescription(CREATED_ANSWER);
                webrtc_adaptive_web_socket.send(JSON.stringify({
                    type: "webrtc.peer_connection",
                    head: "RTCPeerConnectionAnswer",
                    sender_user_id: this.user_id,
                    body: CREATED_ANSWER
                }))
                break

            case "NewIceCandidate":
                try
                {
                    await this.peer_connection.addIceCandidate(DATA.iceCandidate)
                    console.log("Added new Ice Candidate")
                }
                catch(e)
                {
                    console.error("Error adding received ice candidate", e);
                }
                finally
                {
                    break
                }

            default:
                console.error("Unrecognized incoming signal")
                break
        }
    }

    #handleIcaCandidate = (event) => {
        if (event.candidate) {
            this.webrtc_web_socket.send(JSON.stringify({
                type: "webrtc.share_ice_candidate",
                sender_user_id: this.user_id,
                ice_candidate: event.candidate
            }))

            console.log(`Sent another Ice Candidate: ${event.candidate}`)
        }
    }

    #handleNewTrack = async (event) => {
        // process new availiable stream
    }

    #sendSdpOffer = async () => {
        const CREATED_OFFER = await this.peer_connection.createOffer()
        await this.peer_connection.setLocalDescription(CREATED_OFFER)

        this.webrtc_adaptive_web_socket.send(JSON.stringify({
            type: "webrtc.peer_connection",
            head: "RTCPeerConnectionOffer",
            sender_user_id: this.user_id,
            body: CREATED_OFFER
        }))
    }
}



peerConnection = async (USER_DATA) => {
    const localStream = await navigator.mediaDevices.getUserMedia({ video: false, audio: true });
    // const localDemo = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true })
    // localDemo.getVideoTracks()[0].id = "demo"
    PEER_CONNECTION = new RTCPeerConnection(ICE_CONF)
    const remoteVideo = document.querySelector('#remoteVideo');

    const videoElement = document.querySelector('video#localVideo');
    videoElement.srcObject = localStream;

    PEER_CONNECTION.addEventListener('track', async (event) => {
        for (stream of event.streams)
        {
            if (stream.id == "demo")
            {
                // localDemo.srcObject = stream
            }
            else{
                remoteVideo.srcObject = stream
            }
        }
    });
    // localDemo.getTracks().forEach(track => {
    //     PEER_CONNECTION.addTrack(track, localDemo);
    // });

    localStream.getTracks().forEach(track => {
        PEER_CONNECTION.addTrack(track, localStream);
    });

    PEER_CONNECTION.onicecandidate = (event) => {
        console.log(1)
        if (event.candidate) {
            WEBRTC_SOCKET.send(JSON.stringify({
                type: "webrtc.share_ice_candidate",
                sender_user_id: USER_DATA.user_id,
                ice_candidate: event.candidate
            }))

            console.log("Sent another Ice Candidate")
        }
    }

    PEER_CONNECTION.addEventListener('icecandidate', event => {
        console.log(event)
    });

    PEER_CONNECTION.addEventListener('connectionstatechange', event => {
        if (PEER_CONNECTION.connectionState === 'connected') {
            console.log("gratz")
        }
    });

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
        else if (DATA.type == "NewIceCandidate")
        {
            try
            {
                await PEER_CONNECTION.addIceCandidate(DATA.iceCandidate)
                console.log("Added new Ice Candidate")
            }
            catch(e)
            {
                console.error('Error adding received ice candidate', e);
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
let data = {uder_id: 1}
fetch('/vw/get_user_data')
    .then(response => response.json())
    .then((data) => {
        peerConnection(data)
    })


