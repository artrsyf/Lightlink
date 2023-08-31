let USER_ID = sessionStorage.getItem("user_id")
let TOKEN = sessionStorage.getItem("token")
let STREAM_ID = sessionStorage.getItem("stream_id")
let STREAM_TOKEN = sessionStorage.getItem("stream_token")

const client = AgoraRTC.createClient({mode:'rtc', codec:'vp8'})
const share_client = AgoraRTC.createClient({mode: 'rtc', codec: 'vp8'})

let localTracks = []
let remoteUsers = {}

let getSessionUserData = async () => {
    let response = await fetch('/vw/get_user_data/')
    data = await response.json()
    return data
}

curr_user = getSessionUserData()
let USER_USERNAME = curr_user.user_username
let USER_PROFILENAME = curr_user.user_profilename

let joinAndDisplayLocalStream = async () => {

    client.on('user-published', handleUserJoined)
    client.on('user-left', handleUserLeft)

    try{
        await share_client.join(APP_ID, CHANNEL, STREAM_TOKEN, STREAM_ID)
    }
    catch(ex){
        console.error('Cant make stream mirror client')
    }

    await client.join(APP_ID, CHANNEL, TOKEN, USER_ID)

    localTracks = AgoraRTC.createMicrophoneAndCameraTracks()

    let player = `<div  class="video-container" id="user-container-${USER_ID}">
                    <div class="video-player" id="user-${USER_ID}"></div>
                    <div class="video-player-user-name id="name-user-${USER_ID}">${USER_USERNAME}</div>
                </div>`

    document.getElementById('video-streams').insertAdjacentHTML("beforeend", player)
    localTracks[1].play(`user-${USER_ID}`)


    await client.publish([localTracks[0], localTracks[1]])
    
}