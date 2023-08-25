from django.shortcuts import render

def index(request):
    return render(request, 'video_chat/index.html')
