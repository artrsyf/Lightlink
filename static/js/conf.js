// For test
let localVideo = document.querySelector("#localVideo")
let remoteVideo = document.querySelector("#remoteVideo")
const constraints = {
    audio : false,
    video : true
}
// For test

const ws = new WebSocket(
    "ws://"
    + window.location.host
    + '/ws/service/conference/'
    + '1' // for test
    + '/'
)

function sendMessage(message)
{
    console.log(message)
    if (ws.readyState !== ws.OPEN) {
    ws.onopen = () => {
        const jsonMessage = JSON.stringify(message);
        ws.send(jsonMessage);
    }
    return;
    }

    const jsonMessage = JSON.stringify(message);
    ws.send(jsonMessage);
}

let rtc_peers = {}
let room_name = 1 // request for room_name

var OPTIONS = {
    localVideo: localVideo,
    mediaConstraints: constraints,
    onicecandidate: (candidate) => {
        sendMessage({
            type: "video_conference.handleIceCandidate",
            endpoint_type: "sendEndPoint",
            candidate: candidate
        })
    }
}

ws.onmessage = function(message)
{
    const jsonMessage = JSON.parse(message.data);
    console.log(jsonMessage);

    switch (jsonMessage.type) {
        case "waitingForOffer":
            sendSdpOffer(jsonMessage);
            break;
        case "handleIceCandidate":
            if (jsonMessage.endpoint_type == "sendEndPoint"){
                send_rtc_peer.addIceCandidate(jsonMessage.candidate, (err) => {
                    if (err){
                        console.error("[handleAddIceCandidateSendEndPointPeer] " + err);
                        return;
                    }
                    console.log("Added ice to sendEndPoint peer")
                });
            }
            else if (jsonMessage.endpoint_type == "receiveEndPoint"){
                let remote_user_id = jsonMessage.remote_user_id
                rtc_peers[remote_user_id].addIceCandidate(jsonMessage.candidate, (err) => {
                    if (err){
                        console.error("[handleAddIceCandidateReceiveEndPointPeer] " + err);
                        return;
                    }
                    console.log("Added ice to receiveEndPoint peer")
                });
            }
            else{
                console.error("Invalid endpoint type: " + jsonMessage.endpoint_type);
            }
            break;
        case "handleSdpAnswer":
            if (jsonMessage.endpoint_type == "sendEndPoint"){
                send_rtc_peer.processAnswer(jsonMessage.sdp_anwer, (err) => {
                    if (err) {
                        console.error("Cant sdp answer for sendEndPoint", err)
                        console.warn(jsonMessage.sdp_anwer)
                        return;
                    }
                
                    console.log("[handleProcessSdpAnswer] sendEndPoint SDP Answer ready");
                });
            }
            else if (jsonMessage.endpoint_type == "receiveEndPoint"){
                let remote_user_id = jsonMessage.remote_user_id
                rtc_peers[remote_user_id].processAnswer(jsonMessage.sdp_anwer, (err) => {
                    if (err) {
                        console.error("Cant sdp answer for receiveEndPoint", err)
                        console.warn(jsonMessage.sdp_anwer)
                        return;
                    }
                
                    console.log("[handleProcessSdpAnswer] receiveEndPoint SDP Answer ready");
                });
            }
            else{
                console.error("Invalid endpoint type: " + jsonMessage.endpoint_type);
            }
            break;
        default:
            console.error("Invalid message, id: " + jsonMessage.id);
            break;
    }
}

sendSdpOffer = (jsonMessage) => {
    remote_user_id = jsonMessage.remote_user_id
    let REMOTE_OPTIONS = {
        remoteVideo: remoteVideo,
        mediaConstraints: constraints,
        onicecandidate: (candidate) => {
            sendMessage({
                type: "video_conference.handleIceCandidate",
                endpoint_type: "receiveEndPoint",
                local_user_id: user_id,
                remote_user_id: remote_user_id,
                candidate: candidate
            })
        }
    }

    rtc_peers[remote_user_id] = new kurentoUtils.WebRtcPeer.WebRtcPeerRecvonly(REMOTE_OPTIONS, (error) => {
        if (error){
            return console.error(error);
        }

        rtc_peers[remote_user_id].generateOffer((err, sdp_offer) => {
            if (err){
                console.error("[start/WebRtcPeerRecvonly/generateOffer] Error: " + err);
                return;
            }
    
            sendMessage({
                type: "video_conference.handleSdpOffer",
                endpoint_type: "receiveEndPoint",
                remote_user_id: remote_user_id,
                sdp_offer: sdp_offer
            });
            // console.log(`Sent sdp offer from local_user${user_id} to remote_user_${remote_user_id}`)
        })
    })
}

fetch('/vw/get_user_data')
.then(response => response.json())
.then((data) => {
    let user_id = data.user_id

    send_rtc_peer = new kurentoUtils.WebRtcPeer.WebRtcPeerSendonly(OPTIONS, (error) => {
        if (error){
            return console.error(error);
        }
        
        send_rtc_peer.generateOffer((err, sdp_offer) => {
            if (err) {
                console.error("[start/WebRtcPeerSendonly/generateOffer] Error: " + err);
                return;
            }
            text = sdp_offer.replace(/\n/g, "\\n").replace(/\t/g, "\\t");
            console.log(text);
            sendMessage({
                type: "video_conference.handleSdpOffer",
                endpoint_type: "sendEndPoint",
                sdp_offer: sdp_offer
            });
            // console.log(`Sent sdp offer from local_user_${user_id} to remote_user_${user_id}`)
        })
    })
})

