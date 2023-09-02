const csrf_token = document.getElementById('channel-meta').getAttribute('data-csrf-token')
let channel_id = document.getElementById('channel-meta').getAttribute('channel-id')

// let USER_ID = sessionStorage.getItem("user_id")
// let TOKEN = sessionStorage.getItem("token")
// let STREAM_ID = sessionStorage.getItem("stream_id")
// let STREAM_TOKEN = sessionStorage.getItem("stream_token")
// let CHANNEL = sessionStorage.getItem("channel_id")

const client = AgoraRTC.createClient({mode:'rtc', codec:'vp8'})
const share_client = AgoraRTC.createClient({mode: 'rtc', codec: 'vp8'})

let localTracks = []
let remoteUsers = {}

let getSessionUserData = async () => {
    let response = await fetch('/vw/get_user_data/')
    data = await response.json()
    return data
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
                console.log('AGORA_DATA', data)
                resolve(data)
            },
            error: function(xhr, error, status){
                console.error('AGORA_DATA_failure')
                reject(error)
            }
        })
    })
    return response
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
            console.error("CANT READ MEMBER NAME")
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

// APP_ID можно перехватить!
var APP_ID;
var USER_ID
var TOKEN
var STREAM_ID
var STREAM_TOKEN
let CHANNEL = channel_id
getAgoraSDKData().then(data => {
    APP_ID = data.app_id
    fetch(`/vw/get_token/?channel=${channel_id}`)
        .then(CONVERSATION_DATA_JSON => CONVERSATION_DATA_JSON.json())
        .then(CONVERSATION_DATA =>{
            console.log(CONVERSATION_DATA)
            USER_ID = CONVERSATION_DATA.user_id
            TOKEN = CONVERSATION_DATA.token
            // sth wrong
            STREAM_ID = CONVERSATION_DATA.stream_id
            STREAM_TOKEN = CONVERSATION_DATA.stream_token
            joinAndDisplayLocalStream()
    })
    // Видеочат начинает работать только после установки id приложения
    // В случае большой загрузке сервера чат ляжет!
})


/* Комментарий не для коммита <TODO>
   1. Работа чата полностью зависит от параметров, зафиксированных в sessionStorage,
        соответственно, любая проблема с ними приведет к не работе чата, нужно заменить
        данный способ на POST fetching данных с сервера. К примеру, может быть такая проблема:
        Юзер переходит в чат не по нажатию кнопки, а по ссылке, в этом случае из- за отсутсвия значнеия
        канала в sessionStorage (подгрузка происходит только по нажатию на кнопку)
        пользователь не попадет в чат. 
        В теории такой денай пользовательского запроса можно реализовать как часть предметной области*/