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
        switch(this.web_socket.readyState)
        {
            case 1:
                this.web_socket.send(data)
                break

            case 2:
                this.web_socket.onopen = () => {
                    this.web_socket.send(data)
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
        this.webrtc_adaptive_web_socket.onmessage(this.#handleSignal)
        this.ICE_CONF = ice_conf
        this.user_id = user_id

        this.peer_connection = new RTCPeerConnection(ICE_CONF)
        this.peer_connection.addEventListener("track", this.#handleNewTrack)
        this.peer_connection.onicecandidate = this.#handleIcaCandidate
        this.peer_connection.addEventListener("connectionstatechange", this.#handleConnectionStateChanged)

        this.localStream = null
        // test
        this.is_calling = null
    }

    #createDefaultVideoElement = () => {
        const videoElement = document.createElement('video');
        // videoElement.width = 640;
        // videoElement.height = 360;
        videoElement.controls = true;
        videoElement.autoplay = true;

        return videoElement
    }

    makeConnection = async () => {
        this.localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        this.localStream.getTracks().forEach(track => {
            this.peer_connection.addTrack(track, this.localStream);
        });

        let videoElement = this.#createDefaultVideoElement()
        videoElement.srcObject = this.localStream

        // Заменить на корректное добавление тега
        document.body.appendChild(videoElement);

        this.#sendSdpOffer()
    }

    #handleConnectionStateChanged = (event) => {
        if (this.peer_connection.connectionState === "connected") {
            console.log("Peer connection successfully established")
        }
    }

    #handleSignal = async (event) => {
        console.log("got a signal")
        const DATA = JSON.parse(event.data)
        switch(DATA.type){
            case "RTCPeerConnectionAnswer":
                console.log(1)
                const INCOMING_ANSWER = new RTCSessionDescription(DATA.body)
                await this.peer_connection.setRemoteDescription(INCOMING_ANSWER)
                break

            case "RTCPeerConnectionOffer":
                console.log(2)
                const INCOMING_OFFER = new RTCSessionDescription(DATA.body)
                await this.peer_connection.setRemoteDescription(INCOMING_OFFER)
                const CREATED_ANSWER = await this.peer_connection.createAnswer();
                await this.peer_connection.setLocalDescription(CREATED_ANSWER);
                this.webrtc_adaptive_web_socket.send(JSON.stringify({
                    type: "webrtc.peer_connection",
                    head: "RTCPeerConnectionAnswer",
                    sender_user_id: this.user_id,
                    body: CREATED_ANSWER
                }))
                console.log("sent answer")
                break

            case "NewIceCandidate":
                console.log(3)
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
            this.webrtc_adaptive_web_socket.send(JSON.stringify({
                type: "webrtc.share_ice_candidate",
                sender_user_id: this.user_id,
                ice_candidate: event.candidate
            }))

            console.log("Sent another Ice Candidate:", event.candidate)
        }
    }

    #handleNewTrack = async (event) => {
        // process new availiable stream
        const remoteStream = event.streams[0]
        let videoElement = this.#createDefaultVideoElement()

        videoElement.srcObject = remoteStream

        document.body.appendChild(videoElement)
    }

    #sendSdpOffer = async () => {
        if(!this.is_calling) return
        if (this.user_id == '2') return 
        const CREATED_OFFER = await this.peer_connection.createOffer()
        await this.peer_connection.setLocalDescription(CREATED_OFFER)

        this.webrtc_adaptive_web_socket.send(JSON.stringify({
            type: "webrtc.peer_connection",
            head: "RTCPeerConnectionOffer",
            sender_user_id: this.user_id,
            body: CREATED_OFFER
        }))
        console.log('sent offer')
    }
}