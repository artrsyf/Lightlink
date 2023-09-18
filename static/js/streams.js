const csrf_token = document.getElementById('channel-meta').getAttribute('data-csrf-token')
const channel_id = document.getElementById('channel-meta').getAttribute('channel-id')

const client = AgoraRTC.createClient({mode:'rtc', codec:'vp8'})
const share_client = AgoraRTC.createClient({mode: 'rtc', codec: 'vp8'})

let localTracks = []
let remoteUsers = {}

let getSessionUserData = async () => {
    let response = await fetch('/vw/get_user_data/')
    data = await response.json()
    console.log(`*CLIENT RESPONSE: Successfully parsed user data: ${JSON.stringify(data)}`)
    if (data.user_id){
        return data
    }
    else{
        return false;
    }
}

let getAgoraSDKData = async () => {
    let response = await new Promise((resolve, reject) => {
        $.ajax({
            url: '/vw/get_agora_sdk_data',
            dataType: 'json',
            data:{
                'csrfmiddlewaretoken': csrf_token
            },
            method: 'POST',
            success: function(data){
                console.log('*CLIENT RESPONSE: Successfully parsed Agora app data')
                resolve(data)
            },
            error: function(xhr, error, status){
                console.error(`*CLIENT RESPONSE: Could not parse Agora app data with error: ${error}, with status: ${status}`)
                reject(error)
            }
        })
    })
    return response
}

let joinAndDisplayLocalStream = async () => {

    client.on('user-published', handleUserJoined)
    client.on('user-left', handleUserLeft)

    try{
        await share_client.join(APP_ID, CHANNEL, STREAM_TOKEN, STREAM_ID)
        console.log('*CLIENT RESPONSE: Successfully create stream client')
    }
    catch(ex){
        console.error('*CLIENT RESPONSE: Could not create stream client, check Agora logs')
    }

    try{
        await client.join(APP_ID, CHANNEL, TOKEN, USER_ID)
        console.log('*CLIENT RESPONSE: Successfully create client')
    }
    catch(ex){
        console.error('*CLIENT RESPONSE: Could not create client, check Agora logs')
    }

    localTracks = AgoraRTC.createMicrophoneAndCameraTracks()

    let player = `<div  class="video-container" id="user-container-${USER_ID}">
                    <div class="video-player" id="user-${USER_ID}"></div>
                    <div class="video-player-user-name id="name-user-${USER_ID}">${USER_USERNAME}</div>
                </div>`

    document.getElementById('video-streams').insertAdjacentHTML("beforeend", player)
    localTracks[1].play(`user-${USER_ID}`)

    await client.publish([localTracks[0], localTracks[1]])
}

let handleUserJoined = async (user, mediaType) => {
    remoteUsers[user.uid] = user
    await client.subscribe(user, mediaType)

    if (mediaType == 'video'){
        let player = document.getElementById(`user-container-${user.uid}`)
        if (player != null){
            player.remove()
        }
        let member;

        try{
            member = await getMember(user)
        }
        catch(ex){
            console.error("*CLIENT RESPONSE: Could not parse member name")
            member = {name: 'Undefined'}
        }

        player = `<div  class="video-container" id="user-container-${user.uid}">
            <div class="video-player" id="user-${user.uid}" name="${member.name}"></div>
            <div class="video-player-user-name">${member.name}</div>
        </div>`

        document.getElementById('video-streams').insertAdjacentHTML('beforeend', player)
        user.videoTrack.play(`user-${user.uid}`)
    }

    if (mediaType == 'audio'){
        user.audioTrack.play()
    }
}

let handleUserLeft = async (user) => {
    delete remoteUsers[user.uid]
    document.getElementById(`user-container-${user.uid}`).remove()
}

let getMember = async (user) => {
    let response = await fetch(`/vw/get_member/?uid=${user.uid}`)
    let member = await response.json()
    return member
}

let leaveAndRemovLocalStreams = async () => {
    for (let i = 0; i < localTracks.length; i++){
        localTracks[i].stop()
        localTracks[i].close()
    }

    await client.leave()
    window.open('/vw/Home', '_self')
}

let toggleCamera = async (e) => {
    if (localTracks[1].muted){
        await localTracks[1].setMuted(false)
        e.target.style.backgroundColor = 'green'
    }
    else{
        await localTracks[1].setMuted(true)
        e.target.style.backgroundColor = 'blue'
    }
}

let toggleMicrophone = async (e) => {
    if (localTracks[0].muted){
        await localTracks[0].setMuted(false)
        e.target.style.backgroundColor = 'green'
    }
    else{
        await localTracks[0].setMuted(true)
        e.target.style.backgroundColor = 'blue'
    }
}

var isSharingEnabled = false
var screenTrack = []

let toggleSharing = async (e) => {
    if (!isSharingEnabled){
        let withAudio = true
        let defaultConfig = {}
        screenTrack = AgoraRTC.createScreenVideoTrack(defaultConfig, withAudio)

        await share_client.publish([screenTrack[0], screenTrack[1]])
        e.target.style.backgroundColor = 'green'
        isSharingEnabled = true
    }
    else{
        for (const track of screenTrack){
            track.stop()
            track.close()
        }

        await share_client.unpublish([screenTrack[0], screenTrack[1]])
        document.getElementById(`user-container-${stream_UID}`).remove()
        e.target.style.backgroundColor = 'blue'
        isSharingEnabled = false
    }
}

// APP_ID можно перехватить!
var APP_ID;
var USER_ID
var TOKEN
var STREAM_ID
var STREAM_TOKEN
let CHANNEL = channel_id
curr_user = getSessionUserData()

let USER_USERNAME = curr_user.user_username
let USER_PROFILENAME = curr_user.user_profilename

getAgoraSDKData().then(data => {
    APP_ID = data.app_id
    fetch(`/vw/get_token/?channel=${channel_id}`)
        .then(CONVERSATION_DATA_JSON => CONVERSATION_DATA_JSON.json())
        .then(CONVERSATION_DATA =>{
            console.log(`*CLIENT RESPONSE: Client settings: ${JSON.stringify(CONVERSATION_DATA)}`)

            USER_ID = CONVERSATION_DATA.user_id
            TOKEN = CONVERSATION_DATA.token
            STREAM_ID = CONVERSATION_DATA.stream_id
            STREAM_TOKEN = CONVERSATION_DATA.stream_token

            document.getElementById('leave-btn').addEventListener('click', leaveAndRemovLocalStreams)

            document.getElementById('video-btn').addEventListener('click', toggleCamera)

            document.getElementById('mic-btn').addEventListener('click', toggleMicrophone)

            document.getElementById('share-btn').addEventListener('click', toggleSharing)

            joinAndDisplayLocalStream()
    })
})
