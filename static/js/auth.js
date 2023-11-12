let username_input = document.getElementById('username_input')
let password_input = document.getElementById('password_input')
let password_frame = document.getElementById('password_frame')
let username_frame = document.getElementById('username_frame')

username_input.addEventListener('click', () => {
    username_frame.classList.add('frame_open')
})

document.addEventListener('click', (event) => {
    if (!username_input.contains(event.target)){
        username_frame.classList.remove('frame_open')        
    }
})

password_input.addEventListener('click', () => {
    password_frame.classList.add('frame_open')
})

document.addEventListener('click', (event) => {
    if (!password_input.contains(event.target)){
        password_frame.classList.remove('frame_open')        
    }
})
