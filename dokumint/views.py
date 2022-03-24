from django.shortcuts import render,redirect
from dokumint.models import Certifier,Receiver,ProjectDesc
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from django.core.files.base import File
from django.conf.urls.static import static


# Create your views here.
def Home(request):
    return render(request,'home.html')


def Validate(request):
    if request.POST:

        wallet_address = request.POST.get('wallet_address')
        moralis_user_id = request.POST.get('moralis_user_id')
        tempobj=None
        request.session['wallet_address'] = wallet_address
        request.session['moralis_user_id'] = moralis_user_id
        return redirect('dashboard',moralis_user_id)
    else:
        return redirect('home')


def dashboard(request,id):
    
    return render(request,'dashboard.html')

def checkMe(request):
    wallet_address=request.session['wallet_address']
    moralis_user_id=request.session['moralis_user_id']
    if request.POST:
        name = request.POST.get('name')
        symbol = request.POST.get('symbol')
        desc = request.POST.get('desc')
        csvf = request.FILES['csvf']
        certifier=Certifier()
        certifier.wallet_address = wallet_address
        certifier.name = name
        certifier.moralis_user_id = moralis_user_id
        certifier.save()
        projectdesc = ProjectDesc()
        projectdesc.certifier=certifier
        projectdesc.proj_name = "dokumin"
        projectdesc.proj_desc = desc
        projectdesc.symbol = symbol
        projectdesc.save()
        df = pd.read_csv(csvf)
        df = df.reset_index()

        for index, i in df.iterrows():
            obj = Receiver()
            obj.name = i['Name'] 
            print(obj.name)
            obj.certifier = certifier
            print(obj.certifier)
            obj.address = i['Address']
            print(obj.address)
            generateImage(i.Name)
            path_image = 'pictures/'+str(obj.name)+".jpg"
            outfile = Image.open(path_image)
            obj.image = File(outfile)
            print('------------------------------------')
            print(obj.image)
            print('----------------------------------')

            obj.save()
            



    return render(request,'sucess.html')


def generateImage(name):
    imaget = Image.open('certificate.png')
    draw = ImageDraw.Draw(imaget)
    draw.text(xy=(725,760),text='{}'.format(name),fill=(0,0,0))
    imaget.save('pictures/{}.jpg'.format(name))
    return imaget





