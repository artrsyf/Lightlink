const ws = new WebSocket("ws://localhost:8000/ws/service/media/1/");
let webRtcPeer;
let remoteWebRtcPeer;
let remote_user_id;
let localVideo = document.querySelector('#localVideo')
let remoteVideo = document.querySelector('#remoteVideo')
let echoVideo = document.querySelector('#echoVideo')

function sendMessage(message)
{
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

ws.onmessage = function(message)
{
  const jsonMessage = JSON.parse(message.data);
  console.log(jsonMessage);

  switch (jsonMessage.id) {
    case 'sdpAnswer':
      handleProcessSdpAnswer(jsonMessage);
      break;
    case 'iceCandidate':
      handleAddIceCandidate(jsonMessage);
	    break;
    case 'newUser':
      console.log(`Got new user: user_${jsonMessage.user_id}`)
      remote_user_id = jsonMessage.user_id
	  case 'info':
		  console.log(jsonMessage)
		  break;
    case 'error':
      console.error(jsonMessage);
      break;
    default:
      console.error("Invalid message, id: " + jsonMessage.id);
      break;
  }
}

function handleProcessSdpAnswer(jsonMessage)
{
  console.log("SDP Answer from Kurento, process in WebRTC Peer");

  if (webRtcPeer == null) {
    console.warn("Skip, no WebRTC Peer");
    return;
  }

  if (jsonMessage.remote_user_id == user_id)
  {
    webRtcPeer.processAnswer(jsonMessage.payload, (err) => {
      if (err) {
        console.error('cant sdp answer')
        return;
      }
  
      console.log("[handleProcessSdpAnswer] SDP local Answer ready");
    });
  }
  else if (jsonMessage.remote_user_id == remote_user_id)
  {
    remoteWebRtcPeer.processAnswer(jsonMessage.payload, (err) => {
      if (err) {
        console.error('cant sdp answer', err)
        console.warn(jsonMessage.payload)
        return;
      }
  
      console.log("[handleProcessSdpAnswer] SDP remote Answer ready");
    });
  }
}

function handleAddIceCandidate(jsonMessage)
{
  if (webRtcPeer == null) {
    console.warn("Skip, no WebRTC Peer");
    return;
  }

  webRtcPeer.addIceCandidate(jsonMessage.payload, (err) => {
    if (err) {
      console.error("[handleAddIceCandidateLocalPeer] " + err);
      return;
    }
    console.log('added ice to local peer')
  });

  if (remoteWebRtcPeer){
    remoteWebRtcPeer.addIceCandidate(jsonMessage.payload, (err) => {
      if (err) {
        console.error("[handleAddIceCandidateRemotePeer] " + err);
        return;
      }
      console.log('added ice to remote peer')
    });
  }
}

// var constraints = {
//   audio : true,
//   video : {
//     mandatory : {
//       maxWidth : 320,
//       maxFrameRate : 15,
//       minFrameRate : 15
//     }
//   }
// };

var constraints = {
  audio : true,
  video : true
}

var options = {
  localVideo: localVideo,
  remoteVideo: echoVideo,
  mediaConstraints: constraints,
  onicecandidate: (candidate) => {
    console.log('make local ice')
    sendMessage({
      id: 'addIce',
      from_user_id: user_id,
      to_user_id: user_id,
      payload: candidate,
    })
  }
}

webRtcPeer = new kurentoUtils.WebRtcPeer.WebRtcPeerSendrecv(options,
  function (error) {
  if(error) {
    return console.error(error);
  }

  webRtcPeer.generateOffer((err, sdpOffer) => {
    if (err) {
      console.error("[start/WebRtcPeerSendrecv/generateOffer] Error: " + err);
      return;
    }
  
    sendMessage({
      id: 'processOffer',
      from_user_id: user_id,
      to_user_id: user_id,
      payload: sdpOffer,
    });
    console.log(`Sent sdp offer from local_user_${user_id} to remote_user_${user_id}`)
  })
})



// var remote_options = {
//   remoteVideo: remoteVideo,
//   onicecandidate: (candidate) => sendMessage({
//     id: 'addIce',
//     from_user_id: user_id,
//     to_user_id: remote_user_id,
//     payload: candidate,
//   })
// }

// remoteWebRtcPeer = new kurentoUtils.WebRtcPeer.WebRtcPeerRecvonly(remote_options,
//   function (error) {
//   if(error) {
//     return console.error(error);
//   }
//   remoteWebRtcPeer.generateOffer((err, remoteSdpOffer) => {
//     if (err) {
//       console.error("[start/WebRtcPeerRecvonly/generateOffer] Error: " + err);
//       return;
//     }

//     sendMessage({
//       id: 'processOffer',
//       from_user_id: user_id,
//       to_user_id: remote_user_id,
//       payload: remoteSdpOffer,
//     });
//     console.log(`Sent sdp offer from local_user${user_id} to remote_user_${remote_user_id}`)
//   })
// })


