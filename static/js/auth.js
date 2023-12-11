const INPUT_FRAMES = [{"input": document.getElementById('username_input'),
                       "frame": document.getElementById('username_frame')
                      },

                      {"input": document.getElementById('password_input'),
                       "frame": document.getElementById('password_frame')
                      },

                      {"input": document.getElementById('password2_input'),
                       "frame": document.getElementById('password2_frame')
                      },
                       
                      {"input": document.getElementById('email_input'),
                       "frame": document.getElementById('email_frame')}]

let setEventListener = (input, frame) => {
    if (input) {
        input.addEventListener('focus', () => {
            frame.classList.add('frame_open')
        })
        
        input.addEventListener('blur', () => {
            frame.classList.remove('frame_open')        
        })
    }
}

let multiObjectSetEventListener = (input_frame_list) => {
    for (const frame_map of input_frame_list){
        setEventListener(frame_map["input"], frame_map["frame"])
    }
}

multiObjectSetEventListener(INPUT_FRAMES)
