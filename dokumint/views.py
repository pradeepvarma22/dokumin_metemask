from django.shortcuts import render,redirect
from dokumint.models import Certifier,Receiver,ProjectDesc
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import json
import requests

from django.core.files.base import File
from django.conf.urls.static import static
from utils.keys import keys
from utils.nftstorage import NftStorage
from utils.pinata import Pinata
from config.settings import BASE_DIR

NFTSTORAGE_API_KEY = keys['NFTSTORAGE']
PINATA_JWT = keys['PINATA']

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
        projectdesc.proj_name = name
        projectdesc.proj_desc = desc
        projectdesc.symbol = symbol

        projectdesc.save()
        df = pd.read_csv(csvf)
        df = df.reset_index()

        for index, i in df.iterrows():
            obj = Receiver()
            obj.name = i['Name'] 
            #print(obj.name)
            obj.certifier = certifier
            #print(obj.certifier)
            obj.address = i['Address']
            #print(obj.address)
            obj.course = i['Course'] 
            generateImage(i.Name,moralis_user_id)
            path_image = 'images/{}/'.format(moralis_user_id) + str(obj.name) + ".png"
            outfile = Image.open(path_image)
            obj.image = File(outfile)
            obj.save()
            
    return render(request,'sucess.html')


def generateImage(name,user):
    imaget = Image.open('certificate.png')
    draw = ImageDraw.Draw(imaget)
    draw.text(xy=(725,760),text='{}'.format(name),fill=(0,0,0))
    imaget.save('images/{}/{}.png'.format(user,name))

    meta = []
    att = {"trait_type": "Name", "value":""}
    meta.append(att)

    token = {
        "image": base_uri + str(k) + '.png',
        "tokenId": k,
        "name": project_name + ' ' + "#" + str(k),
        "attributes": meta
    }

    meta_path = 'metadata/{}/'.format(user)
    meta_file = meta_path + "/" + str(k) + '.json'

    with open(meta_file, 'w') as outfile:
        json.dump(token, outfile, indent=4)

    return imaget


def uploadIPFS(request):
    user = request.session['moralis_user_id']
    certifierobj = Certifier.objects.get(certifier=user)
    receiverobj = Receiver.objects.filter(certifier=certifierobj)
    projobj = ProjectDesc.objects.get(certifier=certifierobj)
    base_path = BASE_DIR + '/images/{}/'.format(user)

    nstorage = {}
    c = NftStorage(NFTSTORAGE_API_KEY)
    imgpath = ''

    for recobj in receiverobj:
        img = recobj.image 
        imgpath += base_path + img 
        metapath += base_path + str(k) + '.json' 

    cid = c.upload(imgpath, 'image/png')
    nstorage['image_directory_cid'] = cid

    cid = c.upload(metapath, 'application/json')
    nstorage['metadata_directory_cid'] = cid

    p = Pinata(PINATA_JWT)
    for k, v in nstorage.items():
        name = proj_name + ' ' + k.split('_')[0]
        p.pin(name, v)

    projobj.cid = cid
    projobj.save()
    contract  = getContract()
    ipfs_url = "ipfs://" + cid

    contract = contract.replace('MyToken',projobj.name)
    contract = contract.replace('MTK',projobj.symbol)
    contract = contract.replace('ipfs_url',"'"+ipfs_url+"'")

    return render(request, "success.html",  {'contract':contract, 'proj':projobj, 'ipfs_url':ipfs_url })
   
def deploy(request):
    address = request.session['wallet_address']
    user = request.session['moralis_user_id']
    certifierobj = Certifier.objects.get(certifier=user)
    project = ProjectDesc.objects.get(certifier=certifierobj)

    url = "https://api.nftport.xyz/v0/contracts"
    payload = "{\n  \"chain\": \"polygon\",\n  \"name\": \"CRYPTOPUNKS\",\n  \"symbol\": \"CYBER\",\n  \"owner_address\":wallet,\n  \"metadata_updatable\": false,\n  \"type\": \"erc721\"\n}"
    
    print(project.name)
    print(project.symbol)

    payload = payload.replace('CRYPTOPUNKS',project.name)
    payload = payload.replace('CYBER',project.symbol)
    payload = payload.replace('wallet','"'+address+'"')

    headers = {
        'Content-Type': "application/json",
        'Authorization': "d775b8ce-a5b7-420b-b818-3e7c46075ab2"
    }

    response = requests.request("POST", url, data=payload, headers=headers)
    #print(response.text)
    print('--------------------')
    print(response)
    return render(request,'deploy.html',{'respose':response.text})



def getContract():
    return '''
        // SPDX-License-Identifier: MIT
        pragma solidity ^0.8.4;

        import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
        import "@openzeppelin/contracts/access/Ownable.sol";

        contract MyToken is ERC721, Ownable {
            constructor() ERC721("MyToken", "MTK") {}

            function _baseURI() internal pure override returns (string memory) {
                return ipfs_url;
            }

            function safeMint(address to, uint256 tokenId) public onlyOwner {
                _safeMint(to, tokenId);
            }
        }
    '''